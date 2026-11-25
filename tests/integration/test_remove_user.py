"""
Integration tests for account removal.

Removing an account has to leave nothing of the user behind: every row they
own, every file they uploaded — and nothing of anybody else's touched. The
rows live in nine tables spread over three levels (user -> candidature ->
contact, user -> conversation -> message, ...), and the files in a folder the
database knows nothing about, so a regression here is silent: the request
still answers 200 while personal data stays in the database or on disk.

`test_every_table_is_covered` is the one that should start failing the day a
table is added: it forces whoever adds it to decide how it is cleaned up.
"""

import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.api.v1.account import remove_user as remove_user_endpoint
from app.core.config import settings
from app.core.database import Base
from app.core.exceptions import BadRequestError, NotFoundError
from app.models import (
    CV,
    Analyse,
    Candidature,
    ChatConversation,
    ChatMessage,
    Contact,
    Kanban,
    Preference,
    User,
)
from app.schemas.auth import RemoveUserRequest
from app.services.auth_service import AuthService


@pytest.fixture
def upload_root(tmp_path: Path, monkeypatch) -> Path:
    """Points the upload directory at a scratch folder, never the real one."""
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    return tmp_path


async def populate(session, user: User, upload_root: Path) -> dict[str, list[Path]]:
    """
    Gives `user` something in every table, and CV files on disk.

    The analysis, the candidature and the conversation reference each other
    (candidature -> analysis -> conversation, all of them -> cv), which is the
    shape that makes deletion order matter.
    """
    session.add(Preference(user_id=user.id))

    cv_folder = upload_root / str(user.id) / settings.cv_dir
    cv_folder.mkdir(parents=True)
    files: list[Path] = []
    cvs: list[CV] = []
    for index in range(2):
        key = f"{uuid.uuid4().hex}.pdf"
        path = cv_folder / key
        path.write_bytes(b"%PDF-1.4 fake")
        files.append(path)
        cv = CV(
            user_id=user.id,
            name=f"cv-{index}.pdf",
            key=f"{settings.cv_dir}/{key}",
            extracted_text="Jane Doe — développeuse",
        )
        session.add(cv)
        cvs.append(cv)

    conversation = ChatConversation(user_id=user.id, title="Question sur mon CV")
    session.add(conversation)
    await session.flush()
    for seq, role in enumerate(("user", "assistant")):
        session.add(
            ChatMessage(
                conversation_id=conversation.id, seq=seq, role=role, content="…"
            )
        )

    analyse = Analyse(
        user_id=user.id,
        cv_id=cvs[0].id,
        job_description="Offre de test",
        conversation_id=conversation.id,
    )
    session.add(analyse)
    await session.flush()

    for position, status in enumerate(("to_send", "interview")):
        candidature = Candidature(
            user_id=user.id,
            cv_id=cvs[0].id,
            analyse_id=analyse.id if position == 0 else None,
            company_name=f"Acme {position}",
            job_title="dev",
            status=status,
        )
        session.add(candidature)
        await session.flush()
        session.add(
            Kanban(
                candidature_id=candidature.id,
                user_id=user.id,
                status=status,
                position=position,
            )
        )
        session.add(
            Contact(
                candidature_id=candidature.id,
                name="Recruteuse",
                value="recruteuse@acme.test",
            )
        )
    await session.flush()
    return {"files": files}


async def count(session, model, *where) -> int:
    result = await session.execute(select(func.count()).select_from(model).where(*where))
    return result.scalar_one()


async def rows_of(session, user_id: uuid.UUID) -> dict[str, int]:
    """How many rows `user_id` owns in each table, children included."""
    owned_conversations = select(ChatConversation.id).where(
        ChatConversation.user_id == user_id
    )
    owned_candidatures = select(Candidature.id).where(Candidature.user_id == user_id)
    return {
        "users": await count(session, User, User.id == user_id),
        "preferences": await count(session, Preference, Preference.user_id == user_id),
        "cvs": await count(session, CV, CV.user_id == user_id),
        "analyses": await count(session, Analyse, Analyse.user_id == user_id),
        "chat_conversations": await count(
            session, ChatConversation, ChatConversation.user_id == user_id
        ),
        "chat_messages": await count(
            session, ChatMessage, ChatMessage.conversation_id.in_(owned_conversations)
        ),
        "candidatures": await count(
            session, Candidature, Candidature.user_id == user_id
        ),
        "contacts": await count(
            session, Contact, Contact.candidature_id.in_(owned_candidatures)
        ),
        "kanban": await count(session, Kanban, Kanban.user_id == user_id),
    }


class TestRemoveUser:
    async def test_populate_really_fills_every_table(
        self, db_session, test_user, upload_root
    ):
        """Guards the tests below: an empty fixture would make them pass for nothing."""
        await populate(db_session, test_user, upload_root)
        counts = await rows_of(db_session, test_user.id)
        assert all(n > 0 for n in counts.values()), counts

    async def test_removes_every_row_of_the_user(
        self, db_session, test_user, upload_root
    ):
        await populate(db_session, test_user, upload_root)

        await AuthService(db_session).remove_user(str(test_user.id))

        assert await rows_of(db_session, test_user.id) == {
            "users": 0,
            "preferences": 0,
            "cvs": 0,
            "analyses": 0,
            "chat_conversations": 0,
            "chat_messages": 0,
            "candidatures": 0,
            "contacts": 0,
            "kanban": 0,
        }

    async def test_removes_the_uploaded_files(
        self, db_session, test_user, upload_root
    ):
        created = await populate(db_session, test_user, upload_root)
        assert all(path.exists() for path in created["files"])

        await AuthService(db_session).remove_user(str(test_user.id))

        assert not (upload_root / str(test_user.id)).exists()

    async def test_leaves_other_users_alone(
        self, db_session, test_user, other_user, upload_root
    ):
        """The deletion is scoped by user id at every level, folder included."""
        kept = await populate(db_session, other_user, upload_root)
        before = await rows_of(db_session, other_user.id)
        await populate(db_session, test_user, upload_root)

        await AuthService(db_session).remove_user(str(test_user.id))

        assert await rows_of(db_session, other_user.id) == before
        assert all(path.exists() for path in kept["files"])

    async def test_a_user_without_data_can_be_removed(
        self, db_session, test_user, upload_root
    ):
        """A fresh account has no CV, hence no upload folder at all."""
        await AuthService(db_session).remove_user(str(test_user.id))
        assert await count(db_session, User, User.id == test_user.id) == 0

    async def test_unknown_user_is_not_found(self, db_session, upload_root):
        with pytest.raises(NotFoundError):
            await AuthService(db_session).remove_user(str(uuid.uuid4()))

    async def test_a_failing_file_cleanup_does_not_undo_the_removal(
        self, db_session, test_user, upload_root, monkeypatch
    ):
        """
        The rows are gone once committed; reporting an error then would send the
        client back to retry against an account that no longer exists.
        """
        await populate(db_session, test_user, upload_root)

        async def broken(self, folder_path):
            raise PermissionError(folder_path)

        monkeypatch.setattr(
            "app.services.upload_servive.UploadService.remove_folder_recursively",
            broken,
        )

        await AuthService(db_session).remove_user(str(test_user.id))

        assert await count(db_session, User, User.id == test_user.id) == 0
        assert await count(db_session, CV, CV.user_id == test_user.id) == 0


class TestRemoveEndpoint:
    async def test_refuses_without_confirmation(self, db_session, test_user, upload_root):
        with pytest.raises(BadRequestError):
            await remove_user_endpoint(
                RemoveUserRequest(confirm=False),
                db=db_session,
                user_id=str(test_user.id),
            )
        assert await count(db_session, User, User.id == test_user.id) == 1

    async def test_removes_the_account_once_confirmed(
        self, db_session, test_user, upload_root
    ):
        await populate(db_session, test_user, upload_root)

        response = await remove_user_endpoint(
            RemoveUserRequest(confirm=True),
            db=db_session,
            user_id=str(test_user.id),
        )

        assert response.message
        assert await count(db_session, User, User.id == test_user.id) == 0


def test_every_table_is_covered():
    """
    Fails when a table is added without deciding how an account removal cleans
    it. Add it to `rows_of` (and to `populate`) once it is handled.
    """
    covered = {
        "users",
        "preferences",
        "cvs",
        "analyses",
        "chat_conversations",
        "chat_messages",
        "candidatures",
        "contacts",
        "kanban",
    }
    assert set(Base.metadata.tables) == covered

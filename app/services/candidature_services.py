
from app.schemas.candidature import CandidatureUpdate
from app.core.exceptions import NotFoundError
from sqlalchemy.ext.asyncio.session import AsyncSession
from app.models.kanban import Kanban
from app.repositories.candidature_repo import CandidatureRepository
from app.repositories.contact_repo import ContactRepository
from app.repositories.kanban_repo import KanbanRepository
from app.schemas.candidature import (
    CandidatureCreate,
    CandidatureMove,
    CandidatureMoveResponse,
    CandidatureResponse,
    CandidatureStatus,
    CandidatureSummary,
    KanbanBoardResponse,
)
from typing import get_args
from app.core.logging import get_logger
from app.factory.candidature_factory import CandidatureFactory
import uuid
logger = get_logger(__name__)

class CandidatureService:
    """
    Candidature use cases.

    Note on `status`: it is stored twice — on `candidatures.status` and on
    `kanban.status`. Every method here that writes a status must write both,
    in the same transaction. See the debt note on app/models/kanban.py for
    why, and how to repay it.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.candidature_repo = CandidatureRepository(db)
        self.contact_repo = ContactRepository(db)
        self.kanban_repo = KanbanRepository(db)

    async def create_candidature(self, inputs: CandidatureCreate, user_id: uuid.UUID) -> CandidatureResponse:
        candidature = CandidatureFactory.candidature_create_to_model(inputs, user_id)
        candidature = await self.candidature_repo.create_candidature(candidature)
        # Same transaction as the candidature itself: a card without a board
        # entry would sort last in every list until someone noticed.
        await self.kanban_repo.create_entry(
            candidature_id=candidature.id,
            user_id=user_id,
            status=candidature.status,
        )
        candidature_response = CandidatureFactory.candidature_model_to_response(candidature)
        logger.info(
                "Candidature created",
                extra={
                    "user_id": user_id,
                    "candidature_id": str(candidature.id),
                    "company": candidature.company_name,
                    "job_title": candidature.job_title
                },
            )  
        # Create contacts via repository
        #if inputs.contacts:
            #await self.contact_repo.create_many(candidature.id, inputs.contacts) 

        return candidature_response


    async def get_board(self, user_id: uuid.UUID) -> KanbanBoardResponse:
        """
        Builds the board: every column, cards already grouped and ordered.

        The client renders this as-is — it groups nothing and sorts nothing,
        which also removes any chance of the board and the API disagreeing on
        what order a column is in.

        Columns come from the CandidatureStatus literal rather than from the
        data, so an empty column is still returned. Dropping empty columns
        would make one disappear as its last card leaves, leaving nowhere to
        drop a card back into.
        """
        columns: dict[str, list[CandidatureSummary]] = {
            status: [] for status in get_args(CandidatureStatus)
        }

        for candidature, board_status in await self.candidature_repo.list_board_for_user(user_id):
            # A status outside the known set would otherwise be silently
            # dropped; give it a column rather than losing the card.
            columns.setdefault(board_status, []).append(
                CandidatureSummary.model_validate(candidature)
            )

        return KanbanBoardResponse(columns=columns)


    async def update_user_candidature(self, candidature_id: uuid.UUID, inputs: CandidatureUpdate, user_id: uuid.UUID) -> CandidatureResponse:
        candidature = await self.candidature_repo.get_by_user_and_id(user_id, candidature_id)
        if candidature is None:
            raise NotFoundError(resource="Candidature", resource_id=str(candidature_id))
        updated = await self.candidature_repo.update(candidature, **inputs.model_dump(exclude_none=True))
        # The generic update accepts `status` too. This is the write path that
        # gets forgotten — it reads as unrelated to the board — and it is how
        # the two status columns drift apart.
        if inputs.status is not None:
            entry = await self._ensure_entry(user_id, candidature_id, updated.status)
            await self.kanban_repo.set_status(entry, inputs.status)
        return CandidatureResponse.model_validate(updated)


    async def set_status_candidature(self, candidature_id: uuid.UUID, user_id: uuid.UUID, status: str) -> CandidatureResponse:
        candidature = await self.candidature_repo.get_by_user_and_id(user_id, candidature_id)
        if candidature is None:
            raise NotFoundError(resource="Candidature", resource_id=str(candidature_id))
        updated = await self.candidature_repo.update(candidature, status=status)
        # Coming from the status select, not the board: there is no drop index,
        # so the card lands at the end of its target column.
        entry = await self._ensure_entry(user_id, candidature_id, updated.status)
        await self.kanban_repo.set_status(entry, status)
        logger.info(
                "Candidature status updated",
                extra={
                    "user_id": user_id,
                    "candidature_id": str(candidature_id),
                    "new_status": status,
                },
            )
        return CandidatureResponse.model_validate(updated)


    async def move_candidature(self, candidature_id: uuid.UUID, user_id: uuid.UUID, inputs: CandidatureMove) -> CandidatureMoveResponse:
        """
        Places a card at an explicit rank on the board (drag & drop).

        Unlike `set_status_candidature`, this one carries a drop point: the
        neighbours framing it decide the rank. It also mirrors the status onto
        `candidatures.status`, so a drag stays visible on the list view.
        """
        candidature = await self.candidature_repo.get_by_user_and_id(user_id, candidature_id)
        if candidature is None:
            raise NotFoundError(resource="Candidature", resource_id=str(candidature_id))

        entry = await self._ensure_entry(user_id, candidature_id, candidature.status)
        moved = await self.kanban_repo.move(
            entry,
            status=inputs.status,
            before_id=inputs.before_id,
            after_id=inputs.after_id,
        )
        await self.candidature_repo.update(candidature, status=inputs.status)

        logger.info(
                "Candidature moved on board",
                extra={
                    "user_id": user_id,
                    "candidature_id": str(candidature_id),
                    "new_status": moved.status,
                    "new_position": moved.position,
                },
            )
        return CandidatureMoveResponse(status=moved.status, position=moved.position)


    async def delete_user_candidature(self, candidature_id: uuid.UUID, user_id: uuid.UUID) -> None:
        candidature = await self.candidature_repo.get_by_user_and_id(user_id, candidature_id)
        if candidature is None:
            raise NotFoundError(resource="Candidature", resource_id=str(candidature_id))
        # The board entry goes with it via ON DELETE CASCADE. The hole it
        # leaves in the column's numbering is never filled back in — moves
        # compare positions, they do not index into them.
        await self.candidature_repo.delete(candidature)
        logger.info(
                "Candidature deleted",
                extra={
                    "user_id": user_id,
                    "candidature_id": str(candidature_id),
                },
            )  


    async def delete_all_user_candidature(self, user_id: uuid.UUID) -> None:
        await self.candidature_repo.delete_all_user_candidature(user_id)
        logger.info(
                "All candidatures deleted",
                extra={
                    "user_id": user_id,
                },
            )  


    async def _ensure_entry(self, user_id: uuid.UUID, candidature_id: uuid.UUID, status: str) -> Kanban:
        """
        Returns the board entry of a candidature, creating it if it is missing.

        Every candidature should have one — the migration backfilled the
        existing rows and creation makes one — but a missing entry would
        otherwise turn an ordinary status change into a 500.
        """
        entry = await self.kanban_repo.get_by_candidature(user_id, candidature_id)
        if entry is not None:
            return entry
        return await self.kanban_repo.create_entry(
            candidature_id=candidature_id,
            user_id=user_id,
            status=status,
        )

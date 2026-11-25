"""
CV parsing service — extracts plain text from PDF, DOCX, and TXT files.
"""

from app.services.extract_text_service import ExtractTextService
from app.core.config import settings
from app.services.upload_servive import UploadService
from app.services.cv_parser_services import CVParserService
from fastapi import UploadFile
from app.services.cv_upload_services import CVUploadService
from app.core.exceptions import CVTextUnreadableError, NotFoundError
from app.schemas.cv import CVUpdateRequest
from app.repositories.cv_repo import CVRepository
from app.factory.cv_factory import CVFactory
from app.schemas.cv_upload import CVUploadResult
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger
from app.models.cv import CV
import asyncio
import uuid
from pathlib import Path

logger = get_logger(__name__)


class CVService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cv_repo = CVRepository(db)
        self.cv_upload_service = CVUploadService()
        self.cv_parser = CVParserService()
        self.upload_service = UploadService()

    
    async def get_user_cvs(self, user_id: str) -> list[CV]:
        """
        Get all CVs for a user.
        """
        pass

    async def extract_stored_text(self, file_path: str) -> str | None:
        """
        Reads the text of a CV file that is already on disk.

        Returns None rather than raising when nothing can be read (scanned
        PDF, corrupted or missing file): a CV that cannot be read is still a
        CV the user may want to keep, and the failure is reported later, when
        an analysis actually needs the text.
        """
        try:
            # Parsing (OCR included) is blocking work: keep it off the event loop.
            text = await asyncio.to_thread(ExtractTextService().extract_text, Path(file_path))
        except Exception as exc:
            logger.warning(
                "CV text could not be extracted",
                exc_info=exc,
                extra={"file_path": file_path},
            )
            return None
        return text.strip() or None

    async def resolve_text(self, user_id: uuid.UUID, cv_id: uuid.UUID) -> str:
        """
        The text of one of the user's CVs, ready to be analysed.

        Uses the text stored at upload. A CV uploaded before that column existed,
        or whose first read failed, is read from its file once more and the
        result kept for next time.

        Raises:
            NotFoundError:        The CV does not exist or is not the user's.
            CVTextUnreadableError: No text can be read from the file.
        """
        cv = await self.cv_repo.get_by_user_and_id(user_id, cv_id)
        if cv is None:
            raise NotFoundError(resource="CV", resource_id=str(cv_id))
        if cv.extracted_text:
            return cv.extracted_text

        text = await self.extract_stored_text(CVFactory.get_absolute_cv_path(cv))
        if not text:
            raise CVTextUnreadableError(
                detail="No text could be extracted from the CV file.",
                context={"cv_id": str(cv_id)},
            )
        cv.extracted_text = text
        await self.db.flush()
        return text

    async def create_cv(self, user_id: str, input: CVUploadResult) -> CV:
        """
        Create a new CV for a user.
        """
       
        cv = CVFactory.create_from_upload_result_to_model(user_id, input)
        await self.cv_repo.create_cv(cv)
        return cv

    async def update_cv(self, cv_id: uuid.UUID, inputs: CVUpdateRequest) -> CV:
        """
        Update a CV for a user.
        """
        existing_cv = await self.cv_repo.get_by_id(cv_id)
        inputs_dict = inputs.model_dump(exclude_none=True) if hasattr(inputs, "model_dump") else inputs

        if not existing_cv:
            raise NotFoundError(resource="CV", resource_id=cv_id)
        
        CVFactory.update_request_to_model(existing_cv, inputs_dict)

        await self.cv_repo.update_cv(cv_id, inputs_dict)
        return existing_cv

    async def delete_cv(self, cv_id: uuid.UUID) -> None:
        """
        Delete a CV for a user.
        """
        cv = await self.cv_repo.get_by_id(cv_id)
        if cv is None:
            raise NotFoundError(resource="CV", resource_id=str(cv_id))
        await self.cv_repo.delete_cv(cv_id)
        await self.cv_upload_service.unlink_cv_file(cv)
        logger.info("CV deleted", extra={"cv_id": str(cv_id)})
        
        
    async def get_user_default_cv(self, user_id: str) -> CV:
        """
        Get the default CV for a user.
        """
        pass

    async def set_default_cv(self, user_id: uuid.UUID, cv_id: uuid.UUID) -> CV:
        """
        Set a CV as the default for a user.
        """
        cv = await self.cv_repo.get_by_user_and_id(user_id, cv_id)
        if cv is None:
            raise NotFoundError(resource="CV", resource_id=str(cv_id))

        await self.cv_repo.set_default(user_id, cv_id)

    async def remove_all_user_cvs(self, user_id: uuid.UUID) -> None:
        """
        Remove all CVs for a user.
        """
        await self.cv_upload_service.unlink_all_cv_files(str(user_id))
        await self.cv_repo.remove_all_user_cvs(user_id)
        logger.info("All CVs deleted", extra={"user_id": str(user_id)})

    async def extract_cv_text(self, cv_file: UploadFile, user_id: str) -> str:
        """
        Extract text from a CV file (PDF, DOCX or TXT).

        Raises:
            UnsupportedFileTypeError: The file extension is not supported.
            InternalError:            The file could not be parsed.
        """
        key = self.upload_service.generate_file_key(cv_file)
        file_path = await self.upload_service.save_file(cv_file, user_id, settings.cv_dir, key)
        extract_text_service = ExtractTextService()
        try:
            # Dispatch on the extension — hardcoding the PDF parser made every
            # DOCX and TXT upload fail with a 500.
            return extract_text_service.extract_text(Path(file_path))
        finally:
            # The upload is a scratch copy: remove it even when parsing fails.
            await self.upload_service.remove_file(file_path)


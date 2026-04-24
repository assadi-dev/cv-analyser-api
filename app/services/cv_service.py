"""
CV parsing service — extracts plain text from PDF, DOCX, and TXT files.
"""

from app.services.cv_upload_services import CVUploadService
from app.core.exceptions import NotFoundError
from app.schemas.cv import CVUpdateRequest
from app.repositories.cv_repo import CVRepository
from app.factory.cv_factory import CVFactory
from app.schemas.cv_upload import CVUploadResult
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger
from app.models.cv import CV
import uuid

logger = get_logger(__name__)


class CVService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cv_repo = CVRepository(db)
        self.cv_upload_service = CVUploadService()

    
    async def get_user_cvs(self, user_id: str) -> list[CV]:
        """
        Get all CVs for a user.
        """
        pass
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
        await self.cv_upload_service.unlink_all_cv_files(user_id)
        await self.cv_repo.remove_all_user_cvs(user_id)
        logger.info("All CVs deleted", extra={"user_id": user_id})





"""
CV parsing service — extracts plain text from PDF, DOCX, and TXT files.
"""

from app.repositories.cv_repo import CVRepository
from app.factory.cv_factory import CVFactory
from app.schemas.cv_upload import CVUploadResult
from pathlib import Path
from app.core.exceptions import InternalError, UnsupportedFileTypeError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger
from app.models.cv import CV

logger = get_logger(__name__)


class CVService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cv_repo = CVRepository(db)

    
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
        await self.cv_repo.create(cv)
        print(cv.id)

        return cv

    async def update_cv(self, cv: CV) -> CV:
        """
        Update a CV for a user.
        """
        pass

    async def delete_cv(self, cv: CV) -> CV:
        """
        Delete a CV for a user.
        """
        pass
        
    async def get_user_default_cv(self, user_id: str) -> CV:
        """
        Get the default CV for a user.
        """
        pass

    async def set_default_cv(self, user_id: str, cv_id: str) -> CV:
        """
        Set a CV as the default for a user.
        """
        pass

    async def remove_all_user_cvs(self, user_id: str) -> None:
        """
        Remove all CVs for a user.
        """
        pass
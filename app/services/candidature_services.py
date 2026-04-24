
from app.schemas.candidature import CandidatureStatusResponse
from app.schemas.common import DeleteResponse
from app.schemas.candidature import CandidatureUpdate
from app.core.exceptions import NotFoundError
from sqlalchemy.ext.asyncio.session import AsyncSession
from app.repositories.candidature_repo import CandidatureRepository
from app.repositories.contact_repo import ContactRepository
from app.schemas.candidature import CandidatureCreate, CandidatureResponse
from app.core.logging import get_logger
from app.factory.candidature_factory import CandidatureFactory
import uuid
logger = get_logger(__name__)

class CandidatureService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.candidature_repo = CandidatureRepository(db)
        self.contact_repo = ContactRepository(db)

    async def create_candidature(self, inputs: CandidatureCreate, user_id: uuid.UUID) -> CandidatureResponse:
        candidature = CandidatureFactory.candidature_create_to_model(inputs, user_id)
        candidature = await self.candidature_repo.create_candidature(candidature)
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


    async def update_user_candidature(self, candidature_id: uuid.UUID, inputs: CandidatureUpdate, user_id: uuid.UUID) -> CandidatureResponse:
        candidature = await self.candidature_repo.get_by_user_and_id(user_id, candidature_id)
        if candidature is None:
            raise NotFoundError(resource="Candidature", resource_id=str(candidature_id))
        updated = await self.candidature_repo.update(candidature, **inputs.model_dump(exclude_none=True))
        return CandidatureResponse.model_validate(updated)


    async def set_status_candidature(self, candidature_id: uuid.UUID, user_id: uuid.UUID, status: str) -> CandidatureStatusResponse:
        candidature = await self.candidature_repo.get_by_user_and_id(user_id, candidature_id)
        if candidature is None:
            raise NotFoundError(resource="Candidature", resource_id=str(candidature_id))
        updated = await self.candidature_repo.update(candidature, status=status)
        return CandidatureStatusResponse(id=updated.id, status=updated.status)

    async def delete_user_candidature(self, candidature_id: uuid.UUID, user_id: uuid.UUID) -> None:
        candidature = await self.candidature_repo.get_by_user_and_id(user_id, candidature_id)
        if candidature is None:
            raise NotFoundError(resource="Candidature", resource_id=str(candidature_id))
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
        
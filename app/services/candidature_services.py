
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
        print(candidature.contract_type)
      
       
        # Create contacts via repository
        """   if inputs.contacts:
            await self.contact_repo.create_many(candidature.id, inputs.contacts) 
        """

       # await self.db.refresh(candidature)

        """   logger.info(
                "Candidature created",
                extra={
                    "user_id": user_id,
                    "candidature_id": str(candidature.id),
                    "company": candidature.company_name,
                },
            ) """

   
import uuid
from app.models.candidature import Candidature
from app.schemas.candidature import CandidatureCreate


class CandidatureFactory:
    """
    Candidature factory — creates candidature models from different input types.
    """
    @staticmethod
    def candidature_create_to_model(inputs: CandidatureCreate, user_id: uuid.UUID) -> Candidature:
        """
        Create a candidature model from a create request.
        """
        return Candidature(
            id=uuid.uuid4(),
            user_id=user_id,
            company_name=inputs.company_name,
            company_city=inputs.company_city,
            company_region=inputs.company_region,
            company_country=inputs.company_country,
            job_title=inputs.job_title,
            contract_type=inputs.contract_type,
            work_mode=inputs.work_mode,
            source_platform=inputs.source_platform,
            source_name=inputs.source_name,
            source_url=inputs.source_url,
            status=inputs.status,
            notes=inputs.notes,
            cv_id=inputs.cv_id,
        
        )

    
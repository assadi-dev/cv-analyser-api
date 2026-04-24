from app.schemas.candidature import CandidatureResponse
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



    @staticmethod
    def candidature_model_to_response(candidature: Candidature) -> CandidatureResponse:
        """
        Convert a candidature model to a response schema.
        """
        return CandidatureResponse(
            id=candidature.id,
            cv_id=candidature.cv_id,
            company_name=candidature.company_name,
            company_city=candidature.company_city,
            company_region=candidature.company_region,
            company_country=candidature.company_country,
            job_title=candidature.job_title,
            contract_type=candidature.contract_type,
            work_mode=candidature.work_mode,
            source_platform=candidature.source_platform,
            source_name=candidature.source_name,
            source_url=candidature.source_url,
            status=candidature.status,
            notes=candidature.notes,
            created_at=candidature.created_at,
            updated_at=candidature.updated_at,
        )

    
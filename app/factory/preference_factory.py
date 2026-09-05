from app.schemas.preference import ProviderPreferencesResponse
from app.schemas.preference import PreferencesResponseByUser
from app.core.preferences import PreferencesDefaultConfigs
from app.models.preference import Preference

class PreferenceFactory:
    def __init__(self):
        pass

    @staticmethod
    def generate_model(user_id: str) -> Preference:
        return Preference(
            user_id=user_id,
            ai_provider=PreferencesDefaultConfigs.ai_provider,
            ai_model=PreferencesDefaultConfigs.ai_model,
            ai_base_url=PreferencesDefaultConfigs.ai_base_url,
            preferred_language=PreferencesDefaultConfigs.preferred_language,
            ats_threshold=PreferencesDefaultConfigs.ats_threshold,
            recommendation_detail=PreferencesDefaultConfigs.recommendation_detail,
        )

    @staticmethod
    def generate_responseByUser(preference: Preference) -> PreferencesResponseByUser:
        return PreferencesResponseByUser(
            ai_provider=preference.ai_provider,
            ai_model=preference.ai_model,
            ai_base_url=preference.ai_base_url,
            preferred_language=preference.preferred_language,
            ats_threshold=preference.ats_threshold,
            recommendation_detail=preference.recommendation_detail,
            created_at=preference.created_at,
            updated_at=preference.updated_at,
        )


    @staticmethod
    def generate_provider_preferences(preference: Preference) -> ProviderPreferencesResponse:
        return ProviderPreferencesResponse(
            ai_provider=preference.ai_provider,
            ai_model=preference.ai_model,
            ai_base_url=preference.ai_base_url,
            ai_api_key_encrypted=preference.ai_api_key_encrypted,
            preferred_language=preference.preferred_language,
        )
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
            ollama_base_url=PreferencesDefaultConfigs.ollama_base_url,
            preferred_language=PreferencesDefaultConfigs.preferred_language,
            ats_threshold=PreferencesDefaultConfigs.ats_threshold,
            recommendation_detail=PreferencesDefaultConfigs.recommendation_detail,
        )
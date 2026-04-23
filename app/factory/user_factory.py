from app.models.user import User
from app.schemas.auth import RegisterRequest
class UserFactory:
    def __init__(self):
        pass

    @staticmethod
    def register_request_to_model(inputs: RegisterRequest) -> User:
        return User(
            email=inputs.email,
            first_name=inputs.first_name,
            last_name=inputs.last_name,
            password=inputs.password,
            auth_provider=inputs.auth_provider,
            auth_provider_id=inputs.auth_provider_id,
            professional_title=inputs.professional_title,
            avatar_url=inputs.avatar_url,
            email_verified=inputs.email_verified
        )
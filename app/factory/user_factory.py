import json
from app.schemas.encryption import DecryptionPayload
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


    @staticmethod
    def update_request_to_model(user: User, inputs: dict) -> User:
        """Updates an existing user model with input data."""
        for key, value in inputs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        return user


    @staticmethod
    def decrypt_request_to_user_model(inputs: str) -> User:
        json_data = json.loads(inputs)   
        return User(
            email=json_data.get("email"),
            first_name=json_data.get("first_name"),
            last_name=json_data.get("last_name"),
            password=json_data.get("password") or None,
            auth_provider=json_data.get("auth_provider") or None,
            professional_title=json_data.get("professional_title") or None,
            avatar_url=json_data.get("avatar_url") or None,
            email_verified=json_data.get("email_verified") or False
        )
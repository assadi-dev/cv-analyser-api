from app.core.security import create_api_token, get_jwt_payload
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.core.config import settings

class TokenResponseFactory:
    @staticmethod
    def build_token_response(user_id: str) -> TokenResponse:
        api_token = create_api_token(str(user_id))
        payload = get_jwt_payload(api_token)

        return TokenResponse(
            token=api_token,
            type="bearer",
            expires_at=payload.exp,
            expires_in_days=settings.api_token_expire_days,
        )
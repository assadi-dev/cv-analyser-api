


from app.core.security import create_api_token,verify_password,hash_password
from app.schemas.auth import LoginResponse
from app.schemas.auth import LoginRequest
from app.core.logging import get_logger
from app.repositories.user_repo import UserRepository
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.services.auth_validation import validate_auth_provider_fields
from fastapi.exceptions import HTTPException
from app.core.exceptions import BadRequestError
from sqlalchemy.ext.asyncio import AsyncSession


logger = get_logger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)


    async def register_user(self, inputs: RegisterRequest) -> User:
        """
        Register a new user.
        """
        user = await self.user_repo.get_by_email(inputs.email)
        if user:
            raise HTTPException(status_code=400, detail="User already exists")

        validate_auth_provider_fields(inputs)

        hashed_password = hash_password(inputs.password)
    
        user = User(
            email=inputs.email,
            first_name=inputs.first_name,
            last_name=inputs.last_name,
            password=hashed_password,
            auth_provider=inputs.auth_provider,
            auth_provider_id=inputs.auth_provider_id,
        )
        user = await self.user_repo.create_user(user)
        return user



    async def login_user(self, inputs: LoginRequest) -> User:
        """
        Login a user.
        """
        user = await self.user_repo.get_by_email(inputs.email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if inputs.auth_provider == "email":
            if not verify_password(inputs.password, user.password):
                raise HTTPException(status_code=401, detail="Invalid credentials")

        api_token = create_api_token(str(user.id))

        return  user

    async def remove_user(self, user_id: str) -> None:
        """
        Delete a user account.
        """


        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            # Should not happen as it is called behind auth, but better be safe
            from app.core.exceptions import NotFoundError
            raise NotFoundError(resource="User", resource_id=user_id)

        await self.user_repo.delete_user(user)
        await self.db.commit()
        logger.info(f"User {user_id} removed successfully")
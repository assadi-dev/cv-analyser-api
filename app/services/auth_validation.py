

from fastapi.exceptions import HTTPException
from app.schemas.auth import RegisterRequest
import bcrypt

def validate_auth_provider(auth_provider: str) -> bool:
    """
    Validate the auth provider.
    """
    return auth_provider in ["email", "google", "linkedin"]


def validate_password(password: str) -> bool:
    """
    Validate the password.
    """
    return len(password) >= 8


def validate_auth_provider_id(auth_provider_id: str) -> bool:
    """
    Validate the auth provider ID.
    """
    return len(auth_provider_id) > 0

def validate_auth_provider_fields(body: RegisterRequest):
    """
    Validate the auth provider fields.
    """
    if body.auth_provider == "email":
        if not body.password:
            raise HTTPException(status_code=400, detail="Password is required for email authentication")

    if body.auth_provider == "google":
        if not body.auth_provider_id:
            raise HTTPException(status_code=400, detail="Auth provider ID is required for google authentication")

    if body.auth_provider == "linkedin":
        if not body.auth_provider_id:
            raise HTTPException(status_code=400, detail="Auth provider ID is required for linkedin authentication")



def hash_password(password: str) -> str:
    """
    Hash the password.
    """
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed_password.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify the password.
    """
    return bcrypt.checkpw(password, hashed_password)
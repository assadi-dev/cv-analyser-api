"""
Unit tests for the security module.

Tests JWT token creation, decoding, and error cases.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from jose import jwt

from app.core.exceptions import ExpiredTokenError, InvalidTokenError
from app.core.security import create_api_token, decode_api_token


class TestCreateAPIToken:
    """Tests for API token creation."""

    def test_returns_string(self):
        user_id = str(uuid.uuid4())
        token = create_api_token(user_id)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_is_valid_jwt(self):
        from app.core.config import settings
        user_id = str(uuid.uuid4())
        token = create_api_token(user_id)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == user_id

    def test_token_has_correct_type(self):
        from app.core.config import settings
        token = create_api_token(str(uuid.uuid4()))
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["type"] == "api_token"

    def test_token_has_expiry(self):
        from app.core.config import settings
        token = create_api_token(str(uuid.uuid4()))
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert "exp" in payload
        assert "iat" in payload

    def test_different_users_get_different_tokens(self):
        token1 = create_api_token(str(uuid.uuid4()))
        token2 = create_api_token(str(uuid.uuid4()))
        assert token1 != token2


class TestDecodeAPIToken:
    """Tests for API token decoding and validation."""

    def test_valid_token_returns_user_id(self):
        user_id = str(uuid.uuid4())
        token = create_api_token(user_id)
        decoded_id = decode_api_token(token)
        assert decoded_id == user_id

    def test_invalid_signature_raises_error(self):
        from app.core.config import settings
        user_id = str(uuid.uuid4())
        payload = {
            "sub": user_id,
            "type": "api_token",
            "exp": datetime.now(timezone.utc) + timedelta(days=30),
        }
        # Sign with wrong key
        bad_token = jwt.encode(payload, "wrong-secret-key", algorithm=settings.algorithm)
        with pytest.raises(InvalidTokenError):
            decode_api_token(bad_token)

    def test_expired_token_raises_expired_error(self):
        from app.core.config import settings
        payload = {
            "sub": str(uuid.uuid4()),
            "type": "api_token",
            "iat": datetime.now(timezone.utc) - timedelta(days=31),
            "exp": datetime.now(timezone.utc) - timedelta(days=1),  # already expired
        }
        expired_token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
        with pytest.raises(ExpiredTokenError):
            decode_api_token(expired_token)

    def test_wrong_token_type_raises_error(self):
        from app.core.config import settings
        payload = {
            "sub": str(uuid.uuid4()),
            "type": "session_token",  # Wrong type
            "exp": datetime.now(timezone.utc) + timedelta(days=30),
        }
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
        with pytest.raises(InvalidTokenError):
            decode_api_token(token)

    def test_missing_sub_raises_error(self):
        from app.core.config import settings
        payload = {
            "type": "api_token",
            "exp": datetime.now(timezone.utc) + timedelta(days=30),
        }
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
        with pytest.raises(InvalidTokenError):
            decode_api_token(token)

    def test_malformed_token_raises_error(self):
        with pytest.raises(InvalidTokenError):
            decode_api_token("not.a.valid.jwt.token")

    def test_empty_token_raises_error(self):
        with pytest.raises(InvalidTokenError):
            decode_api_token("")

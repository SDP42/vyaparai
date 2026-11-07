import pytest

from app.core.config import DEV_JWT_SECRET, Settings
from app.core.errors import AuthenticationError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("s3cret-password")
    assert hashed.startswith("$argon2")
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong", hashed)


def test_token_roundtrip_and_tamper() -> None:
    settings = Settings(app_env="test")
    token, expires_in = create_access_token("user-1", settings)
    assert expires_in == settings.access_token_expire_minutes * 60
    assert decode_access_token(token, settings)["sub"] == "user-1"

    other = Settings(app_env="test", jwt_secret_key="x" * 40)
    with pytest.raises(AuthenticationError):
        decode_access_token(token, other)


def test_expired_token_rejected() -> None:
    settings = Settings(app_env="test", access_token_expire_minutes=-1)
    token, _ = create_access_token("user-1", settings)
    with pytest.raises(AuthenticationError):
        decode_access_token(token, settings)


def test_production_refuses_dev_secret() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(app_env="production", jwt_secret_key=DEV_JWT_SECRET, database_url="postgresql://x")


def test_production_refuses_sqlite() -> None:
    with pytest.raises(ValueError, match="PostgreSQL"):
        Settings(app_env="production", jwt_secret_key="y" * 40)

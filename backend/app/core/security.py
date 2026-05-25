import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


def hash_password(password: str) -> str:
    salt = hashlib.sha256(settings.secret_key.encode()).hexdigest()[:16]
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 100000
    ).hex() + ":" + salt


def verify_password(plain: str, hashed: str) -> bool:
    try:
        stored_hash, salt = hashed.rsplit(":", 1)
        computed = hashlib.pbkdf2_hmac(
            "sha256", plain.encode(), salt.encode(), 100000
        ).hex()
        return hmac.compare_digest(computed, stored_hash)
    except (ValueError, AttributeError):
        return False


def hash_api_key(key: str) -> str:
    return hash_password(key)


def verify_api_key(key: str, hashed: str) -> bool:
    return verify_password(key, hashed)

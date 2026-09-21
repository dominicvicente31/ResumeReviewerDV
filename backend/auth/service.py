import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
_EXPIRE_HOURS = int(os.environ.get("ACCESS_TOKEN_EXPIRE_HOURS", "24"))


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_EXPIRE_HOURS)
    payload = {"sub": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """Raise JWTError if the token is invalid or expired."""
    return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])

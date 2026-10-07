"""JWT authentication: login, access/refresh tokens, silent refresh rotation."""
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "90"))
APP_USERNAME = os.environ["APP_USERNAME"]
APP_PASSWORD_HASH = os.environ["APP_PASSWORD_HASH"]
REFRESH_TOKEN_DB_PATH = os.getenv(
    "REFRESH_TOKEN_DB_PATH",
    str(Path(__file__).resolve().parent / ".data" / "refresh_tokens.db"),
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()

router = APIRouter()

_refresh_store_lock = threading.Lock()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


def _create_token(subject: str, expires_delta: timedelta, token_type: str, jti: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": jti or str(uuid.uuid4()),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_access_token(subject: str) -> str:
    return _create_token(subject, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def _connect_refresh_store() -> sqlite3.Connection:
    database_path = Path(REFRESH_TOKEN_DB_PATH)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=10)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            jti TEXT PRIMARY KEY,
            subject TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    return connection


def _build_refresh_token(subject: str) -> tuple[str, str, int]:
    jti = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    token = _create_token(
        subject,
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "refresh",
        jti=jti,
    )
    return token, jti, int(expires_at.timestamp())


def create_refresh_token(subject: str) -> str:
    token, jti, expires_at = _build_refresh_token(subject)
    now = int(datetime.now(timezone.utc).timestamp())
    with _refresh_store_lock, _connect_refresh_store() as connection:
        connection.execute("DELETE FROM refresh_tokens WHERE expires_at <= ?", (now,))
        connection.execute(
            "INSERT INTO refresh_tokens (jti, subject, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (jti, subject, expires_at, now),
        )
    return token


def _rotate_refresh_token(old_jti: str, subject: str) -> str:
    token, new_jti, expires_at = _build_refresh_token(subject)
    now = int(datetime.now(timezone.utc).timestamp())

    with _refresh_store_lock, _connect_refresh_store() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM refresh_tokens WHERE expires_at <= ?", (now,))
        removed = connection.execute(
            "DELETE FROM refresh_tokens WHERE jti = ? AND subject = ?",
            (old_jti, subject),
        )
        if removed.rowcount != 1:
            connection.rollback()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token revoked or unknown",
            )
        connection.execute(
            "INSERT INTO refresh_tokens (jti, subject, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (new_jti, subject, expires_at, now),
        )
        connection.commit()

    return token


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    payload = _decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    return payload["sub"]


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest):
    if body.username != APP_USERNAME or not pwd_context.verify(body.password, APP_PASSWORD_HASH):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(
        access_token=create_access_token(body.username),
        refresh_token=create_refresh_token(body.username),
    )


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest):
    payload = _decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    jti = payload.get("jti")
    subject = payload.get("sub")
    if not isinstance(jti, str) or not isinstance(subject, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    new_refresh_token = _rotate_refresh_token(jti, subject)
    return TokenResponse(
        access_token=create_access_token(subject),
        refresh_token=new_refresh_token,
    )

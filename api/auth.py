"""
Authentication & authorization helpers.

Tokens are HS256 JWTs signed with `CU_QUIZ_SECRET`. They are minted in two places:

1. **Student quizzes**  each quiz.catsoop runs a server-side <python> block that
   reads `cs_user_info` and mints a JWT inline using `mint_student_token()`.
2. **Admin panel** `POST /admin/login` with the shared `CU_QUIZ_ADMIN_PASSWORD`
   exchanges the password for an admin JWT, stored client-side in localStorage.

Both flows share the same secret. Tokens carry `{sub, is_admin, exp}` and are
validated by `require_user` / `require_admin` FastAPI dependencies.
"""

import os
import time
import hmac
import json
import base64
import hashlib
import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request

logger = logging.getLogger(__name__)

SECRET = os.environ.get("CU_QUIZ_SECRET", "")
ADMIN_PASSWORD = os.environ.get("CU_QUIZ_ADMIN_PASSWORD", "")
ADMIN_USERS = {u.strip() for u in os.environ.get("CU_QUIZ_ADMINS", "").split(",") if u.strip()}
TOKEN_TTL_SECONDS = 8 * 60 * 60  # 8h

if not SECRET:
    logger.warning(
        "CU_QUIZ_SECRET is empty , auth tokens cannot be validated. "
        "Set CU_QUIZ_SECRET in run.sh before deploying."
    )


def mint_token(username: str, is_admin: bool, ttl: int = TOKEN_TTL_SECONDS) -> str:
    if not SECRET:
        raise RuntimeError("CU_QUIZ_SECRET not set")
    payload = {
        "sub": username,
        "is_admin": bool(is_admin),
        "exp": int(time.time()) + int(ttl),
        "iat": int(time.time()),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    if not SECRET:
        raise HTTPException(status_code=503, detail="Auth not configured")
    try:
        return jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.info("Rejected invalid token: %s", e)
        raise HTTPException(status_code=401, detail="Invalid token")


def _extract_token(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    qp = request.query_params.get("token")
    if qp:
        return qp
    return None


def require_user(request: Request) -> dict:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    claims = decode_token(token)
    if not claims.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid token claims")
    return {"username": claims["sub"], "is_admin": bool(claims.get("is_admin"))}


def require_admin(user: dict = Depends(require_user)) -> dict:
    if not user.get("is_admin"):
        logger.info("Admin denied for user=%s", user.get("username"))
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def verify_admin_password(password: str) -> bool:
    """Constant-time check of the shared admin password."""
    if not ADMIN_PASSWORD or not password:
        return False
    return hmac.compare_digest(password.encode(), ADMIN_PASSWORD.encode())


def is_admin_username(username: str) -> bool:
    return username in ADMIN_USERS

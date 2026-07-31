import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from auth import verify_token
from database import get_db_ctx

security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return payload


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Raise 403 unless the current user is the admin.

    Admin is determined by ADMIN_USER_ID env var, or the first registered user.
    """
    admin_env = os.getenv("ADMIN_USER_ID")
    if admin_env and user["sub"] == admin_env:
        return user
    with get_db_ctx() as conn:
        first = conn.execute(
            "SELECT id FROM users ORDER BY created_at ASC LIMIT 1"
        ).fetchone()
        if first and first["id"] == user["sub"]:
            return user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

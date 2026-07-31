from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth import hash_password, verify_password, create_token
from database import get_db_ctx
from routers.auth_deps import get_current_user

router = APIRouter()


# --- Auth ---

class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/register")
def register(payload: RegisterRequest):
    if not payload.username.strip() or not payload.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username and password required")

    with get_db_ctx() as conn:
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (payload.username.strip(),)).fetchone()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

        user_id = str(uuid4())
        pw_hash = hash_password(payload.password)
        conn.execute(
            "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
            (user_id, payload.username.strip(), pw_hash),
        )

    token = create_token(user_id, payload.username.strip())
    return {"token": token, "user": {"id": user_id, "username": payload.username.strip()}}


@router.post("/auth/login")
def login(payload: LoginRequest):
    with get_db_ctx() as conn:
        row = conn.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (payload.username,)).fetchone()
        if not row or not verify_password(payload.password, row["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token = create_token(row["id"], row["username"])
    return {"token": token, "user": {"id": row["id"], "username": row["username"]}}


@router.get("/auth/me")
def me(user: dict = Depends(get_current_user)):
    return {"id": user["sub"], "username": user["username"]}

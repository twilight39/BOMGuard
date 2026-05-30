"""Authentication endpoints via WorkOS (Google OAuth)."""

import mimetypes
import os
import secrets
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from bomguard.config import Settings
from bomguard.db import get_db
from bomguard.models.database import User
from bomguard.services.auth_service import WorkOSAuthService

settings = Settings()

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class UserUpdateRequest(BaseModel):
    name: str | None = None


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    """Redirect to WorkOS OAuth (Google)."""
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state

    auth_service = WorkOSAuthService()
    redirect_uri = str(request.url_for("auth_callback"))
    url = auth_service.get_authorization_url(redirect_uri=redirect_uri, state=state)
    return RedirectResponse(url)


@router.get("/callback", name="auth_callback")
async def auth_callback(
    request: Request,
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Handle WorkOS OAuth callback."""
    if error:
        detail = error_description or error
        raise HTTPException(status_code=400, detail=f"OAuth error: {detail}")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth code or state")

    stored_state = request.session.get("oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    auth_service = WorkOSAuthService()
    auth_response = auth_service.authenticate_with_code(code)
    workos_user = auth_response.user

    user = db.query(User).filter_by(id=workos_user.id).first()
    if not user:
        user = User(
            id=workos_user.id,
            email=workos_user.email,
            name=workos_user.first_name or workos_user.email,
            avatar_url=workos_user.profile_picture_url,
        )
        db.add(user)
        db.commit()

    request.session["user_id"] = user.id
    request.session["email"] = user.email
    request.session["name"] = user.name

    return RedirectResponse(url=settings.frontend_url)


@router.post("/logout")
async def logout(request: Request) -> dict[str, Any]:
    """Clear session cookie."""
    request.session.clear()
    return {"status": "logged_out"}


@router.get("/me")
async def me(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return current user from session."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
    }


@router.patch("/me")
async def update_me(
    request: Request,
    body: UserUpdateRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Update current user's profile."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if body.name is not None:
        user.name = body.name
        # Sync to WorkOS
        auth_service = WorkOSAuthService()
        auth_service.update_user(user_id, first_name=body.name)
        request.session["name"] = body.name

    db.commit()

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
    }


@router.delete("/me")
async def delete_me(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Delete current user's account."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Delete from WorkOS
    auth_service = WorkOSAuthService()
    auth_service.delete_user(user_id)

    # Delete from local DB
    db.delete(user)
    db.commit()

    request.session.clear()
    return {"status": "deleted"}


AVATARS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static", "avatars")
os.makedirs(AVATARS_DIR, exist_ok=True)


@router.post("/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Upload a profile picture."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    ext = mimetypes.guess_extension(content_type) or ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(AVATARS_DIR, filename)

    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 2MB")

    # Remove old avatar file if it exists
    if user.avatar_url:
        old_filename = os.path.basename(user.avatar_url.split("?")[0])
        old_path = os.path.join(AVATARS_DIR, old_filename)
        if os.path.isfile(old_path):
            os.remove(old_path)

    with open(filepath, "wb") as f:
        f.write(contents)

    cache_buster = int(time.time())
    avatar_url = f"{str(request.base_url).rstrip('/')}/static/avatars/{filename}?v={cache_buster}"
    user.avatar_url = avatar_url
    db.commit()

    request.session["avatar_url"] = avatar_url

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
    }

"""Authentication endpoints via WorkOS (Google OAuth)."""

import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from bomguard.config import Settings
from bomguard.db import get_db
from bomguard.models.database import User
from bomguard.services.auth_service import WorkOSAuthService

settings = Settings()

router = APIRouter(prefix="/api/auth", tags=["Auth"])


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
async def me(request: Request) -> dict[str, Any]:
    """Return current user from session."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "id": user_id,
        "email": request.session.get("email"),
        "name": request.session.get("name"),
    }

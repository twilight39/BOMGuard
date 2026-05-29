# Plan: WorkOS Auth (`feat/auth-workos`)

## Goal
Add WorkOS-based frontend-only authentication to BOMGuard, enabling Google OAuth login that persists user identity for BOM ownership and regulation preferences. APIs remain open (no JWT validation on backend routes for now).

## Current State

### Backend
- **No `User` model** in `backend/bomguard/models/database.py` — no user table at all
- **No auth API endpoints** — no login, callback, logout, or session routes
- **No WorkOS SDK** — `python -c "import workos"` fails (not in `pyproject.toml`)
- `workos_api_key` and `workos_client_id` exist in `Settings` but are unused
- `Bom` model has no `user_id` column — ownership is un-tracked
- `SessionLocal` uses standard SQLAlchemy sessions — no session middleware

### Frontend
- **No auth state** — no React context, no user store, no login/logout UI
- `LandingPage` has "Upload BOM" and "Try a Sample" buttons with no auth gating
- `AppShell` sidebar shows all nav items to everyone — no conditional rendering
- No login page or callback route exists
- `services/api.ts` only has `fetchHealth()` — no auth-aware fetch wrapper

### Infrastructure
- CORS is configured with `allow_credentials=True` (good for cookies)
- PostgreSQL database is available for session storage
- Redis is available (but we’ll use signed cookies for sessions, not Redis)

## Architecture Decisions (Already Made)
- FastAPI + SQLAlchemy 2.0 + PostgreSQL on backend
- React 19 + TypeScript + TanStack Router + Tailwind v4 + shadcn/ui on frontend
- CORS `allow_credentials=True` (enables cookie-based sessions)
- **Frontend-only auth for now** — backend APIs remain open, no JWT gate
- **WorkOS** as the OAuth provider (Google login)

## Implementation Steps

### 1. Install WorkOS SDK

Add `workos>=5.0.0` to `backend/pyproject.toml` dependencies:
```toml
dependencies = [
    # ... existing deps ...
    "workos>=5.0.0",
]
```

Run:
```bash
cd backend && uv add workos>=5.0.0
```

### 2. Database: Add `User` and `UserPreference` Models

Modify `backend/bomguard/models/database.py`:

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # WorkOS user ID
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    boms: Mapped[list["Bom"]] = relationship("Bom", back_populates="user")
    preferences: Mapped["UserPreference | None"] = relationship(
        "UserPreference", back_populates="user", uselist=False
    )


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), primary_key=True)
    subscribed_regulation_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    default_regulation_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship("User", back_populates="preferences")
```

Add `user_id` to `Bom`:
```python
class Bom(Base):
    # ... existing columns ...
    user_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("users.id"))
    
    user: Mapped["User | None"] = relationship("User", back_populates="boms")
```

Generate Alembic migration:
```bash
cd backend && alembic revision --autogenerate -m "add users and user_preferences tables"
```

### 3. Backend: WorkOS Auth Service

Create `backend/bomguard/services/auth_service.py`:
```python
class WorkOSAuthService:
    """Wraps WorkOS SDK for OAuth + user management."""
    
    def __init__(self) -> None:
        self.client = WorkOSClient(api_key=settings.workos_api_key)
        self.client_id = settings.workos_client_id
    
    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Build WorkOS OAuth authorization URL."""
        return self.client.user_management.get_authorization_url(
            provider="GoogleOAuth",
            redirect_uri=redirect_uri,
            state=state,
            client_id=self.client_id,
        )
    
    def authenticate_with_code(self, code: str) -> AuthenticateWithCodeResponse:
        """Exchange authorization code for user info."""
        return self.client.user_management.authenticate_with_code(
            code=code,
            client_id=self.client_id,
        )
    
    def get_user(self, user_id: str) -> UserResponse:
        """Fetch user from WorkOS."""
        return self.client.user_management.get_user(user_id)
```

### 4. Backend: Session Middleware

Create `backend/bomguard/middleware/session.py`:
- Use `itsdangerous.Signer` or `starlette.middleware.sessions.SessionMiddleware` for signed cookie sessions
- Store `user_id`, `email`, `name` in session cookie
- Session cookie settings: `httponly=True`, `secure=False` for dev (set `secure=True` in prod), `samesite="lax"`, `max_age=7 days`

Add to `create_app()` in `main.py`:
```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key or "dev-secret-change-in-prod",
    max_age=604800,  # 7 days
    same_site="lax",
    https_only=False,  # True in prod
)
```

**Need to add `secret_key` to `Settings`** in `config.py`:
```python
secret_key: str = "dev-secret-change-in-prod"
```

### 5. Backend: Auth API Endpoints

Create `backend/bomguard/api/auth.py`:
```python
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

@router.get("/callback")
async def auth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Handle WorkOS OAuth callback."""
    # Verify state
    stored_state = request.session.get("oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    
    # Exchange code for user
    auth_service = WorkOSAuthService()
    auth_response = auth_service.authenticate_with_code(code)
    
    # Get or create user in DB
    user = db.query(User).filter_by(id=auth_response.user.id).first()
    if not user:
        user = User(
            id=auth_response.user.id,
            email=auth_response.user.email,
            name=getattr(auth_response.user, "first_name", None) or auth_response.user.email,
        )
        db.add(user)
        db.commit()
    
    # Set session
    request.session["user_id"] = user.id
    request.session["email"] = user.email
    request.session["name"] = user.name
    
    return RedirectResponse(url="/")

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
```

Register the router in `main.py`:
```python
from bomguard.api.auth import router as auth_router
app.include_router(auth_router)
```

### 6. Frontend: Auth Context & Hook

Create `frontend/src/contexts/AuthContext.tsx`:
```typescript
interface AuthUser {
  id: string
  email: string
  name: string | null
}

interface AuthContextValue {
  user: AuthUser | null
  isLoading: boolean
  login: () => void
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  
  useEffect(() => {
    fetch(`${API_BASE}/api/auth/me`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(data => setUser(data))
      .finally(() => setIsLoading(false))
  }, [])
  
  const login = () => {
    window.location.href = `${API_BASE}/api/auth/login`
  }
  
  const logout = async () => {
    await fetch(`${API_BASE}/api/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    })
    setUser(null)
    window.location.reload()
  }
  
  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be inside AuthProvider')
  return ctx
}
```

Wrap the app in `main.tsx`:
```typescript
<AuthProvider>
  <RouterProvider router={router} />
</AuthProvider>
```

### 7. Frontend: Login UI in AppShell

Modify `frontend/src/components/layout/AppShell.tsx`:
- In the sidebar footer (currently showing "v0.1.0"), add a user section:
  - If logged in: show name/avatar + Logout button
  - If not logged in: show "Sign in with Google" button
- Use `useAuth()` hook
- Keep the sidebar nav items visible regardless of auth (APIs are open)

```tsx
function UserSection() {
  const { user, isLoading, login, logout } = useAuth()
  
  if (isLoading) return <div className="text-xs text-muted-foreground">Loading...</div>
  
  if (user) {
    return (
      <div className="space-y-2">
        <div className="text-sm font-medium">{user.name || user.email}</div>
        <Button variant="ghost" size="sm" onClick={logout}>Logout</Button>
      </div>
    )
  }
  
  return (
    <Button variant="outline" size="sm" onClick={login}>
      Sign in with Google
    </Button>
  )
}
```

### 8. Frontend: Update API Fetch Wrapper

Update `frontend/src/services/api.ts`:
```typescript
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function apiFetch(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',  // Send cookies with every request
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })
  return res
}

export async function fetchHealth() {
  const res = await apiFetch('/api/health')
  return res.json()
}

export async function fetchMe() {
  const res = await apiFetch('/api/auth/me')
  if (!res.ok) return null
  return res.json()
}
```

### 9. Update BOM Endpoints to Track Ownership (Optional but Recommended)

When a user uploads a BOM, set `user_id` from session. Since APIs are open, make `user_id` nullable:

Modify `backend/bomguard/api/boms.py`:
```python
from fastapi import Request

@router.post("/upload")
async def upload_bom(
    file: UploadFile,
    request: Request,
    db: Session = Depends(get_db),
) -> BomUploadResponse:
    user_id = request.session.get("user_id")
    # ... create BOM with user_id=user_id ...
```

### 10. Tests

Backend:
- `test_auth_service.py` — mock WorkOS client, test URL generation, test code exchange
- `test_auth_api.py` — test `/login` redirect, test `/callback` with mocked WorkOS, test `/me` with/without session, test `/logout`
- Use `TestClient` with `SessionMiddleware` configured

Frontend:
- No component tests yet (no test setup in `package.json`). Skip for now.

### 11. Lint / Type-Check / Test

```bash
cd backend && ruff check . && mypy . && basedpyright . && pytest tests/
cd frontend && npm run lint && npm run type-check && npm run build
```

## Key Files to Create/Modify

| Action | File |
|--------|------|
| Create | `backend/bomguard/services/auth_service.py` |
| Create | `backend/bomguard/api/auth.py` |
| Create | `backend/tests/test_services/test_auth_service.py` |
| Create | `backend/tests/test_api/test_auth_api.py` |
| Create | `frontend/src/contexts/AuthContext.tsx` |
| Modify | `backend/pyproject.toml` (add `workos` dep) |
| Modify | `backend/bomguard/models/database.py` (add `User`, `UserPreference`, `user_id` on `Bom`) |
| Modify | `backend/bomguard/models/schemas.py` (add `UserSchema`, `UserPreferenceSchema`) |
| Modify | `backend/bomguard/config.py` (add `secret_key`) |
| Modify | `backend/bomguard/main.py` (add `SessionMiddleware`, include auth router) |
| Modify | `backend/bomguard/api/boms.py` (read `user_id` from session) |
| Modify | `frontend/src/components/layout/AppShell.tsx` (add user section) |
| Modify | `frontend/src/services/api.ts` (add `credentials: 'include'`) |
| Modify | `frontend/src/main.tsx` (wrap in `AuthProvider`) |
| Generate | Alembic migration for new tables |

## Notes

- **WorkOS v5 SDK**: The API changed significantly from v4. Make sure to use the v5 API (`WorkOSClient`, `user_management.authenticate_with_code`, etc.).
- **State parameter**: Required for CSRF protection in OAuth. Store in session, verify on callback.
- **Cookie security**: `secure=False` in dev (localhost is HTTP). In production, set `secure=True` and use HTTPS.
- **Session secret**: `secret_key` defaults to a dev value. Must be changed in production via env var.
- **Frontend-only auth**: The backend APIs do NOT validate sessions on every request. This is intentional — the auth is for ownership tracking and UI personalization only. Future branches can add `@require_auth` decorators.
- **BOM ownership**: Since `user_id` is nullable, unauthenticated uploads still work. This is intentional for the open demo experience.
- **No JWT**: We use server-side signed cookies (SessionMiddleware) instead of JWT. This is simpler, supports logout natively, and avoids token refresh complexity. The trade-off is slightly larger request headers (cookie size).
- **WorkOS Org/SSO**: Not in scope. Only Google OAuth via WorkOS.

"""
Authentication router: register, login, and current-user endpoints.
Business logic lives in auth_service; security helpers in utils/security.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    UserRegister,
    LoginRequest,
    UserLogin,
    UserResponse,
    TokenResponse,
)
from app.services.auth_service import (
    register_user,
    authenticate_user,
    create_user_token,
)
from app.utils.security import decode_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

# OAuth2 scheme — Swagger UI will show an "Authorize" button
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# ---------------------------------------------------------------------------
# Dependency: get current authenticated user from JWT
# ---------------------------------------------------------------------------
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode the Bearer token and return the corresponding User."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    sub: str | None = payload.get("sub")
    if sub is None:
        raise credentials_exception

    user = db.query(User).filter(User.username == sub).first()
    if user is None and str(sub).isdigit():
        user = db.query(User).filter(User.id == int(sub)).first()

    if user is None:
        raise credentials_exception

    return user


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user. Returns the user without password_hash."""
    try:
        user = register_user(db, user_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return user


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------
@router.post("/login", response_model=TokenResponse)
def login(
    user_data: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate and return a JWT access token.
    Accepts application/json with username and password.
    """
    try:
        user = authenticate_user(db, user_data)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_user_token(user)
    return TokenResponse(access_token=access_token)


# ---------------------------------------------------------------------------
# POST /auth/token
# ---------------------------------------------------------------------------
@router.post("/token", response_model=TokenResponse)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    OAuth2 compatible token login, required for Swagger UI Authorize button.
    Accepts application/x-www-form-urlencoded with username and password.
    """
    try:
        user = authenticate_user(db, form_data)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_user_token(user)
    return TokenResponse(access_token=access_token)


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user

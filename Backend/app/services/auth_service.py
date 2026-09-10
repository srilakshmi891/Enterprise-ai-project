from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.user import User
import logging
from app.schemas.auth import UserRegister, UserLogin
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
)


def register_user(db: Session, user_data: UserRegister) -> User:
    """Create a new user with a securely hashed password."""

    # Check duplicate username
    existing_username = (
        db.query(User)
        .filter(User.username == user_data.username)
        .first()
    )

    if existing_username:
        raise ValueError("Username already exists")

    # Check duplicate email
    existing_email = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_email:
        raise ValueError("Email already exists")

    # Hash password before storing
    hashed_password = hash_password(user_data.password)

    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        name=user_data.name,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(db: Session, user_data: UserLogin) -> User:
    """Authenticate a user using username or email and password."""
    identifier = user_data.username.strip().lower()

    logging.debug(f"Attempting authentication for identifier: {identifier}")
    user = (
        db.query(User)
        .filter(
            or_(
                User.username.ilike(identifier),
                User.email.ilike(identifier),
            )
        )
        .first()
    )
    logging.debug(f"User lookup result: {user}")

    if not user:
        raise ValueError("Invalid username or password")

    if not verify_password(
        user_data.password,
        user.password_hash,
    ):
        logging.debug("Password verification failed")
        raise ValueError("Invalid username or password")
    else:
        logging.debug("Password verification succeeded")

    return user


def create_user_token(user: User) -> str:
    """Create a JWT access token for the authenticated user."""

    token_data = {
        "sub": user.username,
        "id": user.id,
    }

    return create_access_token(token_data)
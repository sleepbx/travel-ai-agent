from sqlalchemy.orm import Session

from backend.auth.auth_models import User
from backend.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)


def signup_user(db: Session, name: str, email: str, password: str):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise ValueError("User already exists")

    user = User(
        name=name,
        email=email,
        hashed_password=hash_password(password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def login_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.hashed_password):
        raise ValueError("Invalid credentials")

    token = create_access_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "name": user.name,
        }
    )

    return token

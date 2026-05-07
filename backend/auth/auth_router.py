from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.auth.auth_service import signup_user, login_user
from backend.auth.auth_schemas import SignupRequest, LoginRequest

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup")
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    try:
        user = signup_user(
            db=db,
            name=data.name,
            email=data.email,
            password=data.password,
        )
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    try:
        token = login_user(
            db=db,
            email=data.email,
            password=data.password,
        )
        return {"access_token": token}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

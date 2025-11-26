from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.auth.jwt_handler import create_access_token
from app.auth.schemas import LoginRequest, LoginResponse, UserInfo, UserType
from app.config import settings
from app.database.connection import get_db
from app.database import models

router = APIRouter(prefix="/api", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_user_by_type(
    db: Session, user_type: UserType, email: str
) -> models.Admin | models.Crew | models.Scheduler | models.Engineer | None:
    model_map = {
        UserType.ADMIN: models.Admin,
        UserType.CREW: models.Crew,
        UserType.SCHEDULER: models.Scheduler,
        UserType.ENGINEER: models.Engineer,
    }
    model = model_map.get(user_type)
    if model is None:
        return None
    return db.query(model).filter(model.email_id == email).first()


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    user = get_user_by_type(db, payload.user_type, payload.email)

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Update last_login if available
    if hasattr(user, "last_login"):
        from datetime import datetime

        user.last_login = datetime.utcnow()
        db.add(user)
        db.commit()

    token_data = {
        "sub": user.email_id,
        "user_type": payload.user_type.value,
        "name": user.name,
    }

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(token_data, access_token_expires)

    response.set_cookie(
        key="auth_token",
        value=access_token,
        httponly=settings.cookie_httponly,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )

    user_info = UserInfo(
        id=user.email_id,
        email=user.email_id,
        user_type=payload.user_type,
    )

    return LoginResponse(
        success=True,
        message="Login successful",
        user=user_info,
    )



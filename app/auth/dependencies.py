from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError

from app.auth.jwt_handler import decode_access_token
from app.auth.schemas import UserInfo, UserType


def get_current_user(auth_token: str | None = Cookie(default=None)) -> UserInfo:
    if auth_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = decode_access_token(auth_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    email: str | None = payload.get("sub")
    user_type_str: str | None = payload.get("user_type")

    if email is None or user_type_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_type = UserType(user_type_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user type in token",
        )

    return UserInfo(id=email, email=email, user_type=user_type)


def get_current_user_with_name(auth_token: str | None = Cookie(default=None)) -> UserInfo:
    if auth_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = decode_access_token(auth_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    email: str | None = payload.get("sub")
    user_type_str: str | None = payload.get("user_type")
    user_name: str | None = payload.get("name")
    if email is None or user_type_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_type = UserType(user_type_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user type in token",
        )

    return UserInfo(id=email, email=email, user_type=user_type, name=user_name)

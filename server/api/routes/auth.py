from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from server.engine.database.user_repository import UserRepository
from server.shared.auth_dto import AuthResponseDto, CredentialsDto, UserDto
from server.users.auth_service import AuthService


router = APIRouter(prefix="/api/auth", tags=["authentication"])
bearer_scheme = HTTPBearer(auto_error=False)


def get_user_repository(request: Request) -> UserRepository:
    return request.app.state.user_repository


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> dict[str, Any]:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    user_id = auth.get_user_id_from_token(credentials.credentials)
    if user_id is None:
        raise unauthorized
    user = await users.get_by_id(user_id)
    if user is None:
        raise unauthorized
    return user


@router.post("/register", response_model=AuthResponseDto, status_code=status.HTTP_201_CREATED)
async def register(
    payload: CredentialsDto,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponseDto:
    try:
        user = await auth.register(payload.email, payload.password)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return AuthResponseDto(
        access_token=auth.create_access_token(user["id"]),
        user=UserDto(id=user["id"], email=user["email"], created_at=user["created_at"]),
    )


@router.post("/login", response_model=AuthResponseDto)
async def login(
    payload: CredentialsDto,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponseDto:
    user = await auth.login(payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return AuthResponseDto(
        access_token=auth.create_access_token(user["id"]),
        user=UserDto(id=user["id"], email=user["email"], created_at=user["created_at"]),
    )


@router.get("/me", response_model=UserDto)
async def get_me(user: Annotated[dict[str, Any], Depends(get_current_user)]) -> UserDto:
    return UserDto(id=user["id"], email=user["email"], created_at=user["created_at"])

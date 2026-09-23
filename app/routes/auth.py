from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field

from app.core.security import (
    bearer_scheme,
    get_authenticated_user_id,
    get_supabase_client,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/signup")
def signup(request: SignupRequest):
    try:
        supabase = get_supabase_client()

        response = supabase.auth.sign_up(
            {
                "email": request.email,
                "password": request.password
            }
        )

        return {
            "message": "Account created successfully",
            "user": response.user.model_dump() if response.user else None,
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.post("/login")
def login(request: LoginRequest):
    try:
        supabase = get_supabase_client()

        response = supabase.auth.sign_in_with_password(
            {
                "email": request.email,
                "password": request.password
            }
        )

        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "user": response.user.model_dump()
        }

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )


@router.get("/me")
def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
):
    user_id = get_authenticated_user_id(credentials)

    try:
        supabase = get_supabase_client()
        response = supabase.auth.get_user(credentials.credentials)
        return response.user.model_dump()
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

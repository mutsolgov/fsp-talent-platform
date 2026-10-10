"""
FastAPI Security Utilities.
"""
from typing import Optional
from fastapi import HTTPException, Request, status


class OAuth2PasswordBearer:
    def __init__(self, tokenUrl: str, auto_error: bool = True):
        self.tokenUrl = tokenUrl
        self.auto_error = auto_error

    async def __call__(self, request: Request) -> Optional[str]:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        if self.auto_error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None


class OAuth2PasswordRequestForm:
    def __init__(
        self,
        username: str = "",
        password: str = "",
        scope: str = "",
        grant_type: str = "password",
    ):
        self.username = username
        self.password = password
        self.scope = scope
        self.grant_type = grant_type

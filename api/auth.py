import hashlib
from pydantic import BaseModel
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import APIKeyHeader
from sqlmodel import Session

from config.settings import settings
from utils.database import get_engine
from repositories.api_key_repository import APIKeyRepository

# Define API Key security scheme for OpenAPI/Swagger
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


class APIKeyContext(BaseModel):
    """Context info extracted from verified API key."""
    organization_id: int
    api_key_id: int
    api_key_name: str


def _hash_api_key(raw_key: str) -> str:
    """Derive deterministic hash for API key secrets."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


async def verify_api_key(api_key: str = Security(api_key_header)) -> APIKeyContext:
    """
    Dependency to verify API key from X-API-Key header, backed by api_keys table.

    Returns:
        APIKeyContext: Organization ID and API key metadata for use in routes

    Raises:
        HTTPException: If API key is missing, invalid, inactive, or DB is misconfigured.
    """
    if not settings.DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database is not configured for API key validation",
        )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    hashed = _hash_api_key(api_key)

    try:
        with Session(get_engine()) as session:
            repo = APIKeyRepository(session)
            record = repo.get_by_hash(hashed)

            if not record:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                    headers={"WWW-Authenticate": "ApiKey"},
                )

            if not record.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="API key is inactive",
                    headers={"WWW-Authenticate": "ApiKey"},
                )

            if record.organization_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="API key is not configured with an organization",
                )

            repo.touch_last_used(record)

            # Return context with organization info
            return APIKeyContext(
                organization_id=record.organization_id,
                api_key_id=record.id,
                api_key_name=record.name
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate API key",
        )


def get_current_organization(
    api_key_context: APIKeyContext = Depends(verify_api_key),
) -> int:
    """
    Extract organization ID from verified API key context.

    Args:
        api_key_context: Verified API key context from auth

    Returns:
        Organization ID for the current request

    Usage:
        @router.get("/sessions")
        def get_sessions(org_id: int = Depends(get_current_organization)):
            # All queries will be filtered by org_id
            pass
    """
    return api_key_context.organization_id

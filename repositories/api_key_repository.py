from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from models.api_key import APIKey


class APIKeyRepository:
    """Data access helpers for API keys."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Fetch an API key row by its hash."""
        return self.db.exec(
            select(APIKey).where(APIKey.key_hash == key_hash)
        ).first()

    def touch_last_used(self, api_key: APIKey) -> APIKey:
        """Update last_used_at timestamp for a key."""
        api_key.last_used_at = datetime.utcnow()
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        return api_key

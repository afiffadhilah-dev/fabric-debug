"""Seed script to insert an API key for local development/testing.

Usage:
  python scripts/seed_api_key.py
  python scripts/seed_api_key.py --key my-secret-key
  python scripts/seed_api_key.py --reset
"""

import hashlib
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import argparse
from sqlmodel import Session, create_engine, select
from sqlalchemy import delete

from config.settings import settings
from models.api_key import APIKey
from models.organization import Organization

DEFAULT_RAW_KEY = "tahuB03lat"
DEFAULT_NAME = "fabric-key"
DEFAULT_ORG = "fabric"


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def seed_api_key(raw_key: str = DEFAULT_RAW_KEY, reset: bool = False) -> bool:
    db_url = settings.DATABASE_URL
    if not db_url:
        print("ERROR: DATABASE_URL not set in environment/.env", file=sys.stderr)
        return False

    engine = create_engine(db_url)
    key_hash = hash_key(raw_key)

    try:
        with Session(engine) as db:
            # Ensure organization exists
            print("Creating/verifying organization...")
            org = db.exec(
                select(Organization).where(Organization.name == DEFAULT_ORG)
            ).first()
            
            if not org:
                org = Organization(name=DEFAULT_ORG)
                db.add(org)
                db.commit()
                db.refresh(org)
                print(f"✅ Created organization '{DEFAULT_ORG}' (id={org.id})")
            else:
                print(f"✅ Organization '{DEFAULT_ORG}' exists (id={org.id})")
            
            if reset:
                res = db.exec(delete(APIKey).where(APIKey.key_hash == key_hash))
                deleted = res.rowcount if hasattr(res, "rowcount") and res.rowcount else 0
                db.commit()
                print(f"Reset: removed {deleted} existing key(s)")

            existing = db.exec(
                select(APIKey).where(APIKey.key_hash == key_hash)
            ).first()
            
            if existing:
                print(f"API key already exists (name={existing.name}, org_id={existing.organization_id})")
                return True

            api_key = APIKey(
                key_hash=key_hash,
                name=DEFAULT_NAME,
                organization_id=org.id
            )
            db.add(api_key)
            db.commit()

            print(f"API key seeded successfully:")
            print(f"  Raw key: {raw_key}")
            print(f"  Hash:    {key_hash[:16]}...")
            print(f"  Name:    {DEFAULT_NAME}")
            print(f"  Org ID:  {org.id}")
            print(f"  Org:     {DEFAULT_ORG}")
            return True

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed an API key for local dev/testing")
    parser.add_argument("--key", default=DEFAULT_RAW_KEY, help=f"Raw API key value (default: {DEFAULT_RAW_KEY})")
    parser.add_argument("--reset", action="store_true", help="Remove existing key before inserting")
    args = parser.parse_args()

    ok = seed_api_key(raw_key=args.key, reset=args.reset)
    sys.exit(0 if ok else 1)

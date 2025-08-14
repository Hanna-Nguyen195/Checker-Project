import hashlib, secrets
from datetime import datetime, timedelta, timezone

def new_reset_token_and_hash(ttl_minutes: int = 30) -> tuple[str, str, datetime]:
    raw = secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    expiry = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    return raw, hashed, expiry

def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

import hashlib
import string
import time

from sqlalchemy.orm import Session

from .models import UrlMapping

BASE62_CHARS = string.ascii_letters + string.digits  # a-zA-Z0-9
TOKEN_LENGTH = 7
MAX_RETRIES = 10


def base62_encode(data: bytes) -> str:
    """Convert bytes to Base62 string."""
    num = int.from_bytes(data, "big")
    if num == 0:
        return BASE62_CHARS[0]
    result = []
    while num > 0:
        num, remainder = divmod(num, 62)
        result.append(BASE62_CHARS[remainder])
    return "".join(reversed(result))


def token_exists_in_db(db: Session, token: str) -> bool:
    # The DB is the source of truth for collision checks.
    return db.query(UrlMapping).filter(UrlMapping.token == token).first() is not None


def generate_token(url: str, db: Session) -> str:
    """SHA-256 + nonce + Base62 token generation with collision retry."""
    # Scaffold TODO reference:
    # 1. Hash (url + a varying nonce) so repeated requests can still produce fresh tokens.
    # 2. Base62-encode the digest and truncate it to TOKEN_LENGTH for a short URL-safe token.
    # 3. Ask the database whether that token already exists before returning it.
    for attempt in range(MAX_RETRIES):
        nonce = f"{time.time_ns()}:{attempt}"
        digest = hashlib.sha256(f"{url}:{nonce}".encode("utf-8")).digest()
        token = base62_encode(digest)[:TOKEN_LENGTH]
        if not token_exists_in_db(db, token):
            return token

    # If every retry collides, surface the failure instead of silently reusing a token.
    raise RuntimeError("Unable to generate a unique token")

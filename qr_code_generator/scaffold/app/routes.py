import io
from datetime import datetime, timedelta
from typing import TypedDict

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy import delete, func
from sqlalchemy.orm import Session

from .database import get_db
from .models import CreateAttempt, LOCAL_TZ, ScanEvent, UrlMapping
from .schemas import CreateRequest, CreateResponse, QRInfoResponse, UpdateRequest
from .token_gen import generate_token
from .url_validator import validate_url

router = APIRouter()


class _CacheEntry(TypedDict):
    url: str
    expires_at: datetime | None


# In-memory cache (simulates Redis for prototype)
redirect_cache: dict[str, _CacheEntry] = {}

BASE_URL = "http://localhost:8000"
CREATE_RATE_LIMIT_COUNT = 3
CREATE_RATE_LIMIT_WINDOW = timedelta(minutes=1)


def _local_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=LOCAL_TZ)
    return value.astimezone(LOCAL_TZ)


def _is_expired(value: datetime | None) -> bool:
    expires_at = _local_datetime(value)
    return expires_at is not None and expires_at <= datetime.now(LOCAL_TZ)


def _client_key(request: Request) -> str:
    forwarded = (
        request.headers.get("x-vercel-forwarded-for")
        or request.headers.get("x-forwarded-for")
        or request.headers.get("x-real-ip")
    )
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_create_rate_limit(request: Request, db: Session):
    now = datetime.now(LOCAL_TZ)
    cutoff = now - CREATE_RATE_LIMIT_WINDOW
    client_key = _client_key(request)

    # Keep the backing table bounded to the active rate-limit window.
    db.execute(delete(CreateAttempt).where(CreateAttempt.created_at < cutoff))
    db.commit()

    attempt_count = int(
        db.query(func.count(CreateAttempt.id))
        .filter(CreateAttempt.client_key == client_key, CreateAttempt.created_at >= cutoff)
        .scalar()
        or 0
    )

    if attempt_count >= CREATE_RATE_LIMIT_COUNT:
        oldest_attempt = (
            db.query(CreateAttempt.created_at)
            .filter(CreateAttempt.client_key == client_key, CreateAttempt.created_at >= cutoff)
            .order_by(CreateAttempt.created_at.asc())
            .first()
        )
        oldest_attempt_at = _local_datetime(oldest_attempt[0]) if oldest_attempt else now
        retry_after = int(
            (oldest_attempt_at + CREATE_RATE_LIMIT_WINDOW - now).total_seconds()
        ) + 1
        raise HTTPException(
            status_code=429,
            detail="Too many QR codes created. Try again later.",
            headers={"Retry-After": str(max(retry_after, 1))},
        )

    db.add(CreateAttempt(client_key=client_key, created_at=now))
    db.commit()


@router.post("/api/qr/create", response_model=CreateResponse)
def create_qr(req: CreateRequest, request: Request, db: Session = Depends(get_db)):
    _check_create_rate_limit(request, db)

    # Validate and normalize before we generate a token or persist anything.
    try:                                                                                                                                                           
        normalized_url = validate_url(req.url)                
    except ValueError as e:                                                                                                                                        
        raise HTTPException(status_code=422, detail=str(e))
    token = generate_token(normalized_url, db)

    # Persist the mapping so future redirects resolve through the short token.
    mapping = UrlMapping(
        token=token,
        original_url=normalized_url,
        expires_at=_local_datetime(req.expires_at),
    )
    db.add(mapping)
    db.commit()

    short_url = f"{BASE_URL}/r/{token}"

    # Warm cache with metadata so cache hits never need a DB round-trip.
    redirect_cache[token] = {"url": normalized_url, "expires_at": _local_datetime(req.expires_at)}

    return CreateResponse(
        token=token,
        short_url=short_url,
        qr_code_url=f"{BASE_URL}/api/qr/{token}/image",
        original_url=normalized_url,
    )


@router.get("/r/{token}")
def redirect(token: str, request: Request, db: Session = Depends(get_db)):
    """Redirect fallback flow: Cache -> DB -> 404/410 (from slides mermaid diagram)"""
    # Scaffold TODO reference:
    # 1. Check redirect_cache first because this is the hottest path in the system.
    # 2. Fall back to the DB on cache miss so deletes and expirations still work.
    # 3. Return 404 for unknown tokens, 410 for deleted/expired tokens, and 302 otherwise.
    cached = redirect_cache.get(token)
    if cached is not None:
        # Serve entirely from cached metadata — no DB round-trip needed.
        # Deletions are handled by cache invalidation in delete_qr/update_qr.
        if _is_expired(cached["expires_at"]):
            redirect_cache.pop(token, None)
            raise HTTPException(status_code=410, detail="Gone")
        _record_scan(token, request, db)
        return RedirectResponse(
            url=cached["url"],
            status_code=302,
            headers={"X-Cache": "HIT"},
        )

    mapping = db.query(UrlMapping).filter(UrlMapping.token == token).first()
    if mapping is None:
        raise HTTPException(status_code=404, detail="Not Found")
    if mapping.is_deleted or _is_expired(mapping.expires_at):
        raise HTTPException(status_code=410, detail="Gone")

    # Warm the cache after a DB hit so the next redirect avoids another lookup.
    redirect_cache[token] = {"url": mapping.original_url, "expires_at": mapping.expires_at}
    _record_scan(token, request, db)
    return RedirectResponse(
        url=mapping.original_url,
        status_code=302,
        headers={"X-Cache": "MISS"},
    )


@router.get("/api/qr/{token}", response_model=QRInfoResponse)
def get_qr_info(token: str, db: Session = Depends(get_db)):
    # Read-only metadata lookup for the management API.
    mapping = _get_mapping_or_404(token, db)
    return mapping


@router.patch("/api/qr/{token}", response_model=QRInfoResponse)
def update_qr(token: str, req: UpdateRequest, db: Session = Depends(get_db)):
    mapping = _get_mapping_or_404(token, db)

    if req.url is not None:
        # Re-run the same validation rules used during creation.
        try:
            mapping.original_url = validate_url(req.url)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        # Invalidate cache
        redirect_cache.pop(token, None)

    if req.expires_at is not None:
        mapping.expires_at = _local_datetime(req.expires_at)
        # Invalidate cache
        redirect_cache.pop(token, None)

    db.commit()
    db.refresh(mapping)
    return mapping


@router.delete("/api/qr/{token}")
def delete_qr(token: str, db: Session = Depends(get_db)):
    mapping = _get_mapping_or_404(token, db)
    # Soft delete keeps history in the DB while making future redirects return 410.
    mapping.is_deleted = True
    db.commit()
    # Invalidate cache
    redirect_cache.pop(token, None)
    return {"detail": "Deleted"}


@router.get("/api/qr/{token}/image")
def get_qr_image(token: str, db: Session = Depends(get_db)):
    # The QR code encodes the short redirect URL, not the original long URL.
    _get_mapping_or_404(token, db)
    short_url = f"{BASE_URL}/r/{token}"

    img = qrcode.make(short_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.get("/api/qr/{token}/analytics")
def get_analytics(token: str, db: Session = Depends(get_db)):
    # Aggregate scan count plus a simple daily rollup from scan_events.
    _get_mapping_or_404(token, db)

    total = db.query(func.count(ScanEvent.id)).filter(ScanEvent.token == token).scalar()

    daily = (
        db.query(
            func.date(ScanEvent.scanned_at).label("date"),
            func.count(ScanEvent.id).label("count"),
        )
        .filter(ScanEvent.token == token)
        .group_by(func.date(ScanEvent.scanned_at))
        .all()
    )

    return {
        "token": token,
        "total_scans": total,
        "scans_by_day": [{"date": str(row.date), "count": row.count} for row in daily],
    }


def _get_mapping_or_404(token: str, db: Session) -> UrlMapping:
    # Shared lookup helper for routes that operate on an existing live token.
    mapping = db.query(UrlMapping).filter(UrlMapping.token == token).first()
    if mapping is None or mapping.is_deleted:
        raise HTTPException(status_code=404, detail="Not Found")
    return mapping


def _record_scan(token: str, request: Request, db: Session):
    # Each redirect writes one analytics event with the minimal request metadata we need.
    event = ScanEvent(
        token=token,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.add(event)
    db.commit()

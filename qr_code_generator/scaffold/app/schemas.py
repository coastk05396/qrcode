from datetime import datetime

from pydantic import BaseModel


# Request body for creating a new QR mapping.
class CreateRequest(BaseModel):
    url: str
    expires_at: datetime | None = None


# API response returned immediately after creation.
class CreateResponse(BaseModel):
    token: str
    short_url: str
    qr_code_url: str
    original_url: str


# Full metadata view for an existing QR mapping.
class QRInfoResponse(BaseModel):
    token: str
    original_url: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    is_deleted: bool


# Request body for partial updates to an existing mapping.
class UpdateRequest(BaseModel):
    url: str | None = None
    expires_at: datetime | None = None

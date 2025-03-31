from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional
from datetime import timezone

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    
    class Config:
        from_attributes = True
class Link(BaseModel):
    id: int
    original_url: str
    short_code: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_permanent: bool
    last_accessed: datetime
    clicks: int

    class Config:
        from_attributes = True

class LinkCreate(BaseModel):
    original_url: str
    custom_alias: Optional[str] = None
    is_permanent: Optional[bool] = True
    expires_at: Optional[datetime] = None
    owner_id: Optional[int] = None

class LinkExpiryUpdate(BaseModel):
    expires_at: datetime

    @field_validator("expires_at", mode="before")
    def parse_datetime(cls, value):
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc) if isinstance(value, str) else value.astimezone(timezone.utc)

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class StudentCreate(BaseModel):
    name: str = Field(..., min_length=2, example="John Doe")
    course: str = Field(..., min_length=2, example="Computer Science")
    level: str = Field(..., example="Year 2")
    section: str = Field(..., example="Section A")
    qr_code: Optional[str] = Field(None)


class StudentResponse(BaseModel):
    id: int
    name: str
    course: str
    level: str
    section: str
    qr_code: Optional[str] = None



class AdminCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class AdminLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str


class AdminResponse(BaseModel):
    id: UUID # Changed from UUID to str to fix validation error
    email: EmailStr
    full_name: str
    is_active: bool
    is_admin: bool
    has_full_access: bool
    created_at: datetime
    
    class Config:
        from_attributes = True  # For ORM compatibility
        
    # This will convert UUID to string for serialization
    @classmethod
    def from_orm(cls, obj):
        if hasattr(obj, 'id') and isinstance(obj.id, UUID):
            obj.id = str(obj.id)
        return super().from_orm(obj)
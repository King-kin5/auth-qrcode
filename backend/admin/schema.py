from typing import Optional
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
    id: str
    email: str
    full_name: str
    
    
    class Config:
        orm_mode = True
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Student models
class StudentCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    age: int
    grade: str  # New field for student grade

class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None
    grade: Optional[str] = None  # New field for student grade

class StudentResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    age: int
    grade: str  # New field for student grade
    
    class Config:
        from_attributes = True

# User models
class UserCreate(BaseModel):    
    username: str
    email: str
    password: str
    # Role removed - only admins can assign roles

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: int
    
    class Config:
        from_attributes = True

# Document models
class DocumentResponse(BaseModel):
    id: int
    filename: str
    upload_date: datetime
    file_size: int
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
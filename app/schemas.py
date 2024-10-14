from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    phone_number: str
    device_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class Data(BaseModel):
    latitude: float
    longitude: float
    level: str

class UpdateData(BaseModel):
    id: str
    annotations_str: Optional[str] = None
    lang: Optional[str] = "en"  # Default to English

class OTPRequest(BaseModel):
    phone_number: str
    otp: str

class TokenData(BaseModel):
    phone_number: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

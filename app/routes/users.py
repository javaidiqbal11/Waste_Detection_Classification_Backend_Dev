# routers 
import os
import shutil
import pyotp
from datetime import datetime, timedelta
from fastapi import APIRouter, Body, HTTPException, UploadFile, File, Query, Depends
from fastapi.responses import JSONResponse
from app.schemas import OTPRequest, Token
from app.utils import create_mongo_connection
from app.dependencies import get_current_user
from jose import jwt
import hashlib
import base64
from pydantic import BaseModel

router = APIRouter()

# Ensure SECRET_KEY is defined for JWT
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key").encode()
ALGORITHM = "HS256"

class GenOTP(BaseModel):
    phone_number: str

# Data model for the OTP request
class OTPRequest(BaseModel):
    phone_number: str
    otp: str

# Helper to create a JWT access token with a valid secret key
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=60))
    to_encode.update({"exp": expire})

    if not isinstance(SECRET_KEY, (str, bytes)):
        raise ValueError("SECRET_KEY must be a string or bytes-formatted key.")
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.get("/user_exists/")
async def UserExists(phone_numer: str, device_id: str):
    try:
        DB = create_mongo_connection()

        FindUser = DB["users"].find_one({"phone_number": phone_numer})
        
        if FindUser is None:
            return JSONResponse(
                status_code=200,
                content={"user_exists": False, "same_device": False, "device_id": device_id, "is_active": False},
            )
        else:
            # Check if the user is active
            if FindUser.get("is_active") is False:
                return JSONResponse(
                    status_code=200,
                    content={"user_exists": True, "same_device": False, "device_id": device_id, "is_active": False},
                )
            else:
                # get device_id from DB
                user_device_id = FindUser.get("device_id")
                if user_device_id != device_id:
                    return JSONResponse(
                        status_code=200,
                        content={"user_exists": True, "same_device": False, "device_id": device_id, "is_active": True},
                    )
                else:
                    return JSONResponse(
                        status_code=200,
                        content={"user_exists": True, "same_device": True, "device_id": device_id, "is_active": True},
                    )


    except Exception as err:
        print(err)
        raise HTTPException(status_code=500, detail=f"Internal Server Erorr {err}")
    
# Register User endpoint
@router.post("/register/")
async def register_user(
    phone_number: str = Body(...),
    device_id: str = Body(...),
    first_name: str = None,
    last_name: str = None,
    profile_image: UploadFile = File(None)
):
    try:
        db = create_mongo_connection()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"Database connection error: {e}"}
        )

    try:
        find_user = db["users"].find_one({"phone_number": phone_number})
        if find_user:
            return JSONResponse(status_code=400, content={"message": "User already exists"})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"Database error while checking user existence: {e}"}
        )

    user_data = {
        "first_name": first_name,
        "last_name": last_name,
        "phone_number": phone_number,
        "device_id": device_id,
        "is_active": True,
        "profile_image": None,
    }

    if profile_image:
        try:
            file_location = f"images/{phone_number}/profile_image/{profile_image.filename}"
            os.makedirs(os.path.dirname(file_location), exist_ok=True)
            with open(file_location, "wb+") as file_object:
                file_object.write(profile_image.file.read())
            user_data["profile_image"] = file_location
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"message": f"File saving error: {e}"}
            )

    try:
        db["users"].insert_one(user_data)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"Database insertion error: {e}"}
        )

    try:
        access_token = create_access_token(data={"sub": phone_number})
        return JSONResponse(
            status_code=200,
            content={"access_token": access_token, "token_type": "bearer"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"Token generation error: {e}"}
        )

# Generate OTP endpoint
@router.post("/generate-otp/")
def generate_otp(gen_otp: GenOTP):
    try:
        secret_key = derive_secret_key(gen_otp.phone_number)
        totp = pyotp.TOTP(secret_key, interval=300)
        otp = totp.now()
        return {"otp": otp}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"OTP generation error: {e}"})

# Verify OTP endpoint
@router.post("/verify-otp/")
def verify_otp(otp_request: OTPRequest):
    try:
        secret_key = derive_secret_key(otp_request.phone_number)
        totp = pyotp.TOTP(secret_key, interval=300)
        if totp.verify(otp_request.otp):
            return {"message": "OTP is valid"}
        else:
            raise HTTPException(status_code=400, detail="Invalid OTP")
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"OTP verification error: {e}"})

# Login User endpoint
@router.post("/login/", response_model=Token)
async def login_user(phone_number: str = Body(...), device_id: str = Body(...)):
    try:
        db = create_mongo_connection()
        find_user = db["users"].find_one({"phone_number": phone_number, "device_id": device_id})
        if not find_user:
            raise HTTPException(status_code=400, detail="User does not exist")
        access_token = create_access_token(data={"sub": find_user["phone_number"]})
        return {"access_token": access_token, "token_type": "bearer"}
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Login error: {e}"})

# Read Users Me endpoint
@router.get("/users/me")
async def read_users_me(token: str = Depends(get_current_user)):
    try:
        db = create_mongo_connection()
        phone_number: str = token.get("sub")
        find_user = db["users"].find_one({"phone_number": phone_number})

        if not find_user:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        find_user["_id"] = str(find_user["_id"])
        return JSONResponse(status_code=200, content={"message": "Authenticated", "data": find_user})
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Read user error: {e}"})
    


# Link Clicked endpoint
@router.get("/link/clicked")
async def link_clicked(linkid: str = Query(...)):
    return JSONResponse(status_code=200, content={"message": f"Link with ID {linkid} clicked"})

# Update Profile endpoint
@router.patch("/update_profile/")
async def update_profile(
    first_name: str = Body(None),
    last_name: str = Body(None),
    profile_image: UploadFile = File(None),
    token: str = Depends(get_current_user)
):
    try:
        db = create_mongo_connection()
        phone_number: str = token.get("sub")
        find_user = db["users"].find_one({"phone_number": phone_number})
        if not find_user:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        update_data = {}
        if first_name:
            update_data["first_name"] = first_name
        if last_name:
            update_data["last_name"] = last_name
        if profile_image:
            file_location = f"images/{phone_number}/profile_image/{profile_image.filename}"
            os.makedirs(os.path.dirname(file_location), exist_ok=True)
            with open(file_location, "wb+") as file_object:
                file_object.write(profile_image.file.read())
            update_data["profile_image"] = file_location

        db["users"].find_one_and_update({"phone_number": phone_number}, {"$set": update_data})
        return JSONResponse(status_code=200, content={"message": "Profile updated Successfully"})
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Profile update error: {e}"})

# Deactivate User endpoint
@router.delete("/deactiate_user/")
async def deactivate_user(token: str = Depends(get_current_user)):
    try:
        db = create_mongo_connection()
        phone_number: str = token.get("sub")

        find_user = db["users"].find_one({"phone_number": phone_number})
        
        if not find_user:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        db["users"].find_one_and_update({"phone_number": phone_number}, {"$set": {"is_active": False}})
        return JSONResponse(status_code=200, content={"message": "User deactivated"})
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Deactivation error: {e}"})

# Delete User endpoint
@router.delete("/user/")
async def delete_user(token: str = Depends(get_current_user)):
    try:
        db = create_mongo_connection()
        phone_number: str = token.get("sub")
        
        find_user = db["users"].find_one({"phone_number": phone_number})
        if not find_user:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        db["users"].delete_one({"phone_number": phone_number})
        user_image_dir = f"images/{phone_number}"
        
        if os.path.exists(user_image_dir):
            shutil.rmtree(user_image_dir)
        return JSONResponse(status_code=200, content={"message": "User deleted"})
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Deletion error: {e}"})
    
# A function to derive a secret key from a phone number
def derive_secret_key(phone_number: str):
    # Combine the phone number with the salt and hash it to create a unique secret key
    hash_digest = hashlib.sha256((phone_number).encode()).digest()
    # Encode the hash in base32
    return base64.b32encode(hash_digest).decode('utf-8').strip('=')



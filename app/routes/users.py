import os
import shutil
import pyotp
from fastapi import APIRouter, Body, HTTPException, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas import User, OTPRequest, Token
from app.utils import create_mongo_connection, derive_secret_key, create_access_token
from app.dependencies import get_current_user
from passlib.context import CryptContext

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/generate-otp")
def generate_otp(phone_number: str = Body(...)):
    secret_key = derive_secret_key(phone_number)
    totp = pyotp.TOTP(secret_key, interval=300)
    otp = totp.now()
    # Send OTP via SMS (implementation required)
    return {"message": "OTP generated and sent"}

@router.post("/verify-otp")
def verify_otp(otp_request: OTPRequest):
    secret_key = derive_secret_key(otp_request.phone_number)
    totp = pyotp.TOTP(secret_key, interval=300)
    if totp.verify(otp_request.otp):
        return {"message": "OTP is valid"}
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP")

@router.post("/register/")
async def register_user(
    username: str = Body(...),
    password: str = Body(...),
    phone_number: str = Body(...),
    device_id: str = Body(...),
    first_name: str = Body(None),
    last_name: str = Body(None),
    profile_image: UploadFile = File(None)
):
    db = create_mongo_connection()
    find_user = db["users"].find_one({"phone_number": phone_number})
    if find_user:
        return JSONResponse(status_code=400, content={"message": "User already exists"})

    hashed_password = pwd_context.hash(password)
    user_data = {
        "username": username,
        "password": hashed_password,
        "phone_number": phone_number,
        "device_id": device_id,
        "first_name": first_name,
        "last_name": last_name,
        "is_active": True,
        "profile_image": None,
    }

    if profile_image:
        file_location = f"images/{phone_number}/profile_image/{profile_image.filename}"
        os.makedirs(os.path.dirname(file_location), exist_ok=True)
        with open(file_location, "wb+") as file_object:
            file_object.write(profile_image.file.read())
        user_data["profile_image"] = file_location

    db["users"].insert_one(user_data)
    access_token = create_access_token(data={"sub": phone_number})
    return JSONResponse(
        status_code=200,
        content={"access_token": access_token, "token_type": "bearer"},
    )

@router.post("/login/", response_model=Token)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    db = create_mongo_connection()
    username = form_data.username
    password = form_data.password
    find_user = db["users"].find_one({"username": username})
    if not find_user:
        raise HTTPException(status_code=400, detail="User doesn't exist")
    if not pwd_context.verify(password, find_user["password"]):
        raise HTTPException(status_code=400, detail="Invalid password")
    access_token = create_access_token(data={"sub": find_user["phone_number"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", dependencies=[Depends(get_current_user)])
async def read_users_me(token: str = Depends(get_current_user)):
    db = create_mongo_connection()
    phone_number = token
    find_user = db["users"].find_one({"phone_number": phone_number})
    if not find_user:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    find_user["_id"] = str(find_user["_id"])
    return JSONResponse(status_code=200, content={"message": "Authenticated", "data": find_user})

@router.patch("/update_profile/", dependencies=[Depends(get_current_user)])
async def update_profile(
    first_name: str = Body(None),
    last_name: str = Body(None),
    profile_image: UploadFile = File(None),
    token: str = Depends(get_current_user)
):
    db = create_mongo_connection()
    phone_number = token
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
    return JSONResponse(status_code=200, content={"message": "Profile updated successfully"})

@router.delete("/deactivate/", dependencies=[Depends(get_current_user)])
async def deactivate_user(token: str = Depends(get_current_user)):
    db = create_mongo_connection()
    phone_number = token
    find_user = db["users"].find_one({"phone_number": phone_number})
    if not find_user:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    db["users"].find_one_and_update({"phone_number": phone_number}, {"$set": {"is_active": False}})
    return JSONResponse(status_code=200, content={"message": "User deactivated"})

@router.delete("/delete/", dependencies=[Depends(get_current_user)])
async def delete_user(token: str = Depends(get_current_user)):
    db = create_mongo_connection()
    phone_number = token
    find_user = db["users"].find_one({"phone_number": phone_number})
    if not find_user:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    db["users"].delete_one({"phone_number": phone_number})
    db["wastes"].delete_many({"phone_number": phone_number})
    user_image_dir = f"images/{phone_number}"
    if os.path.exists(user_image_dir):
        shutil.rmtree(user_image_dir)
    return JSONResponse(status_code=200, content={"message": "User deleted"})

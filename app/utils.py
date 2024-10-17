import os
import hashlib
import base64
import pyotp
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pymongo import MongoClient
from dotenv import load_dotenv
import reverse_geocoder as rg
import pycountry

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
ALGORITHM = "HS256"

def create_mongo_connection():
    client = MongoClient(os.getenv("MONGODB_URI"))
    return client["wastedata"]

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=60))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def derive_secret_key(phone_number: str):
    hash_digest = hashlib.sha256(phone_number.encode()).digest()
    return base64.b32encode(hash_digest).decode('utf-8').strip('=')

def get_country_name(lat, lon):
    coordinates = (lat, lon)
    result = rg.search(coordinates)
    country_code = result[0]['cc']
    country = pycountry.countries.get(alpha_2=country_code)
    return country.name if country else "Unknown"

def sort_title_descending(title):
    try:
        number_part = int(title.split()[0])
        return number_part
    except ValueError:
        return 0

import os
import shutil
from bson import ObjectId
from PIL import Image
from app.utils import create_mongo_connection

def save_image(user_id, image_file):
    user_image_dir = f"images/{user_id}"
    if not os.path.exists(user_image_dir):
        os.makedirs(user_image_dir)
    image_path = f"{user_image_dir}/{image_file.filename}"
    try:
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        return image_path
    except Exception as e:
        raise Exception(f"Internal Server Error IMG: {str(e)}")

def save_data_to_db(payload):
    try:
        db = create_mongo_connection()
        db["wastes_copy"].insert_one(payload)
    except Exception as e:
        raise Exception(f"Internal Server Error: {str(e)}")

def update_data_in_db(id, payload):
    try:
        db = create_mongo_connection()
        result = db["wastes_copy"].find_one_and_update({"_id": ObjectId(id)}, {"$set": payload}, return_document=True)
        return result
    except Exception as e:
        raise Exception(f"Internal Server Error: {str(e)}")

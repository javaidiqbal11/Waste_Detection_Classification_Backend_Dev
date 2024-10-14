import os
import uuid
import shutil
from datetime import datetime
from PIL import Image
from bson import ObjectId
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from app.crud import save_image, save_data_to_db, update_data_in_db
from app.utils import get_country_name, create_mongo_connection
from app.dependencies import get_current_user

router = APIRouter()

@router.post("/", dependencies=[Depends(get_current_user)])
async def save_data(
    image_file: UploadFile = File(...),
    latitude: float = Query(...),
    longitude: float = Query(...),
    level: str = Query(...),
    token: str = Depends(get_current_user),
    lang: str = "en"  # Optional language parameter for labels
):
    phone_number = token
    image_path = save_image(phone_number, image_file)
    db = create_mongo_connection()

    # Fetch annotations (IDs) from "wastes_copy" based on the level
    waste_data = db["wastes_copy"].find_one({"level": level})
    annotation_ids = waste_data.get("annotations", []) if waste_data else []

    # Retrieve labels for these IDs from "classLabels" collection
    labels = {}
    for annotation_id in annotation_ids:
        class_label = db["classLabels"].find_one({"ID": annotation_id})
        if class_label:
            label = class_label.get("Eng") if lang == "en" else class_label.get("Fr")
            labels[annotation_id] = label

    # Prepare the payload with all necessary information
    payload = {
        "phone_number": phone_number,
        "image_path": image_path,
        "latitude": latitude,
        "longitude": longitude,
        "country": get_country_name(latitude, longitude),
        "level": level,
        "annotations": labels,
        "cropped_paths": [],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_data_to_db(payload)
    return JSONResponse(status_code=200, content={"message": "Data saved successfully"})

@router.patch("/", dependencies=[Depends(get_current_user)])
async def update_data(
    id: str = Query(...),
    annotations_str: str = Query(None),
    token: str = Depends(get_current_user),
    lang: str = "en"  # Optional language parameter for labels
):
    phone_number = token
    db = create_mongo_connection()

    # Convert annotations from string format to list of IDs
    try:
        annotation_ids = eval(annotations_str) if annotations_str else []
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid annotations format: {str(e)}")

    # Retrieve labels for these IDs from "classLabels" collection
    labels = {}
    for annotation_id in annotation_ids:
        class_label = db["classLabels"].find_one({"ID": annotation_id})
        if class_label:
            label = class_label.get("Eng") if lang == "en" else class_label.get("Fr")
            labels[annotation_id] = label

    # Fetch existing data in "wastes_copy" for updating
    waste_data = db["wastes_copy"].find_one({"_id": ObjectId(id)})
    if not waste_data:
        raise HTTPException(status_code=404, detail="Data not found")

    image_path = waste_data["image_path"]
    cropped_dir = f"images/{phone_number}/cropped"
    if os.path.exists(cropped_dir):
        shutil.rmtree(cropped_dir)
    os.makedirs(cropped_dir, exist_ok=True)

    cropped_paths = []
    for annotation in annotation_ids:
        # Assume each annotation contains the coordinates for cropping
        x1, y1, x2, y2 = annotation['x1'], annotation['y1'], annotation['x2'], annotation['y2']
        image = Image.open(image_path)
        cropped_image = image.crop((x1, y1, x2, y2))
        cropped_image_filename = f"{uuid.uuid4()}_{os.path.basename(image_path)}"
        cropped_image_path = f"{cropped_dir}/{cropped_image_filename}"
        cropped_image.save(cropped_image_path)
        cropped_paths.append(cropped_image_path)

    # Prepare the payload with updated annotations and cropped paths
    payload = {
        "annotations": labels,
        "cropped_paths": cropped_paths,
    }
    update_data_in_db(id, payload)
    return JSONResponse(status_code=200, content={"message": "Data updated successfully"})

import os
import uuid
from PIL import Image
from bson import ObjectId
from datetime import datetime
from fastapi import (APIRouter, UploadFile, HTTPException, File,Query, Depends, status)
from fastapi.responses import JSONResponse
from app.crud import save_image, save_data_to_db, update_data_in_db
from app.utils import get_country_name, create_mongo_connection
from app.dependencies import get_current_user

router = APIRouter()

@router.post("/save_data")
async def save_data(
    image_file: UploadFile = File(...),
    latitude: float = Query(...),
    longitude: float = Query(...),
    level: str = Query(...),
    token: str = Depends(get_current_user),
    ):

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    phone_number: str = token.get("sub")
    image_path = save_image(phone_number, image_file)
    try:
        payload = {
            "phone_number": phone_number,
            "image_path": image_path,
            "latitude": latitude,
            "longitude": longitude,
            "country": get_country_name(latitude, longitude),
            "level": level,
            "annotations": {},
            "cropped_paths": [],
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        save_data_to_db(payload)        
        return JSONResponse(status_code=200, content={"message": "Data saved successfully"})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.patch("/save_data", dependencies=[Depends(get_current_user)])
async def update_data(
    id: str = Query(...),
    annotations_str: str = Query(None),
    token: str = Depends(get_current_user),
    lang: str = "en"
    ):
    
    phone_number: str = token.get("sub")
    db = create_mongo_connection()

    if annotations_str is None:
        annotations = {"annotations": []}
    else:
        try:
            annotations = eval(annotations_str)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid annotations format: {str(e)}"
            )
    
    # Save cropped images in folder according to phone number
    cropped_dir = f"images/{phone_number}/cropped"
    if not os.path.exists(cropped_dir):
        os.makedirs(cropped_dir)

    waste_data = db["wastes_copy"].find_one({"_id": ObjectId(id)})
        
    if not waste_data:
        raise HTTPException(status_code=404, detail="Data not found")
    try:
        image_path = waste_data["image_path"]
        image_file = image_path.split("/")[-1]
        
        # Delete cropped images if exists in images folder
        if os.path.exists(f"images/{phone_number}/cropped"):
            for file in os.listdir(f"images/{phone_number}/cropped"):
                if file.endswith(f"_{image_file}"):
                    os.remove(f"images/{phone_number}/cropped/{file}")
    
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(e)}"
        )
    
    cordsNlabels=[]
    cropped_paths = []
    
    try:
        annotation_list=annotations["annotations"]
        for annotation_dict in annotation_list:
            annotation_id=annotation_dict["label"]
            if lang=='fr':
                class_label = db["classlabels"].find_one({"Fr": annotation_id})
            else:
                class_label = db["classlabels"].find_one({"Eng": annotation_id})
            
            x1, y1, x2, y2 = annotation_dict['x1'], annotation_dict['y1'], annotation_dict['x2'], annotation_dict['y2']
            
            image = Image.open(image_path)
            cordsNlabels.append({"label":int(class_label['ID']),"x1":x1, "y1":y1, "x2":x2, "y2":y2})
            
            cropped_image = image.crop((x1, y1, x2, y2))
            cropped_image_filename = f"{uuid.uuid4()}_{os.path.basename(image_path)}"
            cropped_image_path = f"{cropped_dir}/{cropped_image_filename}"
            cropped_image.save(cropped_image_path)
            cropped_paths.append(cropped_image_path)
    
    except Exception as e:
        raise HTTPException(    
            status_code=500, detail=f"Internal Server Error IMG: {str(e)}"
        )

    payload = {
        "annotations": cordsNlabels,
        "cropped_paths": cropped_paths,
    }
    
    update_data_in_db(id, payload)
    
    return JSONResponse(status_code=200, content={"message": "Data updated successfully"})

@router.get("/save_data")
async def get_all_waste_data(
    token: str = Depends(get_current_user),
    lang: str = "en"
    ):
    
    db = create_mongo_connection()
    phone_number: str = token.get("sub")
    
    FindUser = db["users"].find_one({"phone_number": phone_number})
    if FindUser is None:
        raise HTTPException(
            
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    AllWasteData = list(db["wastes_copy"].find({"phone_number": phone_number}))

    for waste_data in AllWasteData:
        if "annotations" in waste_data:
            for annotation in waste_data["annotations"]:
                label_id = annotation["label"]
                class_label_obj = db["classlabels"].find_one({"ID": str(label_id)})
            
                if lang=='fr':
                    class_label=class_label_obj["Fr"]
                    
                else:
                    class_label=class_label_obj["Eng"]
                
                annotation["label"] = class_label
    
    AllWasteData = [{**level, "_id": str(level["_id"])} for level in AllWasteData]
    
    return JSONResponse(
        status_code=200,
        content={"message": "Operation Successful", "data": AllWasteData},
    )

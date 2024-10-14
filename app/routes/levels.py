from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.utils import create_mongo_connection, sort_title_descending
from app.dependencies import get_current_user

router = APIRouter()

@router.post("/", dependencies=[Depends(get_current_user)])
async def upload_levels(file: UploadFile = File(...)):
    try:
        content = await file.read()
        lines = content.decode().splitlines()
        levels_data = [{"title": line} for line in lines]
        db = create_mongo_connection()
        db["levels"].insert_many(levels_data)
        return JSONResponse(status_code=200, content={"message": "Levels saved successfully"})
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Internal Server Error {err}")

@router.get("/", dependencies=[Depends(get_current_user)])
async def get_levels(lang: str = "en"):  # Default language is English
    try:
        db = create_mongo_connection()
        result = db["levels"].find()
        levels = [{**level, "_id": str(level["_id"])} for level in result]
        
        # Convert label to the chosen language
        for level in levels:
            level['title'] = level['title_en'] if lang == "en" else level['title_fr']
        
        levels = sorted(levels, key=lambda doc: sort_title_descending(doc["title"]), reverse=True)
        return JSONResponse(status_code=200, content={"message": "Operation Successful", "data": levels})
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Internal Server Error {err}")

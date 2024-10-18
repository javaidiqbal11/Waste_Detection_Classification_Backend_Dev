from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.utils import create_mongo_connection, sort_title_descending
from app.dependencies import get_current_user

# from openai import OpenAI
# import os
# AIClient = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter()

# @app.post("/levels/")
# async def ConvertLevels_AND_SaveTo_DB(file: UploadFile = File(...)):
#     try:
#         ParsedFile = await file.read()
#         ParsedFile = ParsedFile.splitlines()

#         EnglishData = []
#         for CodedLine in ParsedFile:
#             line = CodedLine.decode().strip()
#             currentLine = line.split(" ")
            
#             if len(currentLine) < 5:
#                 continue
            
#             level1 = currentLine[0]
#             level2 = currentLine[1]
#             preLevel3 = currentLine[2]
#             level3 = preLevel3[:-1] if preLevel3[-1] == "*" else preLevel3

#             if is_number_between_1_and_101(level3) is not False:
#                 EnglishData = [
#                     (
#                         {
#                             **item,
#                             "levelTwo": [
#                                 (
#                                     {
#                                         **sub_item,
#                                         "levelThree": sub_item["levelThree"]
#                                         + [{"title": line}],
#                                     }
#                                     if sub_item.get("title")
#                                     and sub_item["title"].startswith(
#                                         level1 + " " + level2
#                                     )
#                                     else sub_item
#                                 )
#                                 for sub_item in item["levelTwo"]
#                             ],
#                         }
#                         if item["title"].startswith(level1)
#                         else item
#                     )
#                     for item in EnglishData
#                 ]

#                 continue

#             if is_number_between_1_and_101(level2) is not False:
#                 EnglishData = [
#                     {
#                         **item,
#                         "levelTwo": (
#                             item["levelTwo"] + [{"title": line, "levelThree": []}]
#                             if item["title"].startswith(level1)
#                             else item["levelTwo"]
#                         ),
#                     }
#                     for item in EnglishData
#                 ]

#                 continue

#             if is_number_between_1_and_101(level1) is not False:
#                 EnglishData.append({"title": line, "levelTwo": []})

#         DB = create_mongo_connection()
#         DB["englishLevels"].insert_many(EnglishData)

#         # ------------------- FRENCH LEVELS ----------------------
#         FrenchData = []
#         for CodedLine in ParsedFile:
#             line = CodedLine.decode().strip()
#             currentLine = line.split(" ")
#             if len(currentLine) < 5:
#                 continue
#             line = TranslateToFrench(line)
#             level1 = currentLine[0]
#             level2 = currentLine[1]
#             preLevel3 = currentLine[2]
#             level3 = preLevel3[:-1] if preLevel3[-1] == "*" else preLevel3

#             if is_number_between_1_and_101(level3) is not False:
#                 FrenchData = [
#                     (
#                         {
#                             **item,
#                             "levelTwo": [
#                                 (
#                                     {
#                                         **sub_item,
#                                         "levelThree": sub_item["levelThree"]
#                                         + [{"title": line}],
#                                     }
#                                     if sub_item.get("title")
#                                     and sub_item["title"].startswith(
#                                         level1 + " " + level2
#                                     )
#                                     else sub_item
#                                 )
#                                 for sub_item in item["levelTwo"]
#                             ],
#                         }
#                         if item["title"].startswith(level1)
#                         else item
#                     )
#                     for item in FrenchData
#                 ]

#                 continue

#             if is_number_between_1_and_101(level2) is not False:
#                 FrenchData = [
#                     {
#                         **item,
#                         "levelTwo": (
#                             item["levelTwo"] + [{"title": line, "levelThree": []}]
#                             if item["title"].startswith(level1)
#                             else item["levelTwo"]
#                         ),
#                     }
#                     for item in FrenchData
#                 ]

#                 continue

#             if is_number_between_1_and_101(level1) is not False:
#                 FrenchData.append({"title": line, "levelTwo": []})

#         DB["frenchLevels"].insert_many(FrenchData)

#         return JSONResponse(
#             status_code=200,
#             content={"message": "Operation Successful"},
#         )
    
#     except Exception as err:
#         print(err)
#         raise HTTPException(status_code=500, detail=f"Internal Server Erorr {err}")


@router.get("/levels")
async def get_levels(token: str = Depends(get_current_user), lang: str = "en"):
    try:
        db = create_mongo_connection()
        
        if lang == "eng":
            result = db["englishLevels"].find()
        
        elif lang == "fr":
            result = db["frenchLevels"].find()

        result = [{**level, "_id": str(level["_id"])} for level in result]

        result = sorted(
            result, key=lambda doc: sort_title_descending(doc["title"]), reverse=True
        )

        if token is not None:
            phone_number: str = token.get("sub")
            FindUser = db["users"].find_one({"phone_number": phone_number})

            if FindUser is not None and FindUser.get("links") is not None:
                LinkClicks = FindUser.get("links")
                result = sorted(
                    result, key=lambda x: LinkClicks.get(x["_id"], 0), reverse=True
                )

        return JSONResponse(
            status_code=200,
            content={"message": "Operation Successful", "data": result},
        )

    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Internal Server Erorr {err}")

# def is_number_between_1_and_101(s):
#     if s.isdigit():  # Check if the string consists of only digits
#         number = int(s)
#         if 1 <= number <= 101:  # Check if the number falls within the range
#             return True
#     return False

# def TranslateToFrench(line: str):
#     try:
#         CONTENT = f"""  {line}

#                 Convert above line to french , I need just translated line in response and nothing else
#             """
#         response = AIClient.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "user", "content": CONTENT},
#             ],
#             temperature=0,
#         )
#         data = response.json()
#         data = json.loads(data)

#         if (
#             data.get("choices") is not None
#             and data["choices"][0].get("message") is not None
#         ):
#             Result = data["choices"][0]["message"]["content"]
#         else:
#             Result = None

#         return Result

#     except Exception as err:
#         return None



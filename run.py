import uvicorn
from app.main import app  # Change this line to import app from app.main

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)


# Execute via command 
# uvicorn app:app --reload

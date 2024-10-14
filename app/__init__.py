import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.routes import data, levels, users

app = FastAPI()

# Ensure the 'images' directory exists
if not os.path.exists('images'):
    os.makedirs('images')

app.mount("/images", StaticFiles(directory="images"), name="images")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router, prefix="/save_data")
app.include_router(levels.router, prefix="/levels")
app.include_router(users.router, prefix="/users")

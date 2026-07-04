import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

# Load local environment variables from the .env file
load_dotenv()

app = FastAPI(
    title="MY Inventory Tracking API",
    description="A secure FastAPI application. Use the Authorize button to unlock POST requests.",
    version="1.0.0"
)

# Set up our security interceptor
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Read the secret key from the system environment
MASTER_API_KEY = os.getenv("MY_SECRET_API_KEY", "fallback_local_key")

# Mock internal database storage
data_store = [
    {"id": 1, "name": "Premium Badminton Racket", "status": "Strung"},
    {"id": 2, "name": "O-Ring Drive Chain Lube", "status": "In Stock"}
]

class Item(BaseModel):
    id: int
    name: str
    status: str

# Dependency check function
def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != MASTER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or Missing API Key. Access Denied."
        )
    return api_key

# --- ENDPOINTS ---

@app.get("/", tags=["General"])
def read_root():
    return {"message": "Welcome to my live API! Navigate to /docs to view the interactive Swagger dashboard."}

@app.get("/items", response_model=List[Item], tags=["Inventory"])
def get_items():
    """Public Endpoint: Anyone can view the tracking data."""
    return data_store

@app.post("/items", response_model=Item, tags=["Inventory"])
def create_item(item: Item, token: str = Depends(verify_api_key)):
    """Protected Endpoint: Requires a valid X-API-Key header to append new data."""
    data_store.append(item.dict())
    return item
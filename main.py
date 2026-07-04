import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

# Database Specific Imports
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session, declarative_base

load_dotenv()

# --- DATABASE SETUP ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is missing!")

# Handle Render's postgresql:// vs postgres:// quirk if necessary
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Defining our SQL Table Structure
class DBItem(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    status = Column(String)

# Automatically create the table inside PostgreSQL if it's not already there
Base.metadata.create_all(bind=engine)

# NEW: Database Seeding Logic
def seed_initial_data():
    db = SessionLocal()
    try:
        # Check if the items table is completely empty
        item_count = db.query(DBItem).count()
        if item_count == 0:
            print("Database is empty! Seeding initial data items...")
            
            # Define your initial sample data entries
            initial_items = [
                DBItem(id=1, name="Premium Badminton Racket", status="Strung"),
                DBItem(id=2, name="O-Ring Drive Chain Lube", status="In Stock"),
                DBItem(id=3, name="Riding Gloves", status="Shipped")
            ]
            
            # Add and commit them to the database
            db.add_all(initial_items)
            db.commit()
            print("Database seeded successfully.")
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()

# Run the seeding function right when the app starts up
seed_initial_data()

# Dependency to get a fresh database session per API request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- FASTAPI & SECURITY SETUP ---
app = FastAPI(title="GP Database-Backed API", version="2.0.0")

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
MASTER_API_KEY = os.getenv("MY_SECRET_API_KEY", "fallback_local_key")

class ItemSchema(BaseModel):
    id: int
    name: str
    status: str

    class Config:
        from_attributes = True

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != MASTER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key."
        )
    return api_key

# --- ENDPOINTS ---

@app.get("/items", response_model=List[ItemSchema], tags=["Inventory"])
def get_items(db: Session = Depends(get_db)):
    """Fetch all entries directly out of the live SQL database table."""
    items = db.query(DBItem).all()
    return items

@app.post("/items", response_model=ItemSchema, tags=["Inventory"])
def create_item(item: ItemSchema, db: Session = Depends(get_db), token: str = Depends(verify_api_key)):
    """Insert a brand new verified row directly into the SQL database table."""
    # Check if item ID already exists to avoid SQL duplicates crashes
    db_exist = db.query(DBItem).filter(DBItem.id == item.id).first()
    if db_exist:
        raise HTTPException(status_code=400, detail="Item ID already exists.")
        
    db_item = DBItem(id=item.id, name=item.name, status=item.status)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
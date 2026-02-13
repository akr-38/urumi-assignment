import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_db import Base

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Use a generic fallback for local dev if needed, but in K8s it MUST be provided
    DATABASE_URL = "postgresql://user:password@localhost:5432/stores"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

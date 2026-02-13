from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class StoreModel(Base):
    __tablename__ = "stores"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text, nullable=True)

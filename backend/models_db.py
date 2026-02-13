from sqlalchemy import Column, String, Enum, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
import enum
from datetime import datetime

Base = declarative_base()

class StoreType(str, enum.Enum):
    WOOCOMMERCE = "woocommerce"
    MEDUSA = "medusa"

class StoreStatus(str, enum.Enum):
    PROVISIONING = "Provisioning"
    READY = "Ready"
    FAILED = "Failed"
    DELETING = "Deleting"

class StoreModel(Base):
    __tablename__ = "stores"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    type = Column(String, nullable=False) # Store String value
    status = Column(String, nullable=False) # Store String value
    url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text, nullable=True)

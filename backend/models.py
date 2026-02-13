from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
import uuid
from datetime import datetime

class StoreType(str, Enum):
    WOOCOMMERCE = "woocommerce"
    MEDUSA = "medusa"

class StoreStatus(str, Enum):
    PROVISIONING = "Provisioning"
    READY = "Ready"
    FAILED = "Failed"
    DELETING = "Deleting"

class CreateStoreRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, pattern="^[a-z0-9-]+$")
    type: StoreType

class Store(BaseModel):
    id: str
    name: str
    type: StoreType
    status: StoreStatus
    url: Optional[str] = None
    created_at: str
    error_message: Optional[str] = None

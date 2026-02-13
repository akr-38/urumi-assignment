from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from models import CreateStoreRequest, Store, StoreStatus, StoreType
from db import get_redis_client
from db_postgres import init_db, get_db
from models_db import StoreModel
from sqlalchemy.orm import Session
from fastapi import Depends
import uuid
import datetime
import logging
import traceback
import json

# Initialize Postgres Tables
init_db()

app = FastAPI(title="Store Provisioning API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("backend.main")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/stores", response_model=Store, status_code=status.HTTP_201_CREATED)
def create_store(request: CreateStoreRequest, fastapi_req: Request, db: Session = Depends(get_db)):
    try:
        # 0. Rate Limiting: 2 stores per hour per IP
        client_ip = fastapi_req.client.host
        r = get_redis_client()
        now = datetime.datetime.utcnow().timestamp()
        one_hour_ago = now - 3600
        
        # Use Redis Sorted Set for sliding window rate limiting
        key = f"rate_limit:{client_ip}"
        
        # Remove old timestamps
        r.zremrangebyscore(key, 0, one_hour_ago)
        
        # Count requests in the last hour
        request_count = r.zcard(key)
        
        if request_count >= 3:
            logger.warning(f"🚫 Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: 2 stores per hour per IP"
            )
        
        # Add current request timestamp
        r.zadd(key, {str(now): now})
        r.expire(key, 3600)

        # Check if store already exists in Postgres
        existing_store = db.query(StoreModel).filter(StoreModel.name == request.name).first()
        
        if existing_store:
            status_val = existing_store.status
            
            if status_val == StoreStatus.READY.value:
                raise HTTPException(status_code=400, detail="Store already up and running")
            
            if status_val == StoreStatus.PROVISIONING.value:
                # Return 202 instead of 201 to indicate it's already in progress
                return Store(
                    id=existing_store.id,
                    name=existing_store.name,
                    type=StoreType(existing_store.type),
                    status=StoreStatus(existing_store.status),
                    created_at=existing_store.created_at.isoformat(),
                    url=existing_store.url,
                    error_message="Pls be patient the store is being provisioned"
                )
            
            if status_val == StoreStatus.DELETING.value:
                raise HTTPException(status_code=409, detail="Pls try after the store is deleted successfully")
            
            if status_val == StoreStatus.FAILED.value:
                logger.info(f"🔄 Re-initiating failed store: {request.name}")
                
                # Update status to Provisioning for retry
                existing_store.status = StoreStatus.PROVISIONING.value
                existing_store.error_message = "Store recreation initiated"
                db.commit()
                db.refresh(existing_store)

                # Push delete -> create task sequence to Redis
                r = get_redis_client()
                # 1. First cleanup Kubernetes
                delete_task = {"action": "delete_store", "store_name": request.name}
                r.rpush("tasks", json.dumps(delete_task))
                # 2. Then recreate
                create_task = {"action": "create_store", "store_name": request.name, "store_type": request.type.value}
                r.rpush("tasks", json.dumps(create_task))

                return Store(
                    id=existing_store.id,
                    name=existing_store.name,
                    type=StoreType(existing_store.type),
                    status=StoreStatus(existing_store.status),
                    created_at=existing_store.created_at.isoformat(),
                    url=existing_store.url,
                    error_message=existing_store.error_message
                )

        # New Store Creation
        store_id = str(uuid.uuid4())
        new_store_db = StoreModel(
            id=store_id,
            name=request.name,
            type=request.type.value,
            status=StoreStatus.PROVISIONING.value,
            created_at=datetime.datetime.utcnow()
        )
        
        db.add(new_store_db)
        db.commit()
        db.refresh(new_store_db)

        # Push to Redis Queue
        r = get_redis_client()
        task = {"action": "create_store", "store_name": request.name, "store_type": request.type.value}
        r.rpush("tasks", json.dumps(task))

        logger.info(f"✅ Store creation initiated: {request.name} ({store_id})")
        
        return Store(
            id=new_store_db.id,
            name=new_store_db.name,
            type=StoreType(new_store_db.type),
            status=StoreStatus(new_store_db.status),
            created_at=new_store_db.created_at.isoformat(),
            url=new_store_db.url,
            error_message=new_store_db.error_message
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"❌ Error creating store '{request.name}': {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, 
            detail=f"Internal Server Error: {str(e)}"
        )

@app.get("/stores", response_model=list[Store])
def list_stores(db: Session = Depends(get_db)):
    try:
        stores_db = db.query(StoreModel).order_by(StoreModel.created_at.desc()).all()
        
        stores = []
        for s in stores_db:
            stores.append(Store(
                id=s.id,
                name=s.name,
                type=StoreType(s.type),
                status=StoreStatus(s.status),
                created_at=s.created_at.isoformat(),
                url=s.url,
                error_message=s.error_message
            ))
        return stores

    except Exception as e:
        logger.error(f"❌ Error listing stores: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to fetch stores")

@app.delete("/stores/{name}", status_code=status.HTTP_202_ACCEPTED)
def delete_store(name: str, db: Session = Depends(get_db)):
    try:
        store = db.query(StoreModel).filter(StoreModel.name == name).first()
        if not store:
            raise HTTPException(status_code=404, detail="Store not found")

        # Update status to Deleting in Postgres
        store.status = StoreStatus.DELETING.value
        db.commit()

        # Push delete task to Redis Queue
        r = get_redis_client()
        task = {"action": "delete_store", "store_name": name}
        r.rpush("tasks", json.dumps(task))

        logger.info(f"🗑️ Store deletion initiated: {name}")
        return {"message": "Store deletion started"}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"❌ Error deleting store '{name}': {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to delete store: {str(e)}")

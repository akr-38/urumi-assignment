import os
import redis
import logging
import traceback

# Configuration with defaults
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("backend.db")

try:
    logger.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=5
    )
    redis_client.ping()
    logger.info("✅ Successfully connected to Redis.")
except Exception as e:
    logger.error(f"❌ Failed to connect to Redis: {e}")
    logger.error(traceback.format_exc())
    # We might want to raise this or handle it depending on how critical startup is
    # For now, we'll let it fail loudly if called later
    pass

def get_redis_client():
    """Returns the redis client instance."""
    return redis_client

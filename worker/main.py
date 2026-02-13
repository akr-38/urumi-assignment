import os
import sys
import time
import json
import redis
import subprocess
import logging
import traceback
from db_postgres import get_db_session
from models_db import StoreModel

# Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
PUBLIC_IP = os.getenv("PUBLIC_IP", "127.0.0.1")  # Default to localhost for Kind/Minikube

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("worker")

# Redis Connection
try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    r.ping()
    logger.info(f"✅ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logger.error(f"❌ Failed to connect to Redis: {e}")
    sys.exit(1)

def run_cmd(cmd, desc=None):
    """Runs a shell command and raises exception on failure."""
    if desc:
        logger.info(f"🔹 {desc}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False  # We handle return code manually
        )
        
        if result.returncode != 0:
            logger.error(f"Command failed: {' '.join(cmd)}")
            logger.error(f"Stderr: {result.stderr}")
            raise Exception(f"Command failed: {result.stderr.strip()}")
            
        return result.stdout.strip()
    except Exception as e:
        raise e

def create_store(store_name, store_type):
    """Provisions a new store using Helm."""
    namespace = store_name
    
    logger.info(f"🚀 Starting provisioning for {store_name} ({store_type})")
    
    try:
        # 1. Create Namespace
        try:
            run_cmd(["kubectl", "create", "namespace", namespace], desc=f"Creating namespace '{namespace}'")
        except Exception as e:
            if "already exists" in str(e):
                logger.info(f"Namespace '{namespace}' already exists.")
            else:
                raise e

        # 2. Install Helm Chart
        # Choosing chart based on type
        if store_type == "woocommerce":
            chart = "bitnami/wordpress"
            # Note: In a real scenario, we'd use a robust values file. 
            # Here we use set flags for simplicity as per requirements.
            # Constants matching script.py
            # Credentials from environment variables (Secrets in K8s)
            WORDPRESS_USERNAME = os.getenv("WORDPRESS_USERNAME", "admin")
            WORDPRESS_PASSWORD = os.getenv("WORDPRESS_PASSWORD", "admin123")
            WORDPRESS_EMAIL = os.getenv("WORDPRESS_EMAIL", "admin@example.com")
            WORDPRESS_PLUGINS = os.getenv("WORDPRESS_PLUGINS", "woocommerce")
            MARIADB_ROOT_PASSWORD = os.getenv("MARIADB_ROOT_PASSWORD", "root123")
            MARIADB_PASSWORD = os.getenv("MARIADB_PASSWORD", "wp123")
            MARIADB_DATABASE = os.getenv("MARIADB_DATABASE", "bitnami_wordpress")

            helm_cmd = [
                "helm", "install", store_name, chart,
                "-n", namespace,
                "--set", "service.type=ClusterIP",
                "--set", f"wordpressUsername={WORDPRESS_USERNAME}",
                "--set", f"wordpressPassword={WORDPRESS_PASSWORD}",
                "--set", f"wordpressEmail={WORDPRESS_EMAIL}",
                "--set", f"wordpressBlogName={store_name}",
                "--set", f"wordpressPlugins={WORDPRESS_PLUGINS}",
                "--set", f"mariadb.auth.rootPassword={MARIADB_ROOT_PASSWORD}",
                "--set", f"mariadb.auth.password={MARIADB_PASSWORD}",
                "--set", f"mariadb.auth.database={MARIADB_DATABASE}",
                "--set", "persistence.enabled=false",
                "--set", "ingress.enabled=true",
                "--set", f"ingress.hostname={store_name}.{PUBLIC_IP}.nip.io"
            ]
        elif store_type == "medusa":
            # Stub for Medusa - using a simple nginx for now to prove valid provisioning flow
            # In real implementation, this would be the medusa chart
            logger.info("⚠️ Medusa requested. Using Nginx placeholder as architecture stub.")
            chart = "bitnami/nginx"
            helm_cmd = [
                "helm", "install", store_name, chart,
                "-n", namespace,
                "--set", "service.type=ClusterIP",
                "--set", "ingress.enabled=true",
                "--set", f"ingress.hostname={store_name}.{PUBLIC_IP}.nip.io"
            ]
        else:
            raise Exception(f"Unknown store type: {store_type}")

        run_cmd(helm_cmd, desc=f"Installing {chart} via Helm")

        # 2.5 Wait for Pods to be ready
        wait_cmd = [
            "kubectl", "wait",
            "--for=condition=ready",
            "pod",
            "-l", f"app.kubernetes.io/instance={store_name}",
            "-n", namespace,
            "--timeout=300s"
        ]
        try:
            run_cmd(wait_cmd, desc=f"Waiting for {store_name} pods to be ready")
        except Exception as e:
            logger.warning(f"⚠️ Wait command timed out or failed for {store_name}: {e}")
            # We continue anyway, but the store might not be immediately accessible

        # 3. Update Postgres
        store_url = f"http://{store_name}.{PUBLIC_IP}.nip.io"
        
        db = get_db_session()
        try:
            store = db.query(StoreModel).filter(StoreModel.name == store_name).first()
            if store:
                store.status = "Ready"
                store.url = store_url
                store.error_message = "" # Clear any previous errors
                db.commit()
                logger.info(f"✅ Successfully provisioned {store_name} at {store_url}")
            else:
                logger.error(f"❌ Store {store_name} not found in database during status update.")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Failed to provision {store_name}: {e}")
        db = get_db_session()
        try:
            store = db.query(StoreModel).filter(StoreModel.name == store_name).first()
            if store:
                store.status = "Failed"
                store.error_message = str(e)
                db.commit()
        finally:
            db.close()

def delete_store(store_name):
    """Deletes a store and its resources."""
    logger.info(f"🗑️ Deleting store {store_name}")
    namespace = store_name
    
    try:
        # 1. Uninstall Helm Release
        try:
            run_cmd(["helm", "uninstall", store_name, "-n", namespace], desc="Uninstalling Helm release")
        except Exception as e:
            if "not found" in str(e):
                logger.info("Helm release not found, skipping.")
            else:
                logger.warning(f"Helm uninstall warning: {e}")

        # 2. Delete Namespace
        try:
            run_cmd(["kubectl", "delete", "namespace", namespace, "--timeout=60s"], desc="Deleting namespace")
        except Exception as e:
            if "not found" in str(e):
                logger.info("Namespace not found, skipping.")
            else:
                logger.warning(f"Namespace delete warning: {e}")

        # 3. Cleanup Postgres
        db = get_db_session()
        try:
            store = db.query(StoreModel).filter(StoreModel.name == store_name).first()
            if store:
                # Loophole fix: Only delete the DB record if we are TRULY deleting it (status == Deleting)
                # If status is Failed or Provisioning, it's a retry/cleanup from create_store, so KEEP it.
                if store.status == "Deleting":
                    db.delete(store)
                    db.commit()
                    logger.info(f"✅ Successfully deleted {store_name} from database")
                else:
                    logger.info(f"🔹 Cleaned up K8s resources for {store_name}, keeping DB record for retry.")
            else:
                logger.warning(f"⚠️ Store {store_name} not found in database during deletion cleanup.")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Failed to delete {store_name}: {e}")
        db = get_db_session()
        try:
            store = db.query(StoreModel).filter(StoreModel.name == store_name).first()
            if store:
                store.status = "Failed"
                store.error_message = f"Delete failed: {str(e)}"
                db.commit()
        finally:
            db.close()

def main():
    logger.info("👷 Worker started. Waiting for tasks...")
    
    while True:
        try:
            # Blocking pop from Redis
            # returns (key, value) tuple
            item = r.blpop("tasks", timeout=10)
            
            if not item:
                continue
                
            queue_name, task_data = item
            task = json.loads(task_data)
            
            logger.info(f"📨 Received task: {task['action']}")
            
            if task['action'] == 'create_store':
                create_store(task['store_name'], task['store_type'])
            elif task['action'] == 'delete_store':
                delete_store(task['store_name'])
            else:
                logger.error(f"Unknown action: {task['action']}")
                
        except Exception as e:
            logger.error(f"❌ Worker loop error: {e}")
            logger.error(traceback.format_exc())
            time.sleep(1)

if __name__ == "__main__":
    main()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

from backend.core.cache import init_cache_cleanup
from backend.db.database import init_db
from backend.api import router as api_router

app = FastAPI(
    title="What Beats Rock",
    description="A web-based interactive guessing game where players attempt to submit items that 'beat' the current word",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only, replace with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def run_migrations():
    """Run database migrations using Alembic with improved error handling."""
    try:
        file_path = Path(__file__).resolve()
        backend_dir = file_path.parent
        migrations_dir = backend_dir / "db" / "migrations"
        
        logger.info(f"Running database migrations from {migrations_dir}")
        
        alembic_ini = migrations_dir / "alembic.ini"
        if not alembic_ini.exists():
            logger.error(f"Alembic configuration not found at {alembic_ini}")
            return False
            
        result = subprocess.run(
            ["alembic", "upgrade", "head"], 
            cwd=str(migrations_dir),
            check=False,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("Database migrations applied successfully")
            logger.debug(result.stdout)
            return True
        else:
            logger.error(f"Migration command failed with return code {result.returncode}")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error running migrations: {e}", exc_info=True)
        return False

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    logger.info("Starting application initialization...")
    
    if run_migrations():
        logger.info("Database initialized via migrations")
    else:
        logger.warning("Migrations failed, falling back to direct table creation")
        try:
            init_db()
            logger.info("Database initialized via direct table creation")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
    
    init_cache_cleanup()
    
    logger.info("Application startup complete: database and cache initialized")

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
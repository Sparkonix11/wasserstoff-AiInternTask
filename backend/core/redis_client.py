import redis.asyncio as redis
import os
import json
import logging
import time
from typing import Optional, Any, Dict
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get Redis URL from environment variables
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Default timeout for Redis operations (3 seconds)
REDIS_TIMEOUT = 3.0

# Create Redis pool for the async client with timeout
redis_pool = redis.ConnectionPool.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_timeout=REDIS_TIMEOUT,
    socket_connect_timeout=REDIS_TIMEOUT
)

# Track Redis availability status
redis_last_error_time = 0
AVAILABILITY_LOG_SUPPRESS_SECONDS = 60  # Only log availability issues once per minute

async def get_redis_connection():
    """Get an async Redis connection from the pool."""
    return redis.Redis(connection_pool=redis_pool)

async def is_redis_available() -> bool:
    """Check if Redis is available by attempting a connection."""
    try:
        conn = await get_redis_connection()
        await conn.ping()
        return True
    except redis.exceptions.ConnectionError:
        return False

async def set_cache(key: str, value: Any, expiration: int = 86400) -> bool:
    """
    Set a value in the Redis cache using native async client.
    
    Args:
        key: The cache key
        value: The value to cache (will be JSON serialized)
        expiration: Time to live in seconds (default: 24 hours)
    
    Returns:
        bool: True if successful, False otherwise
    """
    global redis_last_error_time
    
    try:
        conn = await get_redis_connection()
        serialized = json.dumps(value)
        result = await conn.set(key, serialized, ex=expiration)
        return bool(result)
    except redis.exceptions.ConnectionError as e:
        current_time = int(time.time())
        # Only log once per minute to avoid flooding logs
        if current_time - redis_last_error_time > AVAILABILITY_LOG_SUPPRESS_SECONDS:
            logger.warning(f"Redis connection error: {e}. Using fallback mechanisms.")
            redis_last_error_time = current_time
        return False
    except Exception as e:
        logger.error(f"Redis error setting cache: {e}")
        return False

async def get_cache(key: str) -> Optional[Any]:
    """
    Get a value from the Redis cache using native async client.
    
    Args:
        key: The cache key
    
    Returns:
        The cached value (JSON deserialized) or None if not found
    """
    global redis_last_error_time
    
    try:
        conn = await get_redis_connection()
        result = await conn.get(key)
        
        if result is not None:
            return json.loads(result)
        return None
    except redis.exceptions.ConnectionError as e:
        current_time = int(time.time())
        if current_time - redis_last_error_time > AVAILABILITY_LOG_SUPPRESS_SECONDS:
            logger.warning(f"Redis connection error: {e}. Using fallback mechanisms.")
            redis_last_error_time = current_time
        return None
    except Exception as e:
        logger.error(f"Redis error getting cache: {e}")
        return None

async def increment_counter(key: str) -> int:
    """
    Increment a counter in Redis using native async client.
    
    Args:
        key: The counter key
    
    Returns:
        int: The new counter value or 0 on failure
    """
    global redis_last_error_time
    
    try:
        conn = await get_redis_connection()
        result = await conn.incr(key)
        return result
    except redis.exceptions.ConnectionError as e:
        current_time = int(time.time())
        if current_time - redis_last_error_time > AVAILABILITY_LOG_SUPPRESS_SECONDS:
            logger.warning(f"Redis connection error: {e}. Using fallback mechanisms.")
            redis_last_error_time = current_time
        return 0
    except Exception as e:
        logger.error(f"Redis error incrementing counter: {e}")
        return 0

async def get_counter(key: str) -> int:
    """
    Get a counter value from Redis using native async client.
    
    Args:
        key: The counter key
    
    Returns:
        int: The counter value or 0 if not found
    """
    global redis_last_error_time
    
    try:
        conn = await get_redis_connection()
        result = await conn.get(key)
        return int(result) if result is not None else 0
    except redis.exceptions.ConnectionError as e:
        current_time = int(time.time())
        if current_time - redis_last_error_time > AVAILABILITY_LOG_SUPPRESS_SECONDS:
            logger.warning(f"Redis connection error: {e}. Using fallback mechanisms.")
            redis_last_error_time = current_time
        return 0
    except Exception as e:
        logger.error(f"Redis error getting counter: {e}")
        return 0

async def delete_cache(key: str) -> bool:
    """
    Delete a value from the Redis cache using native async client.
    
    Args:
        key: The cache key
    
    Returns:
        bool: True if successful, False otherwise
    """
    global redis_last_error_time
    
    try:
        conn = await get_redis_connection()
        result = await conn.delete(key)
        return bool(result)
    except redis.exceptions.ConnectionError as e:
        current_time = int(time.time())
        if current_time - redis_last_error_time > AVAILABILITY_LOG_SUPPRESS_SECONDS:
            logger.warning(f"Redis connection error: {e}. Using fallback mechanisms.")
            redis_last_error_time = current_time
        return False
    except Exception as e:
        logger.error(f"Redis error deleting cache: {e}")
        return False

# Session management functions
SESSION_PREFIX = "session:"
SESSION_TTL = 3600 * 24 * 7  # 7 days

async def save_session(session_id: str, session_data: Any) -> bool:
    """
    Save a game session to Redis.
    
    Args:
        session_id: The unique session identifier
        session_data: The session data to store
    
    Returns:
        bool: True if successful, False otherwise
    """
    key = f"{SESSION_PREFIX}{session_id}"
    return await set_cache(key, session_data, SESSION_TTL)

async def get_session(session_id: str) -> Optional[Any]:
    """
    Retrieve a game session from Redis.
    
    Args:
        session_id: The unique session identifier
    
    Returns:
        The session data or None if not found
    """
    key = f"{SESSION_PREFIX}{session_id}"
    return await get_cache(key)

async def delete_session(session_id: str) -> bool:
    """
    Delete a game session from Redis.
    
    Args:
        session_id: The unique session identifier
    
    Returns:
        bool: True if successful, False otherwise
    """
    key = f"{SESSION_PREFIX}{session_id}"
    return await delete_cache(key)

async def get_active_session_count() -> int:
    """
    Get count of active game sessions.
    
    Returns:
        int: Number of active sessions
    """
    global redis_last_error_time
    
    try:
        conn = await get_redis_connection()
        keys = await conn.keys(f"{SESSION_PREFIX}*")
        return len(keys)
    except redis.exceptions.ConnectionError as e:
        current_time = int(time.time())
        if current_time - redis_last_error_time > AVAILABILITY_LOG_SUPPRESS_SECONDS:
            logger.warning(f"Redis connection error: {e}. Using fallback mechanisms.")
            redis_last_error_time = current_time
        return 0
    except Exception as e:
        logger.error(f"Redis error counting sessions: {e}")
        return 0
import os
import json
import asyncio
from typing import Dict, Any, Optional
import time
from backend.core.redis_client import set_cache, get_cache, increment_counter, get_counter, is_redis_available

class LocalCache:
    def __init__(self):
        self.verdict_cache: Dict[str, bool] = {}
        self.global_counts: Dict[str, int] = {}
        self.word_pair_counts: Dict[str, int] = {}
        self.cache_timestamps: Dict[str, float] = {}
        
local_cache = LocalCache()

CACHE_TTL = 24 * 60 * 60

VERDICT_KEY_PREFIX = "verdict:"
COUNT_KEY_PREFIX = "count:"
PAIR_COUNT_KEY_PREFIX = "pair_count:"

async def get_verdict_from_cache(cache_key: str) -> Optional[bool]:
    """
    Get a cached verdict for a pair of words.
    Tries Redis first, falls back to in-memory cache.
    Returns None if not found or expired.
    """
    redis_key = f"{VERDICT_KEY_PREFIX}{cache_key}"
    
    redis_result = await get_cache(redis_key)
    if (redis_result is not None):
        local_cache.verdict_cache[cache_key] = bool(redis_result)
        local_cache.cache_timestamps[cache_key] = time.monotonic()
        return bool(redis_result)
    
    if cache_key in local_cache.verdict_cache:
        timestamp = local_cache.cache_timestamps.get(cache_key, 0)
        if time.monotonic() - timestamp <= CACHE_TTL:
            return local_cache.verdict_cache[cache_key]
        else:
            del local_cache.verdict_cache[cache_key]
            if cache_key in local_cache.cache_timestamps:
                del local_cache.cache_timestamps[cache_key]
    
    return None

async def save_verdict_to_cache(cache_key: str, verdict: bool) -> None:
    """Save a verdict to both Redis and in-memory cache."""
    redis_key = f"{VERDICT_KEY_PREFIX}{cache_key}"
    
    redis_success = await set_cache(redis_key, verdict, CACHE_TTL)
    
    local_cache.verdict_cache[cache_key] = verdict
    local_cache.cache_timestamps[cache_key] = time.monotonic()

async def get_global_count(word: str) -> int:
    """Get the global count for a word from Redis or in-memory cache."""
    lowercase_word = word.lower()
    redis_key = f"{COUNT_KEY_PREFIX}{lowercase_word}"
    
    count = await get_counter(redis_key)
    if count > 0:
        local_cache.global_counts[lowercase_word] = count
        return count
    
    return local_cache.global_counts.get(lowercase_word, 0)

async def increment_global_count(word: str) -> int:
    """Increment the global count for a word in Redis and in-memory cache."""
    lowercase_word = word.lower()
    redis_key = f"{COUNT_KEY_PREFIX}{lowercase_word}"
    
    count = await increment_counter(redis_key)
    
    if lowercase_word in local_cache.global_counts:
        local_cache.global_counts[lowercase_word] += 1
    else:
        local_cache.global_counts[lowercase_word] = 1
    
    return count if count > 0 else local_cache.global_counts[lowercase_word]

async def get_word_pair_count(word1: str, word2: str) -> int:
    """
    Get the count for a word pair from Redis or in-memory cache.
    word1 is the word that gets beaten, word2 is the word that beats.
    """
    lowercase_word1 = word1.lower()
    lowercase_word2 = word2.lower()
    pair_key = f"{lowercase_word1}:{lowercase_word2}"
    redis_key = f"{PAIR_COUNT_KEY_PREFIX}{pair_key}"
    
    count = await get_counter(redis_key)
    if count > 0:
        local_cache.word_pair_counts[pair_key] = count
        return count
    
    return local_cache.word_pair_counts.get(pair_key, 0)

async def increment_word_pair_count(word1: str, word2: str) -> int:
    """
    Increment the count for a word pair in Redis and in-memory cache.
    word1 is the word that gets beaten, word2 is the word that beats.
    """
    lowercase_word1 = word1.lower()
    lowercase_word2 = word2.lower()
    pair_key = f"{lowercase_word1}:{lowercase_word2}"
    redis_key = f"{PAIR_COUNT_KEY_PREFIX}{pair_key}"
    
    count = await increment_counter(redis_key)
    
    if pair_key in local_cache.word_pair_counts:
        local_cache.word_pair_counts[pair_key] += 1
    else:
        local_cache.word_pair_counts[pair_key] = 1
    
    return count if count > 0 else local_cache.word_pair_counts[pair_key]

async def clean_expired_cache():
    """Remove expired entries from the in-memory cache."""
    current_time = time.monotonic()
    expired_keys = [key for key, timestamp in local_cache.cache_timestamps.items() 
                   if current_time - timestamp > CACHE_TTL]
    
    for key in expired_keys:
        if key in local_cache.verdict_cache:
            del local_cache.verdict_cache[key]
        if key in local_cache.cache_timestamps:
            del local_cache.cache_timestamps[key]
    
    if expired_keys:
        print(f"Cleaned {len(expired_keys)} expired cache entries.")

async def cache_cleanup_task():
    """Background task to periodically clean the cache."""
    while True:
        await asyncio.sleep(3600)  # Clean every hour
        await clean_expired_cache()

def init_cache_cleanup():
    """Initialize the cache cleanup background task."""
    loop = asyncio.get_event_loop()
    loop.create_task(cache_cleanup_task())
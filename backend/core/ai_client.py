import os
import google.generativeai as genai
from typing import Dict, Any, Optional, Tuple
import asyncio
import json
import re
import logging
import time
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = os.getenv("GEMINI_API_KEY", "")
if not API_KEY:
    logger.warning("GEMINI_API_KEY environment variable not set!")

genai.configure(api_key=API_KEY)

PERSONAS = {
    "default": {
        "system_prompt": """You are a judge in a game called "What Beats Rock". 
        Your task is to determine if an item beats another item in a logical or conceptual sense.
        You MUST respond with ONLY a single word: either "true" or "false".
        No explanations, no additional text. Just the single word "true" or "false".""",
        "feedback_prompt": """You are providing feedback in a game called "What Beats Rock".
        Your tone is neutral and straightforward.
        Explain briefly why the guess either beats or doesn't beat the current word.
        Keep your explanation to 1-2 sentences, focusing on the logical relationship."""
    },
    "serious": {
        "system_prompt": """You are a logical and serious judge in a game called "What Beats Rock". 
        Your task is to carefully analyze whether an item beats another item in a rational and logical sense.
        You MUST respond with ONLY a single word: either "true" or "false".
        No explanations, no additional text. Just the single word "true" or "false".""",
        "feedback_prompt": """You are providing feedback as a logical and serious judge in a game called "What Beats Rock".
        Your tone is formal, analytical, and emphasizes rational thinking.
        Explain with logical precision why the guess either beats or doesn't beat the current word.
        Keep your explanation to 1-2 sentences, focusing on the rational relationship."""
    },
    "cheery": {
        "system_prompt": """You are an enthusiastic and fun-loving judge in a game called "What Beats Rock"! 
        Your task is to decide if one item beats another in a creative and playful sense.
        You MUST respond with ONLY a single word: either "true" or "false".
        No explanations, no additional text. Just the single word "true" or "false".""",
        "feedback_prompt": """You are providing feedback as an enthusiastic and fun-loving judge in a game called "What Beats Rock"!
        Your tone is playful, energetic, and uses exclamation points and emoji occasionally.
        Explain in a fun, creative way why the guess either beats or doesn't beat the current word.
        Keep your explanation to 1-2 sentences, focusing on the creative relationship."""
    }
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config={
        "temperature": 0.2,
        "top_p": 0.95,
        "max_output_tokens": 30,
    },
    safety_settings=[
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]
)

feedback_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config={
        "temperature": 0.7,
        "top_p": 0.95,
        "max_output_tokens": 150,
    },
    safety_settings=[
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]
)

REQUEST_INTERVAL = 0.5
RATE_LIMIT_KEY = "ai_request:last_time"
FEEDBACK_RATE_LIMIT_KEY = "ai_feedback_request:last_time"

MAX_BACKOFF = 60
INITIAL_BACKOFF = 1

@dataclass
class BackoffState:
    """Thread-safe class to manage backoff state for API retries."""
    backoff_time: float = INITIAL_BACKOFF
    
    def reset(self) -> None:
        """Reset backoff time to initial value."""
        self.backoff_time = INITIAL_BACKOFF
        
    def increase(self) -> float:
        """Increase backoff time exponentially and return the new value."""
        current = self.backoff_time
        self.backoff_time = min(self.backoff_time * 2, MAX_BACKOFF)
        return current

_backoff_state = BackoffState()
_feedback_backoff_state = BackoffState()

async def get_last_request_time() -> float:
    """Get the timestamp of the last request using Redis if available."""
    try:
        from backend.core.redis_client import get_redis_connection
        
        conn = await get_redis_connection()
        last_time_str = await conn.get(RATE_LIMIT_KEY)
        
        if last_time_str:
            return float(last_time_str)
        return 0
    except Exception:
        return asyncio.get_event_loop().time() - REQUEST_INTERVAL

async def get_last_feedback_request_time() -> float:
    """Get the timestamp of the last feedback request using Redis if available."""
    try:
        from backend.core.redis_client import get_redis_connection
        
        conn = await get_redis_connection()
        last_time_str = await conn.get(FEEDBACK_RATE_LIMIT_KEY)
        
        if last_time_str:
            return float(last_time_str)
        return 0
    except Exception:
        return asyncio.get_event_loop().time() - REQUEST_INTERVAL

async def set_last_request_time(timestamp: float) -> None:
    """Set the timestamp of the last request using Redis if available."""
    try:
        from backend.core.redis_client import get_redis_connection
        
        conn = await get_redis_connection()
        await conn.set(RATE_LIMIT_KEY, str(timestamp), ex=60)
    except Exception:
        pass

async def set_last_feedback_request_time(timestamp: float) -> None:
    """Set the timestamp of the last feedback request using Redis if available."""
    try:
        from backend.core.redis_client import get_redis_connection
        
        conn = await get_redis_connection()
        await conn.set(FEEDBACK_RATE_LIMIT_KEY, str(timestamp), ex=60)
    except Exception:
        pass

def parse_ai_response(response_text: str) -> Tuple[bool, float]:
    """
    Parse the AI response to extract a boolean verdict with confidence.
    Optimized for strictly formatted true/false responses.
    
    Args:
        response_text: The text response from the AI
        
    Returns:
        Tuple of (verdict, confidence)
        - verdict: True if response indicates "beats", False otherwise
        - confidence: Value between 0.5 and 1.0 indicating confidence
    """
    text = response_text.strip().lower()
    
    original_text = text
    
    if text == "true":
        return True, 1.0
    elif text == "false":
        return False, 1.0
    
    if re.search(r'^\s*true\s*$', text):
        return True, 0.95
    if re.search(r'^\s*false\s*$', text):
        return False, 0.95
    
    if re.search(r'^\s*yes\s*$', text):
        return True, 0.9
    if re.search(r'^\s*no\s*$', text):
        return False, 0.9
    
    if "true" in text and "false" not in text:
        logger.warning(f"Using fallback true pattern match for: '{original_text}'")
        return True, 0.6
    elif "false" in text and "true" not in text:
        logger.warning(f"Using fallback false pattern match for: '{original_text}'")
        return False, 0.6
    
    logger.warning(f"Could not parse AI response: '{original_text}'. Defaulting to false.")
    return False, 0.0

async def check_if_beats(current_word: str, guess: str, persona: str = "default") -> bool:
    """Check if the guess beats the current word using Gemini API, with distributed rate limiting."""
    global backoff_time
    
    persona_config = PERSONAS.get(persona, PERSONAS["default"])
    system_prompt = persona_config["system_prompt"]
    
    user_prompt = f"Does '{guess}' beat '{current_word}'? Answer only with true or false."
    
    try:
        last_time = await get_last_request_time()
        current_time = asyncio.get_event_loop().time()
        time_since_last_request = current_time - last_time
        
        if time_since_last_request < REQUEST_INTERVAL:
            await asyncio.sleep(REQUEST_INTERVAL - time_since_last_request)
        
        await set_last_request_time(asyncio.get_event_loop().time())
    except Exception as e:
        logger.warning(f"Error in rate limiting: {e}. Continuing with API call.")
    
    max_retries = 3
    retries = 0
    
    while retries < max_retries:
        try:
            response = await asyncio.to_thread(
                model.generate_content,
                [system_prompt, user_prompt]
            )
            
            _backoff_state.reset()
            
            verdict, confidence = parse_ai_response(response.text)
            
            if confidence < 0.7:
                logger.warning(f"Low confidence ({confidence}) parsing: '{response.text}' -> {verdict}")
            
            return verdict
                    
        except Exception as e:
            retries += 1
            logger.error(f"API Error: {str(e)}. Retrying ({retries}/{max_retries})...")
            
            await asyncio.sleep(_backoff_state.increase())
            
            if retries >= max_retries:
                logger.error(f"Failed after {max_retries} attempts. Defaulting to false.")
                return False
    
    return False

async def get_feedback(current_word: str, guess: str, verdict: bool, persona: str = "default") -> str:
    """Get feedback explaining why a guess beats or doesn't beat the current word using Gemini API."""
    persona_config = PERSONAS.get(persona, PERSONAS["default"])
    system_prompt = persona_config["feedback_prompt"]
    
    relation = "beats" if verdict else "doesn't beat"
    user_prompt = f"Explain why '{guess}' {relation} '{current_word}'. Be concise."
    
    try:
        last_time = await get_last_feedback_request_time()
        current_time = asyncio.get_event_loop().time()
        time_since_last_request = current_time - last_time
        
        if time_since_last_request < REQUEST_INTERVAL:
            await asyncio.sleep(REQUEST_INTERVAL - time_since_last_request)
        
        await set_last_feedback_request_time(asyncio.get_event_loop().time())
    except Exception as e:
        logger.warning(f"Error in feedback rate limiting: {e}. Continuing with API call.")
    
    max_retries = 3
    retries = 0
    
    default_feedback = f"{'Correct!' if verdict else 'Incorrect!'} '{guess}' {'beats' if verdict else 'does not beat'} '{current_word}'."
    
    while retries < max_retries:
        try:
            response = await asyncio.to_thread(
                feedback_model.generate_content,
                [system_prompt, user_prompt]
            )
            
            _feedback_backoff_state.reset()
            
            if response and response.text:
                feedback = response.text.strip()
                # Return the full feedback without truncation
                return feedback
            else:
                return default_feedback
                    
        except Exception as e:
            retries += 1
            logger.error(f"Feedback API Error: {str(e)}. Retrying ({retries}/{max_retries})...")
            
            await asyncio.sleep(_feedback_backoff_state.increase())
            
            if retries >= max_retries:
                logger.error(f"Failed to get feedback after {max_retries} attempts. Using default feedback.")
                return default_feedback
    
    return default_feedback
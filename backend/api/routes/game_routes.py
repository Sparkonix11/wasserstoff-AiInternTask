from fastapi import APIRouter, HTTPException, Depends, Header, Query, BackgroundTasks
from typing import List, Optional, Dict
from backend.core.game_logic import GameSession
from backend.core.cache import get_global_count, increment_global_count
from backend.core.redis_client import save_session, get_session, delete_session, get_active_session_count
import redis.asyncio as redis
from backend.db.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from backend.db.models.models import (
    GuessRequest, 
    GuessResponse, 
    GameStartResponse, 
    HistoryResponse,
    LeaderboardResponse,
    StatisticsResponse,
    WordCounter,
    GameSession as DBGameSession,
    GameStatistics,
    PopularWord
)
import json
import uuid
import asyncio
import logging
import time
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.timestamps = {}
        self.max_age = 24 * 60 * 60
        self.operations_since_cleanup = 0

    async def cleanup_if_needed(self):
        """Clean old sessions periodically based on operation count"""
        self.operations_since_cleanup += 1
        if self.operations_since_cleanup >= 100:
            await self.cleanup_old_sessions()
            self.operations_since_cleanup = 0
    
    async def cleanup_old_sessions(self):
        """Remove old sessions from in-memory fallback to prevent memory leaks."""
        current_time = time.monotonic()
        expired_sessions = [
            sid for sid, timestamp in self.timestamps.items() 
            if current_time - timestamp > self.max_age
        ]
        
        for sid in expired_sessions:
            if sid in self.sessions:
                del self.sessions[sid]
            if sid in self.timestamps:
                del self.timestamps[sid]
        
        if expired_sessions:
            logger.info(f"Cleaned {len(expired_sessions)} expired in-memory sessions.")

    def add_session(self, session_id: str, session: GameSession):
        """Add a session to the session manager"""
        self.sessions[session_id] = session
        self.timestamps[session_id] = time.monotonic()

    def get_session(self, session_id: str) -> Optional[GameSession]:
        """Get a session if it exists and isn't expired"""
        if session_id not in self.sessions:
            return None
            
        timestamp = self.timestamps.get(session_id, 0)
        current_time = time.monotonic()
        if current_time - timestamp > self.max_age:
            if session_id in self.sessions:
                del self.sessions[session_id]
            if session_id in self.timestamps:
                del self.timestamps[session_id]
            return None
            
        self.timestamps[session_id] = current_time
        return self.sessions[session_id]
        
    def update_session(self, session_id: str, session: GameSession):
        """Update an existing session"""
        if session_id in self.sessions:
            self.sessions[session_id] = session
            self.timestamps[session_id] = time.monotonic()

    def count_sessions(self) -> int:
        """Count active sessions"""
        return len(self.sessions)

session_manager = SessionManager()

@router.post("/start", response_model=GameStartResponse)
async def start_game(persona: Optional[str] = Query("default"), background_tasks: BackgroundTasks = None):
    """Start a new game session with Rock as the initial word."""
    if background_tasks:
        background_tasks.add_task(session_manager.cleanup_old_sessions)
    else:
        await session_manager.cleanup_if_needed()
    
    session_id = str(uuid.uuid4())
    session = GameSession(initial_word="Rock", persona=persona)
    
    redis_success = await save_session(session_id, session.to_dict())
    
    if not redis_success:
        session_manager.add_session(session_id, session)
    
    global_count = await get_global_count("Rock")
    
    return {
        "session_id": session_id,
        "word": "Rock",
        "message": f"Game started! What beats {session.current_word}?",
        "persona": persona,
        "word_count_message": f"Rock → {global_count} total guesses so far"
    }

async def get_game_session(session_id: str) -> Optional[GameSession]:
    """Retrieve a game session from either Redis or fallback storage."""
    session_data = await get_session(session_id)
    if session_data:
        return GameSession.from_dict(session_data)
    
    return session_manager.get_session(session_id)

async def save_game_session(session_id: str, session: GameSession) -> None:
    """Save a game session to Redis with fallback to in-memory."""
    redis_success = await save_session(session_id, session.to_dict())
    
    if not redis_success:
        session_manager.update_session(session_id, session)

@router.post("/guess", response_model=GuessResponse)
async def make_guess(request: GuessRequest, background_tasks: BackgroundTasks = None):
    """Submit a guess to the game."""
    session_id = request.session_id
    guess = request.guess.strip()
    
    await session_manager.cleanup_if_needed()
    
    session = await get_game_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    if not guess:
        raise HTTPException(status_code=400, detail="Guess cannot be empty")
    
    try:
        result = await session.process_guess(guess)
        
        await save_game_session(session_id, session)
        
        if result.valid:
            await increment_global_count(guess)
        
        global_count = await get_global_count(session.current_word)
        
        word_count_message = f"{session.current_word} → {global_count} total guesses so far"
        
        if result.game_over:
            if background_tasks:
                background_tasks.add_task(save_finished_game_to_db, session_id, session)
            else:
                asyncio.create_task(save_finished_game_to_db(session_id, session))
        
        return {
            "valid": result.valid,
            "message": result.message,
            "new_word": session.current_word if result.valid else None,
            "score": session.score,
            "history": session.get_recent_history(5),
            "global_count": global_count,
            "game_over": session.game_over,
            "word_count_message": word_count_message,
            "ai_feedback": result.ai_feedback  # Include the AI feedback in the response
        }
    except redis.exceptions.RedisError as e:
        logger.error(f"Redis error processing guess: {e}")
        raise HTTPException(status_code=500, detail="Cache error processing guess. Using fallback mechanisms.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except asyncio.TimeoutError:
        logger.error("Timeout error while processing guess")
        raise HTTPException(status_code=504, detail="Request timed out while processing guess")
    except Exception as e:
        logger.error(f"Unexpected error processing guess: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing guess: {str(e)}")

async def save_finished_game_to_db(session_id: str, session: GameSession):
    """Save a finished game to the database with improved error handling."""
    from backend.db.database import get_db_context
    
    try:
        with get_db_context() as db:
            db_session = DBGameSession(
                id=session_id,
                current_word=session.current_word,
                score=session.score,
                game_over=True,
                persona=session.persona,
                history=json.dumps(session.history_list)
            )
            db.add(db_session)
            
            stats = db.query(GameStatistics).filter(GameStatistics.id == 1).first()
            if stats:
                old_total = stats.total_games
                new_avg = stats.avg_score if old_total == 0 else ((stats.avg_score * old_total) + session.score) / (old_total + 1)
                
                stats.total_games += 1
                stats.total_guesses += session.score
                stats.avg_score = new_avg
                stats.max_score = max(stats.max_score, session.score)
            else:
                stats = GameStatistics(
                    id=1,
                    total_games=1,
                    total_guesses=session.score,
                    avg_score=session.score,
                    max_score=session.score
                )
                db.add(stats)
        logger.info(f"Successfully saved game {session_id} with score {session.score} to database")
    except Exception as e:
        logger.error(f"Error saving game statistics: {e}")

@router.get("/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str):
    """Get the full history for a game session."""
    await session_manager.cleanup_if_needed()
    
    session = await get_game_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")
        
    return {"history": session.history_list, "score": session.score}

@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(db: Session = Depends(get_db)):
    """Get a leaderboard of top scores."""
    try:
        top_games = db.query(
            DBGameSession.id, 
            DBGameSession.score,
            DBGameSession.created_at
        ).filter(
            DBGameSession.game_over == True
        ).order_by(
            desc(DBGameSession.score)
        ).limit(10).all()
        
        leaderboard = [
            {
                "position": idx + 1,
                "score": game.score,
                "date": game.created_at.strftime("%Y-%m-%d")
            }
            for idx, game in enumerate(top_games)
        ]
        
        return {"top_scores": leaderboard}
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        return {
            "top_scores": [
                {"position": 1, "score": 15, "date": "2025-04-23"},
                {"position": 2, "score": 12, "date": "2025-04-22"},
                {"position": 3, "score": 10, "date": "2025-04-21"}
            ]
        }

@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(db: Session = Depends(get_db), background_tasks: BackgroundTasks = None):
    """Get global game statistics."""
    try:
        if background_tasks:
            background_tasks.add_task(session_manager.cleanup_old_sessions)
        else:
            await session_manager.cleanup_if_needed()
        
        active_sessions = await get_active_session_count()
        active_sessions += session_manager.count_sessions()
        
        popular_words_db = db.query(
            WordCounter.word,
            WordCounter.count
        ).order_by(
            desc(WordCounter.count)
        ).limit(5).all()
        
        popular_words = [
            {"word": word.word, "count": word.count}
            for word in popular_words_db
        ]
        
        if not popular_words:
            popular_words = [
                {"word": "Paper", "count": 125},
                {"word": "Scissors", "count": 98},
                {"word": "Rock", "count": 87}
            ]
        
        return {
            "active_sessions": active_sessions,
            "popular_words": popular_words
        }
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        return {
            "active_sessions": session_manager.count_sessions(),
            "popular_words": [
                {"word": "Paper", "count": 125},
                {"word": "Scissors", "count": 98},
                {"word": "Rock", "count": 87}
            ]
        }
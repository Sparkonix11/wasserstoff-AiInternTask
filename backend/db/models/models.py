from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import datetime
from pydantic import BaseModel
from typing import List, Optional

Base = declarative_base()

# SQLAlchemy Models
class WordCounter(Base):
    """Model to store global counters for each unique answer."""
    __tablename__ = "word_counters"
    
    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(255), unique=True, index=True, nullable=False)
    count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class WordPairCounter(Base):
    """Model to store counters for word pairs (what beats what)."""
    __tablename__ = "word_pair_counters"
    
    id = Column(Integer, primary_key=True, index=True)
    word1 = Column(String(255), nullable=False, index=True)  # The word that is beaten
    word2 = Column(String(255), nullable=False, index=True)  # The word that beats
    count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Composite index for fast lookups
    __table_args__ = (
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )
    
class VerdictCache(Base):
    """Model to store AI verdicts for word pairs."""
    __tablename__ = "verdict_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    word1 = Column(String(255), nullable=False)
    word2 = Column(String(255), nullable=False)
    verdict = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Composite index for fast lookups
    __table_args__ = (
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )

class GameSession(Base):
    """Model to store information about a game session."""
    __tablename__ = "game_sessions"
    
    id = Column(String(36), primary_key=True)
    current_word = Column(String(255), nullable=False)
    score = Column(Integer, default=0)
    game_over = Column(Boolean, default=False)
    persona = Column(String(50), default="default")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    history = Column(Text, nullable=False)  # JSON serialized history
    
class GameStatistics(Base):
    """Model to store global game statistics."""
    __tablename__ = "game_statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    total_games = Column(Integer, default=0)
    total_guesses = Column(Integer, default=0)
    avg_score = Column(Float, default=0.0)
    max_score = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Pydantic Models for API
class GuessRequest(BaseModel):
    """Request model for submitting a guess."""
    guess: str
    session_id: str

class GuessResponse(BaseModel):
    """Response model for guess results."""
    valid: bool
    message: str
    new_word: Optional[str] = None
    score: int
    history: List[str]
    global_count: int
    game_over: bool
    word_count_message: Optional[str] = None  # Field for per-answer counter message
    ai_feedback: Optional[str] = None  # New field for AI-generated feedback

class GameStartResponse(BaseModel):
    """Response model for starting a new game."""
    session_id: str
    word: str
    message: str
    persona: str
    word_count_message: Optional[str] = None  # New field for per-answer counter message

class HistoryResponse(BaseModel):
    """Response model for game history."""
    history: List[str]
    score: int

class LeaderboardEntry(BaseModel):
    """Model for a leaderboard entry."""
    position: int
    score: int
    date: str

class LeaderboardResponse(BaseModel):
    """Response model for leaderboard data."""
    top_scores: List[LeaderboardEntry]

class PopularWord(BaseModel):
    """Model for popular word statistics."""
    word: str
    count: int

class PopularWordPair(BaseModel):
    """Model for popular word pair statistics."""
    beaten_word: str
    beating_word: str
    count: int

class StatisticsResponse(BaseModel):
    """Response model for game statistics."""
    active_sessions: int
    popular_words: List[PopularWord]
    popular_word_pairs: List[PopularWordPair]
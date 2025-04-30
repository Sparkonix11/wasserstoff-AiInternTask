from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass
from pydantic import BaseModel
from backend.core.ai_client import check_if_beats, get_feedback
from backend.core.moderation import moderate_content
from backend.core.cache import get_verdict_from_cache, save_verdict_to_cache
import asyncio

@dataclass
class GuessResult:
    valid: bool
    message: str
    game_over: bool = False
    ai_feedback: str = ""

class GameSession:
    def __init__(self, initial_word: str = "Rock", persona: str = "default"):
        self.history_list: List[str] = [initial_word]
        self.current_word: str = initial_word
        self.score: int = 0
        self.game_over: bool = False
        self.persona: str = persona
        self.seen_guesses: Set[str] = {initial_word.lower()}
    
    async def process_guess(self, guess: str) -> GuessResult:
        """Process a player's guess and determine if it beats the current word."""
        if self.game_over:
            return GuessResult(
                valid=False, 
                message="Game is already over. Start a new game.",
                game_over=True
            )
        
        lowercase_guess = guess.lower()
        
        if lowercase_guess in self.seen_guesses:
            self.game_over = True
            return GuessResult(
                valid=False,
                message=f"Game over! '{guess}' has already been used in this game.",
                game_over=True
            )
        
        moderation_result = await moderate_content(guess)
        if not moderation_result.is_acceptable:
            return GuessResult(
                valid=False,
                message=f"That guess contains inappropriate content: {moderation_result.reason}"
            )
            
        from backend.core.moderation import check_for_prompt_injection
        is_safe, reason = await check_for_prompt_injection(guess)
        if not is_safe:
            return GuessResult(
                valid=False,
                message=f"That guess was rejected: {reason}"
            )
            
        cache_key = f"{self.current_word.lower()}:{lowercase_guess}"
        cached_verdict = await get_verdict_from_cache(cache_key)
        
        if cached_verdict is not None:
            return await self._process_verdict_with_feedback(guess, cached_verdict)
        
        verdict = await check_if_beats(self.current_word, guess, self.persona)
        
        await save_verdict_to_cache(cache_key, verdict)
        
        return await self._process_verdict_with_feedback(guess, verdict)
    
    async def _process_verdict_with_feedback(self, guess: str, beats: bool) -> GuessResult:
        """Process the verdict, get AI feedback, and update the game state."""
        # Get AI-generated feedback based on persona
        ai_feedback = await get_feedback(self.current_word, guess, beats, self.persona)
        
        if beats:
            self.current_word = guess
            self.history_list.append(guess)
            self.seen_guesses.add(guess.lower())
            self.score += 1
            return GuessResult(
                valid=True, 
                message=f"Correct! '{guess}' beats '{self.history_list[-2]}'. What beats {guess}?",
                ai_feedback=ai_feedback
            )
        else:
            self.game_over = True
            return GuessResult(
                valid=False,
                message=f"Game over! '{guess}' doesn't beat '{self.current_word}'.",
                game_over=True,
                ai_feedback=ai_feedback
            )
    
    def get_recent_history(self, count: int) -> List[str]:
        """Get the most recent items from the history."""
        return self.history_list[-count:] if len(self.history_list) > count else self.history_list
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization."""
        return {
            "history_list": self.history_list,
            "current_word": self.current_word,
            "score": self.score,
            "game_over": self.game_over,
            "persona": self.persona,
            "seen_guesses": list(self.seen_guesses)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameSession':
        """Create session from dictionary after deserialization."""
        session = cls(
            initial_word=data["current_word"],
            persona=data["persona"]
        )
        session.history_list = data["history_list"]
        session.score = data["score"]
        session.game_over = data["game_over"]
        session.seen_guesses = set(data["seen_guesses"])
        return session
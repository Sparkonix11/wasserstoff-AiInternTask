from dataclasses import dataclass
import re
from typing import List, Set, Tuple
import string

@dataclass
class ModerationResult:
    is_acceptable: bool
    reason: str = ""

PROFANITY_LIST: Set[str] = {
    "profanity1", "profanity2", "badword1", "badword2",
    "ass", "asshole", "bitch", "bullshit", "crap", "cunt", "damn", "dick", "fuck", 
    "piss", "shit", "slut", "whore"
}

EVASION_PATTERNS = [
    r'f+[^a-z]*u+[^a-z]*c+[^a-z]*k+',
    r's+[^a-z]*h+[^a-z]*i+[^a-z]*t+',
    r'b+[^a-z]*i+[^a-z]*t+[^a-z]*c+[^a-z]*h+',
]

def get_leetspeak_variants(word: str) -> List[str]:
    """
    Generate common leetspeak variants of a word to catch evasion attempts.
    For example: "ass" -> "a55", "@ss", etc.
    """
    substitutions = {
        'a': ['a', '@', '4'],
        'b': ['b', '8'],
        'e': ['e', '3'],
        'i': ['i', '1', '!'],
        'l': ['l', '1'],
        'o': ['o', '0'],
        's': ['s', '5', '$'],
        't': ['t', '7'],
    }
    
    base = [word]
    for char, replacements in substitutions.items():
        if char in word:
            new_variants = []
            for variant in base:
                for replacement in replacements:
                    if replacement != char:
                        new_variants.append(variant.replace(char, replacement))
            base.extend(new_variants)
    
    return base

EXPANDED_PROFANITY_LIST: Set[str] = set()
for word in PROFANITY_LIST:
    EXPANDED_PROFANITY_LIST.add(word)
    EXPANDED_PROFANITY_LIST.update(get_leetspeak_variants(word))

def normalize_text(text: str) -> str:
    """Normalize text to detect evasion attempts."""
    normalized = text.lower()
    normalized = re.sub(r'\s+', '', normalized)
    normalized = re.sub(r'[^\w\s]', '', normalized)
    return normalized

async def moderate_content(text: str) -> ModerationResult:
    """
    Moderate content to ensure it doesn't contain inappropriate language.
    Returns a ModerationResult with a boolean indicating if the content is acceptable.
    """
    original_text = text
    text_lower = text.lower()
    normalized = normalize_text(text)
    
    if not text or len(text.strip()) < 2:
        return ModerationResult(
            is_acceptable=False,
            reason="Content is too short"
        )
    
    for word in EXPANDED_PROFANITY_LIST:
        if word in text_lower:
            return ModerationResult(
                is_acceptable=False,
                reason="Content contains inappropriate language"
            )
    
    for pattern in EVASION_PATTERNS:
        if re.search(pattern, text_lower):
            return ModerationResult(
                is_acceptable=False,
                reason="Content contains inappropriate language"
            )
    
    words = text_lower.split()
    for word in words:
        clean_word = word.strip(string.punctuation)
        if clean_word in EXPANDED_PROFANITY_LIST:
            return ModerationResult(
                is_acceptable=False,
                reason="Content contains inappropriate language"
            )
    
    special_char_ratio = sum(1 for c in text if not c.isalnum()) / max(len(text), 1)
    if special_char_ratio > 0.5:
        return ModerationResult(
            is_acceptable=False,
            reason="Content contains too many special characters"
        )
    
    if any(c * 5 in text for c in text):
        return ModerationResult(
            is_acceptable=False,
            reason="Content contains repetitive patterns"
        )
        
    if any(len(word) > 30 for word in words):
        return ModerationResult(
            is_acceptable=False,
            reason="Content contains suspiciously long words"
        )
        
    return ModerationResult(is_acceptable=True)

async def is_safe_for_ai(text: str) -> bool:
    """
    Determine if text is safe to send to the AI.
    This is a basic implementation - in production, consider
    using a more comprehensive moderation API or pre-trained model.
    """
    result = await moderate_content(text)
    return result.is_acceptable

async def check_for_prompt_injection(text: str) -> Tuple[bool, str]:
    """
    Check for potential prompt injection attempts.
    Returns (is_safe, reason)
    """
    injection_patterns = [
        r"ignore (previous|above|all) instructions",
        r"disregard .*? instructions",
        r"do not (follow|adhere to) .*? (instructions|rules)",
        r"new instructions",
        r"your (real|actual) purpose",
        r"you (are|will) (now|actually) (act|work) as",
        r"system (prompt|message|instruction)",
    ]
    
    text_lower = text.lower()
    
    for pattern in injection_patterns:
        if re.search(pattern, text_lower):
            return False, "Potential prompt injection attempt detected"
    
    return True, ""
import asyncio
import unittest
from backend.core.game_logic import GameSession, GuessResult

class TestDuplicateGuessPath(unittest.TestCase):
    """Test the duplicate-guess game-over path."""
    
    def setUp(self):
        """Set up a game session for testing."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.session = GameSession(initial_word="Rock")
    
    def tearDown(self):
        """Clean up after tests."""
        self.loop.close()
    
    def test_duplicate_guess_ends_game(self):
        """Test that submitting a duplicate guess ends the game."""
        # First valid guess - Paper beats Rock
        result = self.loop.run_until_complete(self.session.process_guess("Paper"))
        self.assertTrue(result.valid)
        self.assertEqual(self.session.current_word, "Paper")
        self.assertEqual(self.session.score, 1)
        self.assertFalse(self.session.game_over)
        
        # Second valid guess - Scissors beats Paper
        result = self.loop.run_until_complete(self.session.process_guess("Scissors"))
        self.assertTrue(result.valid)
        self.assertEqual(self.session.current_word, "Scissors")
        self.assertEqual(self.session.score, 2)
        self.assertFalse(self.session.game_over)
        
        # Third valid guess - Rock beats Scissors
        result = self.loop.run_until_complete(self.session.process_guess("Rock"))
        self.assertTrue(result.valid)
        self.assertEqual(self.session.current_word, "Rock")
        self.assertEqual(self.session.score, 3)
        self.assertFalse(self.session.game_over)
        
        # Duplicate guess - Paper was already used
        result = self.loop.run_until_complete(self.session.process_guess("Paper"))
        self.assertFalse(result.valid)
        self.assertTrue(result.game_over)
        self.assertTrue(self.session.game_over)
        
    def test_case_insensitive_duplicate_detection(self):
        """Test that duplicate detection is case-insensitive."""
        # First valid guess - Paper beats Rock
        result = self.loop.run_until_complete(self.session.process_guess("Paper"))
        self.assertTrue(result.valid)
        
        # Duplicate with different case - should still be detected as duplicate
        result = self.loop.run_until_complete(self.session.process_guess("PAPER"))
        self.assertFalse(result.valid)
        self.assertTrue(result.game_over)
        self.assertTrue(self.session.game_over)

if __name__ == '__main__':
    unittest.main()
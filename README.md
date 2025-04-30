# What Beats Rock

A creative AI-powered guessing game where players challenge themselves to create chains of items that beat each other.

## Overview

"What Beats Rock" is an innovative web game inspired by the classic "Rock, Paper, Scissors" but expanded infinitely using AI. Players start with "Rock" and must guess what beats the current word. For every correct guess, the new word becomes the target, and the chain continues. The game ends when a player guesses incorrectly or repeats a previously used word.

Video - https://drive.google.com/file/d/1HbAUyf8ya-YvFqzgrZAPcwvjWjGGhipc/view?usp=sharing

## How to Play

1. Start with the initial word "Rock"
2. Enter what you think beats the current word (e.g., "Paper" beats "Rock")
3. If correct, your new word becomes the target (now you must guess what beats "Paper")
4. Continue the chain as long as possible to achieve a high score
5. Game ends if your guess is incorrect or if you use a word that's already appeared in the chain

## Setup Instructions

### Prerequisites

- Docker and Docker Compose
- Node.js 16+ (for local development)
- Python 3.9+ (for local development)

### Running with Docker

1. Clone the repository
2. Set up environment variables:
   ```
   cp .env.example .env
   ```
3. Add your Gemini API key to the `.env` file:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
4. Start the application:
   ```
   docker-compose up -d
   ```
5. Access the game at http://localhost:3000

### Local Development Setup

#### Backend
```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the backend server
uvicorn backend.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm start
```

## Architecture Overview

The project follows a modern web architecture with a React frontend and FastAPI backend:

### Backend
- **FastAPI**: Main web framework for RESTful API
- **Gemini AI**: Powers the game logic to determine if one item beats another
- **Redis**: Session management and caching of AI verdicts
- **SQLAlchemy**: ORM for database operations
- **Alembic**: Database migrations

### Frontend
- **React**: UI framework
- **Axios**: HTTP client
- **CSS**: Custom styling with animations and responsive design

## Prompt Engineering

The game relies on carefully designed prompts for the Gemini AI model:

1. **Verdict Prompts**: Determine whether one item beats another
   - Strict output format (single word: "true" or "false")
   - System instructions to evaluate conceptual "beating" relationships

2. **Feedback Prompts**: Generate natural language feedback
   - Multiple personas (default, serious, cheery) for varied user experience
   - Controlled length (1-2 sentences) for consistent UI presentation

3. **Content Moderation**: Additional prompts ensure appropriate content
   - Filter inappropriate words/phrases
   - Detect prompt injection attempts

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
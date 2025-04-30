import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import GameInput from './GameInput';
import GameStats from './GameStats';
import GameHistory from './GameHistory';
import GameOverModal from './GameOverModal';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const ERROR_TYPES = {
  NETWORK: 'network',
  SERVER: 'server',
  TIMEOUT: 'timeout',
  UNKNOWN: 'unknown'
};

const GameContainer = ({ persona }) => {
  const [sessionId, setSessionId] = useState('');
  const [currentWord, setCurrentWord] = useState('Rock');
  const [score, setScore] = useState(0);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('info');
  const [history, setHistory] = useState(['Rock']);
  const [wordCountMessage, setWordCountMessage] = useState('');
  const [isGameOver, setIsGameOver] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [animation, setAnimation] = useState('');
  const [hasGuessed, setHasGuessed] = useState(false);
  const messageRef = useRef(null);
  
  const setFeedbackAnimation = (isCorrect) => {
    const animationType = isCorrect ? 'correct' : 'incorrect';
    const animationClass = `animate-${animationType}-${persona}`;
    setAnimation(animationClass);
    
    setTimeout(() => {
      setAnimation('');
    }, 1000);
  };
  
  const handleApiError = (error, context) => {
    setError(null);
    
    console.error(`Error in ${context}:`, error);
    
    let errorType = ERROR_TYPES.UNKNOWN;
    let errorDetails = '';
    let userMessage = `Failed to ${context}. Please try again.`;
    
    if (error.response) {
      errorType = ERROR_TYPES.SERVER;
      errorDetails = `Status: ${error.response.status}, Data: ${JSON.stringify(error.response.data)}`;
      
      if (error.response.data && error.response.data.detail) {
        userMessage = `Server error: ${error.response.data.detail}`;
      }
    } else if (error.request) {
      errorType = ERROR_TYPES.NETWORK;
      errorDetails = 'No response received from server';
      userMessage = 'Network error. Cannot reach the server.';
    } else if (error.code === 'ECONNABORTED') {
      errorType = ERROR_TYPES.TIMEOUT;
      errorDetails = 'Request timed out';
      userMessage = 'Request timed out. Please try again later.';
    }
    
    setError({
      type: errorType,
      message: error.message,
      details: errorDetails,
      context
    });
    
    setMessage(userMessage);
    setMessageType('error');
    setIsLoading(false);
    
    if (process.env.NODE_ENV === 'development') {
      console.group(`API Error Details (${context})`);
      console.log('Type:', errorType);
      console.log('Message:', error.message);
      console.log('Details:', errorDetails);
      if (error.response) {
        console.log('Response:', error.response);
      }
      console.groupEnd();
    }
  };
  
  const startGame = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await axios.post(`${API_URL}/start`, null, {
        params: { persona },
        timeout: 10000
      });
      
      setSessionId(response.data.session_id);
      setCurrentWord(response.data.word);
      setScore(0);
      setMessage(response.data.message);
      setMessageType('info');
      setHistory([response.data.word]);
      setWordCountMessage(response.data.word_count_message || '');
      setIsGameOver(false);
      setIsLoading(false);
    } catch (error) {
      handleApiError(error, 'start game');
    }
  }, [persona]);
  
  const handleGuess = async (guess) => {
    if (!sessionId || isLoading || isGameOver) return;
    
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await axios.post(`${API_URL}/guess`, {
        guess,
        session_id: sessionId
      }, {
        timeout: 10000
      });
      
      const { valid, new_word, score: newScore, history: newHistory, word_count_message, game_over, ai_feedback } = response.data;
      
      // Use AI feedback if available, otherwise fallback to the standard message
      const feedbackMessage = ai_feedback || response.data.message;
      
      if (valid) {
        setMessage(feedbackMessage);
        setFeedbackAnimation(true);
        
        setCurrentWord(new_word);
        setScore(newScore);
        setHistory(newHistory);
        setWordCountMessage(word_count_message || '');
        setHasGuessed(true);
      } else {
        setMessage(feedbackMessage);
        setFeedbackAnimation(false);
      }
      
      setMessageType(valid ? 'success' : game_over ? 'error' : 'info');
      
      if (game_over) {
        setIsGameOver(true);
      }
      
      setIsLoading(false);
    } catch (error) {
      handleApiError(error, 'submit guess');
    }
  };
  
  const DevDebugPanel = () => {
    if (process.env.NODE_ENV !== 'development' || !error) return null;
    
    return (
      <div className="dev-debug-panel">
        <h4>Development Debug Info</h4>
        <p><strong>Error Type:</strong> {error.type}</p>
        <p><strong>Context:</strong> {error.context}</p>
        <p><strong>Message:</strong> {error.message}</p>
        {error.details && <p><strong>Details:</strong> {error.details}</p>}
      </div>
    );
  };
  
  useEffect(() => {
    startGame();
  }, [persona, startGame]);
  
  useEffect(() => {
    startGame();
  }, [startGame]);
  
  return (
    <div className={`game-container persona-${persona}`}>
      <h2>What Beats Rock</h2>
      
      <div className="current-word">
        Current Word: <span className={`word-highlight ${animation}`}>{currentWord}</span>
      </div>
      
      <div ref={messageRef} className={`game-message message-${messageType} ${animation}`}>
        {message}
      </div>
      
      {process.env.NODE_ENV === 'development' && <DevDebugPanel />}
      
      <GameInput onGuess={handleGuess} disabled={isLoading || isGameOver} />
      
      <GameStats score={score} wordCountMessage={hasGuessed ? wordCountMessage : ''} />
      
      <GameHistory history={history} />
      
      {isGameOver && (
        <GameOverModal score={score} onNewGame={startGame} />
      )}
    </div>
  );
};

export default GameContainer;
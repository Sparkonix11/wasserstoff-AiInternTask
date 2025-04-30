import React from 'react';

const GameStats = ({ score, wordCountMessage }) => {
  return (
    <div className="game-stats">
      <div className="stat-item">
        <div className="stat-value">{score}</div>
        <div className="stat-label">Your Score</div>
      </div>
      
      {wordCountMessage && (
        <div className="stat-item word-counter">
          <div className="stat-value word-count-message">{wordCountMessage}</div>
          <div className="stat-label">Word Counter</div>
        </div>
      )}
    </div>
  );
};

export default GameStats;
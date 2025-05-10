import React from 'react';

const GameStats = ({ score, wordCountMessage }) => {
  // Check if the wordCountMessage contains pair count information
  const hasPairCount = wordCountMessage && wordCountMessage.includes('|');
  
  let singleWordCount, pairCountInfo;
  
  if (hasPairCount) {
    // Split the message into individual word count and pair count
    [singleWordCount, pairCountInfo] = wordCountMessage.split('|').map(s => s.trim());
  } else {
    singleWordCount = wordCountMessage;
  }
  
  return (
    <div className="game-stats">
      <div className="stat-item">
        <div className="stat-value">{score}</div>
        <div className="stat-label">Your Score</div>
      </div>
      
      {singleWordCount && (
        <div className="stat-item word-counter">
          <div className="stat-value word-count-message">{singleWordCount}</div>
          <div className="stat-label">Word Counter</div>
        </div>
      )}
      
      {pairCountInfo && (
        <div className="stat-item pair-counter">
          <div className="stat-value pair-count-message">{pairCountInfo}</div>
          <div className="stat-label">Pairing Counter</div>
        </div>
      )}
    </div>
  );
};

export default GameStats;
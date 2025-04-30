import React from 'react';

const GameHistory = ({ history }) => {
  return (
    <div className="game-history">
      <h3>History</h3>
      <ul className="history-list">
        {history.map((word, index) => (
          <li key={index} className="history-item">
            <div className="history-number">{index + 1}</div>
            <div className="history-word">{word}</div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default GameHistory;
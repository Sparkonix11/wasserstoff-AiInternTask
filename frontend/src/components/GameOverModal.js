import React from 'react';

const GameOverModal = ({ score, onNewGame }) => {
  return (
    <div className="game-over-modal">
      <div className="modal-content">
        <h2 className="modal-title">Game Over!</h2>
        <p>You made it to a score of <strong>{score}</strong>!</p>
        <p>Game over! You either submitted a duplicate word or your answer was incorrect.</p>
        <button className="modal-button" onClick={onNewGame}>
          Start New Game
        </button>
      </div>
    </div>
  );
};

export default GameOverModal;
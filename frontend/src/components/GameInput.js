import React, { useState } from 'react';

const GameInput = ({ onGuess, disabled }) => {
  const [inputValue, setInputValue] = useState('');
  
  const handleInputChange = (e) => {
    setInputValue(e.target.value);
  };
  
  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (inputValue.trim()) {
      onGuess(inputValue.trim());
      setInputValue('');
    }
  };
  
  return (
    <form className="game-input" onSubmit={handleSubmit}>
      <input
        type="text"
        value={inputValue}
        onChange={handleInputChange}
        placeholder="Enter what beats the current word..."
        disabled={disabled}
        autoFocus
      />
      <button type="submit" disabled={disabled || !inputValue.trim()}>
        {disabled ? 'Processing...' : 'Submit'}
      </button>
    </form>
  );
};

export default GameInput;
import React from 'react';

const Header = ({ onPersonaChange, persona }) => {
  return (
    <header className="App-header">
      <h1>What Beats Rock</h1>
      <div className="persona-selector">
        <button 
          className={`persona-button ${persona === 'default' ? 'active' : ''}`}
          onClick={() => onPersonaChange('default')}
        >
          Default
        </button>
        <button 
          className={`persona-button ${persona === 'serious' ? 'active' : ''}`}
          onClick={() => onPersonaChange('serious')}
        >
          Serious
        </button>
        <button 
          className={`persona-button ${persona === 'cheery' ? 'active' : ''}`}
          onClick={() => onPersonaChange('cheery')}
        >
          Cheery
        </button>
      </div>
    </header>
  );
};

export default Header;
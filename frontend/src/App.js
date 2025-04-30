import React, { useState, useEffect } from 'react';
import './App.css';
import GameContainer from './components/GameContainer';
import Header from './components/Header';
import Footer from './components/Footer';

function App() {
  const [persona, setPersona] = useState('default');
  
  const handlePersonaChange = (newPersona) => {
    setPersona(newPersona);
  };

  return (
    <div className="App">
      <Header onPersonaChange={handlePersonaChange} persona={persona} />
      <main className="App-main">
        <GameContainer persona={persona} />
      </main>
      <Footer />
    </div>
  );
}

export default App;
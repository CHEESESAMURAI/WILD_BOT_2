import React from 'react';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>WB-Analyzer</h1>
        <p>
          Анализ товаров и ниш на Wildberries
        </p>
        <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <a href="/login" style={{ color: 'white' }}>Вход</a>
          <a href="/signup" style={{ color: 'white' }}>Регистрация</a>
        </div>
      </header>
    </div>
  );
}

export default App; 
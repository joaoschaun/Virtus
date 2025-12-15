import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Error handler global
window.onerror = (msg, url, line, col, error) => {
  console.error('Global error:', { msg, url, line, col, error })
}

window.onunhandledrejection = (event) => {
  console.error('Unhandled promise rejection:', event.reason)
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

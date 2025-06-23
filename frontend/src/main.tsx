// Improved main.tsx with error boundary and better structure
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';

import SRTControlPanel from './SRTControlPanel.tsx';
import ErrorBoundary from './ErrorBoundary.tsx';

// Check for required environment variables
const requiredEnvVars = {
  VITE_API_URL: import.meta.env.VITE_API_URL,
  VITE_SRT_IP: import.meta.env.VITE_SRT_IP
};

// Log environment variables for debugging
console.log('Environment Variables:', {
  API_URL: requiredEnvVars.VITE_API_URL || 'http://localhost:5000 (default)',
  SRT_IP: requiredEnvVars.VITE_SRT_IP || '127.0.0.1 (default)'
});

// Warn about missing environment variables
Object.entries(requiredEnvVars).forEach(([key, value]) => {
  if (!value) {
    console.warn(`⚠️ Environment variable ${key} is not set. Using default values.`);
  }
});

// Global error handler for unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason);
  
  // You can show a user-friendly message or report the error
  if (import.meta.env.DEV) {
    console.error('Full rejection event:', event);
  }
});

// Global error handler for uncaught errors
window.addEventListener('error', (event) => {
  console.error('Uncaught error:', event.error);
  
  if (import.meta.env.DEV) {
    console.error('Full error event:', event);
  }
});

const root = document.getElementById('root');

if (!root) {
  throw new Error('Root element not found. Make sure your HTML file has a div with id="root"');
}

createRoot(root).render(
  <StrictMode>
    <ErrorBoundary fallback={
      <div style={{ 
        padding: '40px', 
        textAlign: 'center',
        backgroundColor: '#f8f9fa',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center'
      }}>
        <h1 style={{ color: '#dc3545', marginBottom: '20px' }}>
          🚨 SRT Control Panel Error
        </h1>
        <p style={{ color: '#6c757d', marginBottom: '20px' }}>
          The application encountered an unexpected error.
        </p>
        <button 
          onClick={() => window.location.reload()}
          style={{
            padding: '12px 24px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '16px'
          }}
        >
          Reload Application
        </button>
      </div>
    }>
      <div className="app-container" style={{ 
        padding: '20px',
        minHeight: '100vh',
        backgroundColor: '#f8f9fa'
      }}>
        <header style={{ 
          textAlign: 'center', 
          marginBottom: '30px',
          padding: '20px',
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          <h1 style={{ 
            margin: '0 0 10px 0',
            color: '#333',
            fontSize: '2rem'
          }}>
            Multi-Screen SRT Control Panel
          </h1>
          <p style={{ 
            margin: 0,
            color: '#6c757d',
            fontSize: '1rem'
          }}>
            Group Management & Client Control System
          </p>
        </header>
        
        <main>
          <SRTControlPanel />
        </main>
        
        <footer style={{ 
          textAlign: 'center', 
          marginTop: '40px',
          padding: '20px',
          color: '#6c757d',
          fontSize: '0.9rem'
        }}>
          <p>
            API: {requiredEnvVars.VITE_API_URL || 'http://localhost:5000'} | 
            SRT: {requiredEnvVars.VITE_SRT_IP || '127.0.0.1'}
          </p>
        </footer>
      </div>
    </ErrorBoundary>
  </StrictMode>
);
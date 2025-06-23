// ErrorBoundary.tsx - Add this component to catch React errors
import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="error-boundary">
          <div style={{ 
            padding: '20px', 
            margin: '20px', 
            border: '2px solid #dc3545', 
            borderRadius: '8px', 
            backgroundColor: '#f8d7da',
            color: '#721c24'
          }}>
            <h2>🚨 Application Error</h2>
            <p>Something went wrong with the SRT Control Panel.</p>
            
            <details style={{ marginTop: '10px' }}>
              <summary>Error Details</summary>
              <pre style={{ 
                background: '#fff', 
                padding: '10px', 
                borderRadius: '4px', 
                marginTop: '10px',
                fontSize: '12px',
                overflow: 'auto'
              }}>
                {this.state.error?.message}
                {this.state.errorInfo?.componentStack}
              </pre>
            </details>
            
            <button 
              onClick={() => this.setState({ hasError: false, error: undefined, errorInfo: undefined })}
              style={{
                marginTop: '10px',
                padding: '8px 16px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Try Again
            </button>
            
            <button 
              onClick={() => window.location.reload()}
              style={{
                marginTop: '10px',
                marginLeft: '10px',
                padding: '8px 16px',
                backgroundColor: '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
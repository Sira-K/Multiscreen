import React from 'react';
import ErrorSystemTabs from './ErrorSystemTabs';
import './ErrorSystemDemo.css';

/**
 * Error System Demo - Demonstrates the new tabbed error system interface
 * This component shows how to integrate the ErrorSystemTabs into your application
 */
const ErrorSystemDemo = () => {
    return (
        <div className="error-system-demo">
            <div className="demo-header">
                <h1>🚨 Error System Demo</h1>
                <p>Welcome to the comprehensive error handling and testing system</p>
            </div>
            
            <div className="demo-content">
                <ErrorSystemTabs />
            </div>
            
            <div className="demo-footer">
                <h3>🎯 How to Use This Component</h3>
                <div className="usage-steps">
                    <div className="step">
                        <span className="step-number">1</span>
                        <div className="step-content">
                            <h4>Import the Component</h4>
                            <code>import ErrorSystemTabs from './ErrorSystemTabs';</code>
                        </div>
                    </div>
                    
                    <div className="step">
                        <span className="step-number">2</span>
                        <div className="step-content">
                            <h4>Use in Your App</h4>
                            <code>{'<ErrorSystemTabs />'}</code>
                        </div>
                    </div>
                    
                    <div className="step">
                        <span className="step-number">3</span>
                        <div className="step-content">
                            <h4>Navigate Between Tabs</h4>
                            <p>Switch between Testing, Examples, and Documentation tabs</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ErrorSystemDemo;

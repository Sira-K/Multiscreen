import React from 'react';
import ErrorSystemTabs from './ErrorSystemTabs';
import './ErrorSystemTest.css';

/**
 * Error System Test - Simple test page for local testing
 * This component provides a minimal environment to test the tabs
 */
const ErrorSystemTest = () => {
    return (
        <div className="error-system-test">
            <div className="test-header">
                <h1> Error System Tabs - Local Test</h1>
                <p>Test the new tabbed interface locally</p>
            </div>

            <div className="test-content">
                <ErrorSystemTabs />
            </div>

            <div className="test-info">
                <h3> Test Instructions</h3>
                <ol>
                    <li><strong>Click on different tabs</strong> to see the navigation</li>
                    <li><strong>Test the Error Testing tab</strong> - try clicking different error buttons</li>
                    <li><strong>Explore the Examples tab</strong> - view code examples</li>
                    <li><strong>Check the Documentation tab</strong> - browse error codes and troubleshooting</li>
                    <li><strong>Test responsiveness</strong> - resize your browser window</li>
                </ol>

                <div className="test-notes">
                    <h4> What to Look For:</h4>
                    <ul>
                        <li> Tab switching works smoothly</li>
                        <li> Error notifications appear when testing</li>
                        <li> Responsive design on different screen sizes</li>
                        <li> Smooth animations and transitions</li>
                        <li> All error types can be tested</li>
                    </ul>
                </div>
            </div>
        </div>
    );
};

export default ErrorSystemTest;


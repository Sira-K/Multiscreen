import React, { useState, useEffect } from 'react';
import './ErrorNotification.css';

const ErrorNotification = ({ error, onClose, onRetry }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [errorDetails, setErrorDetails] = useState(null);
    const [loading, setLoading] = useState(false);

    // Fetch detailed error information when error changes
    useEffect(() => {
        if (error && error.error_code) {
            fetchErrorDetails(error.error_code);
        }
    }, [error]);

    const fetchErrorDetails = async (errorCode) => {
        setLoading(true);
        try {
            const response = await fetch(`/errors/error/${errorCode}`);
            const data = await response.json();

            if (data.success) {
                setErrorDetails(data.error_details);
            } else {
                // Fallback to basic error info
                setErrorDetails({
                    message: error.message || 'Unknown error',
                    meaning: 'Error details not available',
                    common_causes: ['System error', 'Configuration issue'],
                    primary_solution: 'Check system logs and try again',
                    detailed_solutions: ['Restart the service', 'Verify configuration'],
                    troubleshooting_steps: {
                        immediate_actions: ['Check the primary solution above'],
                        diagnostic_commands: ['Check system logs'],
                        escalation_steps: ['Contact support if issue persists']
                    }
                });
            }
        } catch (err) {
            console.error('Failed to fetch error details:', err);
            // Use fallback error info
            setErrorDetails({
                message: error.message || 'Unknown error',
                meaning: 'Error details not available',
                common_causes: ['System error', 'Configuration issue'],
                primary_solution: 'Check system logs and try again',
                detailed_solutions: ['Restart the service', 'Verify configuration'],
                troubleshooting_steps: {
                    immediate_actions: ['Check the primary solution above'],
                    diagnostic_commands: ['Check system logs'],
                    escalation_steps: ['Contact support if issue persists']
                }
            });
        } finally {
            setLoading(false);
        }
    };

    if (!error) return null;

    const getErrorIcon = (category) => {
        switch (category) {
            case '1xx': return '🎬';
            case '2xx': return '🐳';
            case '3xx': return '🎥';
            case '4xx': return '💻';
            case '5xx': return '⚙️';
            default: return '❌';
        }
    };

    const getErrorColor = (category) => {
        switch (category) {
            case '1xx': return '#e74c3c'; // Stream errors - red
            case '2xx': return '#f39c12'; // Docker errors - orange
            case '3xx': return '#9b59b6'; // Video errors - purple
            case '4xx': return '#3498db'; // Client errors - blue
            case '5xx': return '#e67e22'; // System errors - dark orange
            default: return '#95a5a6'; // Unknown - gray
        }
    };

    return (
        <div className="error-notification-overlay" onClick={onClose}>
            <div className="error-notification" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className="error-header" style={{ borderLeftColor: getErrorColor(error.error_category || '5xx') }}>
                    <div className="error-header-left">
                        <span className="error-icon">
                            {getErrorIcon(error.error_category || '5xx')}
                        </span>
                        <div className="error-title">
                            <h3>Error {error.error_code || 'Unknown'}</h3>
                            <p>{error.message || 'An error occurred'}</p>
                        </div>
                    </div>
                    <div className="error-header-right">
                        <button
                            className="error-expand-btn"
                            onClick={() => setIsExpanded(!isExpanded)}
                            title={isExpanded ? 'Collapse' : 'Expand'}
                        >
                            {isExpanded ? '−' : '+'}
                        </button>
                        <button
                            className="error-close-btn"
                            onClick={onClose}
                            title="Close"
                        >
                            ×
                        </button>
                    </div>
                </div>

                {/* Error Details */}
                {isExpanded && errorDetails && (
                    <div className="error-details">
                        {loading ? (
                            <div className="error-loading">
                                <div className="spinner"></div>
                                <p>Loading error details...</p>
                            </div>
                        ) : (
                            <>
                                {/* Error Meaning */}
                                <div className="error-section">
                                    <h4>📋 What This Means</h4>
                                    <p>{errorDetails.meaning}</p>
                                </div>

                                {/* Common Causes */}
                                <div className="error-section">
                                    <h4>🚨 Common Causes</h4>
                                    <ul>
                                        {errorDetails.common_causes?.map((cause, index) => (
                                            <li key={index}>{cause}</li>
                                        ))}
                                    </ul>
                                </div>

                                {/* Primary Solution */}
                                <div className="error-section">
                                    <h4>✅ Primary Solution</h4>
                                    <p className="primary-solution">{errorDetails.primary_solution}</p>
                                </div>

                                {/* Detailed Solutions */}
                                {errorDetails.detailed_solutions && errorDetails.detailed_solutions.length > 0 && (
                                    <div className="error-section">
                                        <h4>🔧 Detailed Solutions</h4>
                                        <ul>
                                            {errorDetails.detailed_solutions.map((solution, index) => (
                                                <li key={index}>{solution}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                {/* Troubleshooting Steps */}
                                {errorDetails.troubleshooting_steps && (
                                    <div className="error-section">
                                        <h4>🛠️ Troubleshooting Steps</h4>
                                        <div className="troubleshooting-grid">
                                            {Object.entries(errorDetails.troubleshooting_steps).map(([stepType, steps]) => (
                                                <div key={stepType} className="troubleshooting-group">
                                                    <h5>{stepType.split('_').map(word =>
                                                        word.charAt(0).toUpperCase() + word.slice(1)
                                                    ).join(' ')}</h5>
                                                    <ul>
                                                        {Array.isArray(steps) && steps.map((step, index) => (
                                                            <li key={index}>{step}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Context Information */}
                                {error.context && Object.keys(error.context).length > 0 && (
                                    <div className="error-section">
                                        <h4>🔍 Context Information</h4>
                                        <div className="context-grid">
                                            {Object.entries(error.context).map(([key, value]) => (
                                                <div key={key} className="context-item">
                                                    <strong>{key}:</strong> {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                )}

                {/* Action Buttons */}
                <div className="error-actions">
                    {onRetry && (
                        <button className="error-retry-btn" onClick={onRetry}>
                            🔄 Retry
                        </button>
                    )}
                    <button className="error-help-btn" onClick={() => window.open('/error_lookup.html', '_blank')}>
                        📚 Error Help
                    </button>
                    <button className="error-close-action-btn" onClick={onClose}>
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ErrorNotification;

import React, { useState } from 'react';
import useErrorHandler from './useErrorHandler';
import './ErrorTestPanel.css';

/**
 * Error Test Panel - Component for testing the error system
 * This allows developers and users to easily induce different types of errors
 */
const ErrorTestPanel = () => {
    const [testMode, setTestMode] = useState('manual');
    const [customErrorCode, setCustomErrorCode] = useState('143');
    const [customMessage, setCustomMessage] = useState('Custom error message');

    const {
        showError,
        showErrorByCode,
        showFFmpegError,
        showSRTError,
        showDockerError,
        showVideoError,
        showSimpleError,
        showToastError,
        handleValidationErrors,
        handleFileUploadError,
        handleStreamingError,
        handleNetworkError,
        handleAuthError
    } = useErrorHandler();

    // Test different error types
    const testErrorTypes = () => {
        return (
            <div className="error-test-section">
                <h3>🎯 Test Different Error Types</h3>

                <div className="test-buttons">
                    <button
                        onClick={() => showFFmpegError('process_failed', {
                            command: 'ffmpeg -i input.mp4 output.mp4',
                            group_id: 'test_group_123'
                        })}
                        className="test-btn ffmpeg"
                    >
                        🎬 FFmpeg Process Failed
                    </button>

                    <button
                        onClick={() => showSRTError('connection_timeout', {
                            srt_ip: '192.168.1.100',
                            srt_port: 9000,
                            timeout: 5,
                            group_id: 'test_group_123'
                        })}
                        className="test-btn srt"
                    >
                        📡 SRT Connection Timeout
                    </button>

                    <button
                        onClick={() => showDockerError('service_not_running', {
                            service_name: 'docker',
                            check_command: 'sudo systemctl status docker',
                            group_id: 'test_group_123'
                        })}
                        className="test-btn docker"
                    >
                        🐳 Docker Service Not Running
                    </button>

                    <button
                        onClick={() => showVideoError('file_not_found', {
                            file_path: '/path/to/video.mp4',
                            requested_by: 'streaming_component',
                            group_id: 'test_group_123'
                        })}
                        className="test-btn video"
                    >
                        🎥 Video File Not Found
                    </button>
                </div>
            </div>
        );
    };

    // Test error scenarios
    const testErrorScenarios = () => {
        return (
            <div className="error-test-section">
                <h3>🚨 Test Error Scenarios</h3>

                <div className="test-buttons">
                    <button
                        onClick={() => showSimpleError('This is a simple error message for testing')}
                        className="test-btn simple"
                    >
                        📝 Simple Error
                    </button>

                    <button
                        onClick={() => showToastError('This is a toast error that auto-hides in 3 seconds', 3000)}
                        className="test-btn toast"
                    >
                        🍞 Toast Error (3s)
                    </button>

                    <button
                        onClick={() => handleValidationErrors({
                            groupId: 'Group ID is required',
                            videoFiles: 'At least one video file is required',
                            resolution: 'Resolution must be 1920x1080 or higher'
                        })}
                        className="test-btn validation"
                    >
                        ✅ Validation Errors
                    </button>

                    <button
                        onClick={() => handleFileUploadError(new Error('File size exceeds 100MB limit'), {
                            file_name: 'large_video.mp4',
                            file_size: '150MB',
                            max_size: '100MB'
                        })}
                        className="test-btn file"
                    >
                        📁 File Upload Error
                    </button>

                    <button
                        onClick={() => handleStreamingError(new Error('SRT connection failed: Connection refused'), {
                            group_id: 'test_group_123',
                            operation: 'start_streaming',
                            timestamp: new Date().toISOString()
                        })}
                        className="test-btn streaming"
                    >
                        🎬 Streaming Error
                    </button>
                </div>
            </div>
        );
    };

    // Test network and API errors
    const testNetworkErrors = () => {
        return (
            <div className="error-test-section">
                <h3>🌐 Test Network & API Errors</h3>

                <div className="test-buttons">
                    <button
                        onClick={() => handleNetworkError(new Error('Request timeout after 30 seconds'), {
                            endpoint: '/api/streaming/start',
                            timeout: 30000
                        })}
                        className="test-btn network"
                    >
                        ⏱️ Network Timeout
                    </button>

                    <button
                        onClick={() => handleNetworkError(new Error('Failed to fetch: CORS policy violation'), {
                            endpoint: '/api/external',
                            origin: 'https://example.com'
                        })}
                        className="test-btn cors"
                    >
                        🚫 CORS Error
                    </button>

                    <button
                        onClick={() => handleAuthError(new Error('Authentication token expired'), {
                            user_id: 'user_123',
                            token_expiry: '2025-08-15T10:00:00Z'
                        })}
                        className="test-btn auth"
                    >
                        🔐 Auth Token Expired
                    </button>

                    <button
                        onClick={() => handleAuthError(new Error('Insufficient permissions for this operation'), {
                            user_id: 'user_123',
                            required_role: 'admin',
                            current_role: 'user'
                        })}
                        className="test-btn permission"
                    >
                        🚫 Permission Denied
                    </button>
                </div>
            </div>
        );
    };

    // Test custom error codes
    const testCustomErrors = () => {
        return (
            <div className="error-test-section">
                <h3>🔧 Test Custom Error Codes</h3>

                <div className="custom-error-form">
                    <div className="form-row">
                        <label htmlFor="errorCode">Error Code:</label>
                        <input
                            type="text"
                            id="errorCode"
                            value={customErrorCode}
                            onChange={(e) => setCustomErrorCode(e.target.value)}
                            placeholder="e.g., 143, 200, 340"
                        />
                    </div>

                    <div className="form-row">
                        <label htmlFor="errorMessage">Custom Message:</label>
                        <input
                            type="text"
                            id="errorMessage"
                            value={customMessage}
                            onChange={(e) => setCustomMessage(e.target.value)}
                            placeholder="Custom error message"
                        />
                    </div>

                    <button
                        onClick={() => showErrorByCode(parseInt(customErrorCode), {
                            custom_message: customMessage,
                            test_mode: true,
                            timestamp: new Date().toISOString()
                        })}
                        className="test-btn custom"
                    >
                        🎯 Show Custom Error
                    </button>
                </div>
            </div>
        );
    };

    // Test error with context
    const testErrorWithContext = () => {
        return (
            <div className="error-test-section">
                <h3>🔍 Test Error with Rich Context</h3>

                <div className="test-buttons">
                    <button
                        onClick={() => showError({
                            error_code: 143,
                            message: 'Group not found in Docker',
                            error_category: '1xx',
                            context: {
                                group_id: 'test_group_456',
                                operation: 'start_multi_video_stream',
                                user_id: 'user_789',
                                request_data: {
                                    video_count: 4,
                                    layout: '2x2',
                                    resolution: '1920x1080'
                                },
                                system_state: {
                                    docker_containers: 2,
                                    active_streams: 1,
                                    memory_usage: '75%',
                                    cpu_usage: '60%'
                                },
                                previous_errors: [
                                    { code: 200, time: '2025-08-15T09:30:00Z' },
                                    { code: 260, time: '2025-08-15T09:25:00Z' }
                                ],
                                troubleshooting_steps: [
                                    'Check if Docker container exists',
                                    'Verify group configuration',
                                    'Check Docker service status'
                                ]
                            }
                        })}
                        className="test-btn context"
                    >
                        📊 Rich Context Error
                    </button>

                    <button
                        onClick={() => showError({
                            error_code: 502,
                            message: 'System overload detected',
                            error_category: '5xx',
                            context: {
                                system_metrics: {
                                    cpu_usage: '95%',
                                    memory_usage: '88%',
                                    disk_usage: '92%',
                                    network_usage: '78%'
                                },
                                active_processes: 45,
                                recent_errors: [
                                    'FFmpeg process killed by OOM',
                                    'SRT connection timeout',
                                    'Docker container restart loop'
                                ],
                                recommendations: [
                                    'Reduce concurrent streams',
                                    'Increase system resources',
                                    'Check for memory leaks'
                                ]
                            }
                        })}
                        className="test-btn system"
                    >
                        ⚙️ System Overload Error
                    </button>
                </div>
            </div>
        );
    };

    // Test error recovery
    const testErrorRecovery = () => {
        return (
            <div className="error-test-section">
                <h3>🔄 Test Error Recovery</h3>

                <div className="test-buttons">
                    <button
                        onClick={() => {
                            // Show error first
                            showError({
                                error_code: 143,
                                message: 'Group not found in Docker - Click Retry to simulate recovery',
                                error_category: '1xx',
                                context: {
                                    group_id: 'test_group_789',
                                    retryFunction: () => {
                                        showToastError('✅ Recovery successful! Docker container created.', 3000);
                                    }
                                }
                            });
                        }}
                        className="test-btn recovery"
                    >
                        🔄 Error with Retry Function
                    </button>

                    <button
                        onClick={() => {
                            // Simulate multiple errors
                            showError({
                                error_code: 200,
                                message: 'Docker service not running',
                                error_category: '2xx',
                                context: {
                                    retryFunction: () => {
                                        showToastError('✅ Docker service started successfully!', 3000);
                                    }
                                }
                            });
                        }}
                        className="test-btn docker-recovery"
                    >
                        🐳 Docker Recovery Test
                    </button>
                </div>
            </div>
        );
    };

    return (
        <div className="error-test-panel">
            <div className="test-header">
                <h2>🧪 Error System Test Panel</h2>
                <p>Use this panel to test different error scenarios and see how the error system responds</p>
            </div>

            {/* Test Mode Selector */}
            <div className="test-mode-selector">
                <h3>🎛️ Test Mode</h3>
                <div className="mode-buttons">
                    <button
                        className={`mode-btn ${testMode === 'manual' ? 'active' : ''}`}
                        onClick={() => setTestMode('manual')}
                    >
                        Manual Testing
                    </button>
                    <button
                        className={`mode-btn ${testMode === 'automatic' ? 'active' : ''}`}
                        onClick={() => setTestMode('automatic')}
                    >
                        Automatic Testing
                    </button>
                </div>
            </div>

            {/* Test Sections */}
            {testErrorTypes()}
            {testErrorScenarios()}
            {testNetworkErrors()}
            {testCustomErrors()}
            {testErrorWithContext()}
            {testErrorRecovery()}

            {/* Test Results */}
            <div className="test-results">
                <h3>📊 Test Results</h3>
                <div className="results-info">
                    <p>✅ <strong>Error notifications</strong> should appear as popups when you click the test buttons</p>
                    <p>🔍 <strong>Click the expand button (+)</strong> to see detailed error information</p>
                    <p>🔄 <strong>Use the retry button</strong> to test error recovery scenarios</p>
                    <p>📚 <strong>Click the help button</strong> to open the error lookup system</p>
                </div>
            </div>

            {/* Quick Test All */}
            <div className="quick-test-all">
                <h3>🚀 Quick Test All Errors</h3>
                <button
                    onClick={() => {
                        // Test all error types in sequence
                        setTimeout(() => showFFmpegError('process_failed'), 0);
                        setTimeout(() => showSRTError('connection_timeout'), 1000);
                        setTimeout(() => showDockerError('service_not_running'), 2000);
                        setTimeout(() => showVideoError('file_not_found'), 3000);
                        setTimeout(() => showSimpleError('Final test error'), 4000);
                    }}
                    className="test-all-btn"
                >
                    🎯 Test All Error Types (Sequential)
                </button>
            </div>
        </div>
    );
};

export default ErrorTestPanel;

import React, { useState } from 'react';
import ErrorTestPanel from './ErrorTestPanel';
import './ErrorSystemTabs.css';

/**
 * Error System Tabs - Main component with tabbed interface for error system
 * Contains both the existing ErrorTestPanel and a new dedicated testing tab
 */
const ErrorSystemTabs = () => {
    const [activeTab, setActiveTab] = useState('testing');

    const tabs = [
        {
            id: 'testing',
            label: ' Error Testing',
            icon: '',
            description: 'Comprehensive error testing and simulation'
        },
        {
            id: 'examples',
            label: ' Examples',
            icon: '',
            description: 'Error system usage examples and demonstrations'
        },
        {
            id: 'documentation',
            label: ' Documentation',
            icon: '',
            description: 'Error codes, categories, and troubleshooting'
        }
    ];

    const renderTabContent = () => {
        switch (activeTab) {
            case 'testing':
                return <ErrorTestPanel />;
            case 'examples':
                return <ErrorExamplesTab />;
            case 'documentation':
                return <ErrorDocumentationTab />;
            default:
                return <ErrorTestPanel />;
        }
    };

    return (
        <div className="error-system-tabs">
            <div className="tabs-header">
                <h1> Error System Dashboard</h1>
                <p>Comprehensive error handling, testing, and documentation system</p>
            </div>

            <div className="tabs-navigation">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
                        onClick={() => setActiveTab(tab.id)}
                    >
                        <span className="tab-icon">{tab.icon}</span>
                        <span className="tab-label">{tab.label}</span>
                        <span className="tab-description">{tab.description}</span>
                    </button>
                ))}
            </div>

            <div className="tab-content">
                {renderTabContent()}
            </div>
        </div>
    );
};

// New dedicated testing tab component
const ErrorExamplesTab = () => {
    return (
        <div className="error-examples-tab">
            <div className="tab-header">
                <h2> Error System Examples</h2>
                <p>Learn how to use the error system in your components</p>
            </div>

            <div className="examples-grid">
                <div className="example-card">
                    <h3> Basic Error Handling</h3>
                    <p>Simple error display and toast notifications</p>
                    <div className="code-example">
                        <pre>{`import { useErrorHandler } from './useErrorHandler';

const { showSimpleError, showToastError } = useErrorHandler();

// Show simple error
showSimpleError('Something went wrong');

// Show toast error
showToastError('Operation failed', 3000);`}</pre>
                    </div>
                </div>

                <div className="example-card">
                    <h3> FFmpeg Error Handling</h3>
                    <p>Handle video processing errors with context</p>
                    <div className="code-example">
                        <pre>{`const { showFFmpegError } = useErrorHandler();

showFFmpegError('process_failed', {
    command: 'ffmpeg -i input.mp4 output.mp4',
    group_id: 'group_123',
    exit_code: 1
});`}</pre>
                    </div>
                </div>

                <div className="example-card">
                    <h3> SRT Error Handling</h3>
                    <p>Handle streaming protocol errors</p>
                    <div className="code-example">
                        <pre>{`const { showSRTError } = useErrorHandler();

showSRTError('connection_timeout', {
    srt_ip: '192.168.1.100',
    srt_port: 9000,
    timeout: 5
});`}</pre>
                    </div>
                </div>

                <div className="example-card">
                    <h3> Docker Error Handling</h3>
                    <p>Handle container and service errors</p>
                    <div className="code-example">
                        <pre>{`const { showDockerError } = useErrorHandler();

showDockerError('service_not_running', {
    service_name: 'docker',
    check_command: 'sudo systemctl status docker'
});`}</pre>
                    </div>
                </div>

                <div className="example-card">
                    <h3> Video Error Handling</h3>
                    <p>Handle video file and streaming errors</p>
                    <div className="code-example">
                        <pre>{`const { showVideoError } = useErrorHandler();

showVideoError('file_not_found', {
    file_path: '/path/to/video.mp4',
    requested_by: 'streaming_component'
});`}</pre>
                    </div>
                </div>

                <div className="example-card">
                    <h3> API Error Handling</h3>
                    <p>Handle network and API errors automatically</p>
                    <div className="code-example">
                        <pre>{`const { handleApiCall } = useErrorHandler();

try {
    const response = await handleApiCall(
        () => fetch('/api/endpoint'),
        { context: { operation: 'fetch_data' } }
    );
} catch (error) {
    // Error is automatically handled
}`}</pre>
                    </div>
                </div>
            </div>
        </div>
    );
};

// New documentation tab component
const ErrorDocumentationTab = () => {
    const errorCategories = [
        {
            category: '1xx - Information',
            description: 'General information and status messages',
            examples: [
                { code: 100, message: 'Continue', description: 'Request should continue' },
                { code: 101, message: 'Switching Protocols', description: 'Protocol switch requested' }
            ]
        },
        {
            category: '2xx - Success',
            description: 'Successful operations and responses',
            examples: [
                { code: 200, message: 'OK', description: 'Request succeeded' },
                { code: 201, message: 'Created', description: 'Resource created successfully' }
            ]
        },
        {
            category: '3xx - Redirection',
            description: 'Further action required',
            examples: [
                { code: 300, message: 'Multiple Choices', description: 'Multiple options available' },
                { code: 301, message: 'Moved Permanently', description: 'Resource moved permanently' }
            ]
        },
        {
            category: '4xx - Client Errors',
            description: 'Client-side errors and invalid requests',
            examples: [
                { code: 400, message: 'Bad Request', description: 'Invalid request syntax' },
                { code: 401, message: 'Unauthorized', description: 'Authentication required' },
                { code: 404, message: 'Not Found', description: 'Resource not found' }
            ]
        },
        {
            category: '5xx - Server Errors',
            description: 'Server-side errors and failures',
            examples: [
                { code: 500, message: 'Internal Server Error', description: 'Server encountered an error' },
                { code: 502, message: 'Bad Gateway', description: 'Invalid response from upstream' },
                { code: 503, message: 'Service Unavailable', description: 'Service temporarily unavailable' }
            ]
        }
    ];

    const customErrorCodes = [
        { code: 143, message: 'Group not found in Docker', category: 'Docker', solution: 'Check if Docker container exists and is running' },
        { code: 200, message: 'Docker service not running', category: 'Docker', solution: 'Start Docker service: sudo systemctl start docker' },
        { code: 260, message: 'SRT connection failed', category: 'Streaming', solution: 'Verify SRT server is running and accessible' },
        { code: 340, message: 'Video file not found', category: 'Video', solution: 'Check file path and permissions' },
        { code: 450, message: 'FFmpeg process failed', category: 'Video Processing', solution: 'Check FFmpeg installation and input files' }
    ];

    return (
        <div className="error-documentation-tab">
            <div className="tab-header">
                <h2> Error System Documentation</h2>
                <p>Comprehensive guide to error codes, categories, and troubleshooting</p>
            </div>

            <div className="documentation-sections">
                <div className="section">
                    <h3> Error Categories</h3>
                    <div className="categories-grid">
                        {errorCategories.map((cat, index) => (
                            <div key={index} className="category-card">
                                <h4>{cat.category}</h4>
                                <p>{cat.description}</p>
                                <div className="examples">
                                    {cat.examples.map((example, idx) => (
                                        <div key={idx} className="example-item">
                                            <span className="code">{example.code}</span>
                                            <span className="message">{example.message}</span>
                                            <span className="description">{example.description}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="section">
                    <h3> Custom Error Codes</h3>
                    <p>Application-specific error codes and their solutions</p>
                    <div className="custom-errors-table">
                        <table>
                            <thead>
                                <tr>
                                    <th>Code</th>
                                    <th>Message</th>
                                    <th>Category</th>
                                    <th>Solution</th>
                                </tr>
                            </thead>
                            <tbody>
                                {customErrorCodes.map((error, index) => (
                                    <tr key={index}>
                                        <td className="code">{error.code}</td>
                                        <td className="message">{error.message}</td>
                                        <td className="category">{error.category}</td>
                                        <td className="solution">{error.solution}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div className="section">
                    <h3> Troubleshooting Guide</h3>
                    <div className="troubleshooting-grid">
                        <div className="troubleshooting-card">
                            <h4> Docker Issues</h4>
                            <ul>
                                <li>Check Docker service status: <code>sudo systemctl status docker</code></li>
                                <li>Verify container exists: <code>docker ps -a</code></li>
                                <li>Check Docker logs: <code>docker logs [container_name]</code></li>
                                <li>Restart Docker service: <code>sudo systemctl restart docker</code></li>
                            </ul>
                        </div>

                        <div className="troubleshooting-card">
                            <h4> SRT Issues</h4>
                            <ul>
                                <li>Verify SRT server is running</li>
                                <li>Check firewall settings and port accessibility</li>
                                <li>Test connection: <code>nc -zv [ip] [port]</code></li>
                                <li>Check SRT logs for connection errors</li>
                            </ul>
                        </div>

                        <div className="troubleshooting-card">
                            <h4> FFmpeg Issues</h4>
                            <ul>
                                <li>Verify FFmpeg installation: <code>ffmpeg -version</code></li>
                                <li>Check input file format and codec support</li>
                                <li>Verify output directory permissions</li>
                                <li>Check system resources (CPU, memory)</li>
                            </ul>
                        </div>

                        <div className="troubleshooting-card">
                            <h4> Network Issues</h4>
                            <ul>
                                <li>Check network connectivity</li>
                                <li>Verify API endpoint accessibility</li>
                                <li>Check CORS configuration</li>
                                <li>Review network timeout settings</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ErrorSystemTabs;

import React, { useState, useEffect } from 'react';
import { useError } from './ErrorContext';

const ErrorNotification = () => {
    const { currentError, clearError } = useError();
    const [isExpanded, setIsExpanded] = useState(false);
    const [errorDetails, setErrorDetails] = useState(null);

    useEffect(() => {
        if (currentError && currentError.error_code) {
            generateErrorDetails(currentError);
        }
    }, [currentError]);

    const generateErrorDetails = (error) => {
        let details = {
            meaning: 'An unexpected error occurred in the system.',
            common_causes: ['System error', 'Configuration issue'],
            primary_solution: 'Check system logs and try again.',
            detailed_solutions: ['Restart the service', 'Verify configuration']
        };

        // Check if we have enhanced error information from the context
        if (error.common_causes && error.what_this_means && error.primary_solution) {
            details = {
                meaning: error.what_this_means,
                common_causes: error.common_causes,
                primary_solution: error.primary_solution,
                detailed_solutions: error.troubleshooting_steps || []
            };
        } else if (error.context && error.context.server_response) {
            const serverResponse = error.context.server_response;
            if (serverResponse.error) { details.message = serverResponse.error; }
            if (serverResponse.details) { details.meaning = serverResponse.details; }
            if (serverResponse.validation_errors) {
                details.common_causes = Object.values(serverResponse.validation_errors);
                details.primary_solution = 'Fix the validation errors above and try again';
                details.detailed_solutions = [
                    'Check all required fields are filled',
                    'Verify data types and formats',
                    'Ensure values meet validation rules',
                    'Check request body structure'
                ];
            }
        } else if (error.error_code) {
            const errorCode = error.error_code.toString();
            if (errorCode.startsWith('HTTP_4')) {
                if (errorCode === 'HTTP_400') {
                    details.meaning = 'Bad Request: The server could not understand the request due to invalid syntax or missing data.';
                    details.common_causes = ['Missing required fields', 'Invalid data format', 'Validation rule violations', 'Malformed request body'];
                    details.primary_solution = 'Fix the request data and try again.';
                    details.detailed_solutions = ['Check all required fields are filled', 'Verify data types and formats', 'Ensure values meet validation rules', 'Check request body structure'];
                } else {
                    details.meaning = 'Client Error: The request cannot be completed due to client-side issues.';
                    details.common_causes = ['Invalid request format', 'Missing authentication', 'Insufficient permissions', 'Resource not found'];
                    details.primary_solution = 'Check your request and try again.';
                    details.detailed_solutions = ['Verify request format', 'Check authentication', 'Confirm permissions', 'Verify resource exists'];
                }
            } else if (errorCode.startsWith('HTTP_5')) {
                details.meaning = 'Server Error: The server encountered an error while processing your request.';
                details.common_causes = ['Server overload', 'Database connection issues', 'External service failures', 'Configuration problems'];
                details.primary_solution = 'Please try again later or contact support.';
                details.detailed_solutions = ['Wait a few minutes and retry', 'Check server status', 'Contact system administrator', 'Verify external services'];
            } else if (errorCode === 'VALIDATION_ERROR') {
                details.meaning = 'Validation Error: The provided data does not meet the required format or rules.';
                details.common_causes = ['Missing required fields', 'Invalid data types', 'Value out of range', 'Format violations'];
                details.primary_solution = 'Review and fix the data according to the validation rules.';
                details.detailed_solutions = ['Fill all required fields', 'Use correct data types', 'Ensure values are within limits', 'Follow the specified format'];
            } else if (errorCode === 'NETWORK_ERROR' || errorCode === 'SERVER_UNREACHABLE') {
                details.meaning = 'Network Error: Unable to connect to the server or service.';
                details.common_causes = ['Server is down', 'Network connectivity issues', 'Firewall blocking', 'Incorrect server address'];
                details.primary_solution = 'Check your network connection and server status.';
                details.detailed_solutions = ['Verify internet connection', 'Check server status', 'Review firewall settings', 'Confirm server address'];
            } else if (errorCode === 'GROUP_CREATION_FAILED' || error.message?.includes('Missing group name')) {
                details.meaning = 'Failed to create a new group because the group name is missing or invalid.';
                details.common_causes = ['Group name field is empty', 'Group name contains only whitespace', 'Group name is too short', 'Group name contains invalid characters'];
                details.primary_solution = 'Enter a valid group name and try again.';
                details.detailed_solutions = ['Fill in the group name field', 'Use 3-50 characters for the name', 'Avoid special characters except hyphens and underscores', 'Ensure the name is descriptive and unique'];
            } else if (errorCode === 'FILE_UPLOAD_FAILED') {
                details.meaning = 'File Upload Error: The file could not be uploaded to the server.';
                details.common_causes = ['File too large', 'Invalid file type', 'Server storage full', 'Network interruption'];
                details.primary_solution = 'Check file size and type, then try again.';
                details.detailed_solutions = ['Reduce file size if too large', 'Use supported file formats', 'Check server storage space', 'Ensure stable network connection'];
            }
        }
        setErrorDetails(details);
    };

    const getErrorIcon = (category) => {
        const icons = {
            '1xx': '',
            '2xx': '',
            '3xx': '',
            '4xx': '',
            '5xx': '',
            'ffmpeg': '',
            'srt': '',
            'docker': '',
            'video': '',
            'network': '',
            'validation': '',
            'auth': '',
            'custom': ''
        };
        return icons[category] || '';
    };

    const getErrorColor = (category) => {
        const colors = {
            '1xx': 'border-blue-500 bg-blue-50',
            '2xx': 'border-green-500 bg-green-50',
            '3xx': 'border-yellow-500 bg-yellow-50',
            '4xx': 'border-orange-500 bg-orange-50',
            '5xx': 'border-red-500 bg-red-50',
            'ffmpeg': 'border-purple-500 bg-purple-50',
            'srt': 'border-blue-500 bg-blue-50',
            'docker': 'border-cyan-500 bg-cyan-50',
            'video': 'border-pink-500 bg-pink-50',
            'network': 'border-gray-500 bg-gray-50',
            'validation': 'border-yellow-500 bg-yellow-50',
            'auth': 'border-red-500 bg-red-50',
            'custom': 'border-indigo-500 bg-indigo-50'
        };
        return colors[category] || 'border-red-500 bg-red-50';
    };

    const getErrorVariant = (category) => {
        const variants = {
            '1xx': 'default',
            '2xx': 'default',
            '3xx': 'secondary',
            '4xx': 'destructive',
            '5xx': 'destructive',
            'ffmpeg': 'destructive',
            'srt': 'destructive',
            'docker': 'destructive',
            'video': 'destructive',
            'network': 'destructive',
            'validation': 'destructive',
            'auth': 'destructive',
            'custom': 'destructive'
        };
        return variants[category] || 'destructive';
    };

    if (!currentError) return null;

    // Toast-like popup (collapsed state)
    if (!isExpanded) {
        return (
            <div className="fixed bottom-4 right-4 z-50 max-w-sm">
                <div
                    className={`${getErrorColor(currentError.error_category || '5xx')} border rounded-lg shadow-lg p-3 cursor-pointer hover:shadow-xl transition-all duration-200 transform hover:scale-105`}
                    onClick={() => setIsExpanded(true)}
                >
                    <div className="flex items-start space-x-2">
                        <span className="text-lg flex-shrink-0">
                            {getErrorIcon(currentError.error_category || '5xx')}
                        </span>
                        <div className="flex-1 min-w-0">
                            <h3 className="text-sm font-semibold text-gray-900 truncate">
                                Error {currentError.error_code || 'Unknown'}
                            </h3>
                            <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                                {currentError.message || 'An error occurred'}
                            </p>
                            <p className="text-xs text-gray-500 mt-1 italic">
                                Click for details
                            </p>
                        </div>
                        <button
                            className="text-gray-400 hover:text-gray-600 transition-colors p-1 rounded hover:bg-gray-100"
                            onClick={(e) => {
                                e.stopPropagation();
                                clearError();
                            }}
                        >

                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // Expanded detailed view
    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-2 z-50">
            <div className="bg-white rounded-xl border shadow-lg max-w-2xl w-full max-h-[90vh] flex flex-col mx-4 overflow-hidden" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className={`border-l-4 ${getErrorColor(currentError.error_category || '5xx')} p-4 flex-shrink-0 rounded-t-xl`}>
                    <div className="flex items-start justify-between">
                        <div className="flex items-start space-x-2">
                            <span className="text-xl">
                                {getErrorIcon(currentError.error_category || '5xx')}
                            </span>
                            <div className="flex-1 min-w-0">
                                <h3 className="text-lg font-semibold leading-tight tracking-tight">
                                    Error {currentError.error_code || 'Unknown'}
                                </h3>
                                <p className="text-sm mt-1 text-gray-600 break-words">{currentError.message || 'An error occurred'}</p>
                            </div>
                        </div>
                        <div className="flex items-center space-x-2 flex-shrink-0">
                            <button
                                className="inline-flex items-center justify-center gap-1 whitespace-nowrap rounded text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 h-8 px-3 bg-secondary text-secondary-foreground hover:bg-secondary/80"
                                onClick={() => setIsExpanded(false)}
                            >
                                Collapse
                            </button>
                            <button
                                className="inline-flex items-center justify-center gap-1 whitespace-nowrap rounded text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 h-8 w-8 rounded border border-input bg-background hover:bg-accent hover:text-accent-foreground"
                                onClick={clearError}
                            >

                            </button>
                        </div>
                    </div>
                </div>

                {/* Content */}
                <div className="p-4 pt-0 flex-1 overflow-y-auto">
                    {/* Basic Error Info */}
                    <div className="space-y-3">
                        {currentError.context && (
                            <div className="space-y-3">
                                <h4 className="text-sm font-medium text-gray-900">Context</h4>
                                <div className="bg-gray-50 rounded-lg p-3 text-sm">
                                    <div className="space-y-2">
                                        {currentError.context.component && (
                                            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                                                <span className="font-medium text-gray-600">Component:</span>
                                                <span className="text-gray-900 break-words">{currentError.context.component}</span>
                                            </div>
                                        )}
                                        {currentError.context.operation && (
                                            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                                                <span className="font-medium text-gray-600">Operation:</span>
                                                <span className="text-gray-900 break-words">{currentError.context.operation}</span>
                                            </div>
                                        )}
                                        {currentError.context.server_status && (
                                            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                                                <span className="font-medium text-gray-600">HTTP Status:</span>
                                                <span className="text-gray-900">{currentError.context.server_status}</span>
                                            </div>
                                        )}
                                        {currentError.context.api_base_url && (
                                            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                                                <span className="font-medium text-gray-600">API URL:</span>
                                                <span className="text-gray-900 break-all text-xs">{currentError.context.api_base_url}</span>
                                            </div>
                                        )}
                                        {currentError.context.timestamp && (
                                            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                                                <span className="font-medium text-gray-600">Timestamp:</span>
                                                <span className="text-gray-900">{new Date(currentError.context.timestamp).toLocaleString()}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Server Response Details */}
                        {currentError.context && currentError.context.server_response && (
                            <div className="space-y-3">
                                <h4 className="text-sm font-medium text-gray-900">Server Response</h4>
                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm">
                                    <div className="space-y-2">
                                        {currentError.context.server_response.error && (
                                            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                                                <span className="font-medium text-blue-700">Error:</span>
                                                <span className="text-blue-900 break-words">{currentError.context.server_response.error}</span>
                                            </div>
                                        )}
                                        {currentError.context.server_response.message && (
                                            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                                                <span className="font-medium text-blue-700">Message:</span>
                                                <span className="text-blue-900 break-words">{currentError.context.server_response.message}</span>
                                            </div>
                                        )}
                                        {currentError.context.server_response.details && (
                                            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                                                <span className="font-medium text-blue-700">Details:</span>
                                                <span className="text-blue-900 break-words">{currentError.context.server_response.details}</span>
                                            </div>
                                        )}
                                        {currentError.context.server_response.validation_errors && (
                                            <div>
                                                <span className="font-medium text-blue-700">Validation Errors:</span>
                                                <div className="mt-1 space-y-1">
                                                    {Object.entries(currentError.context.server_response.validation_errors).map(([field, message]) => (
                                                        <div key={field} className="text-blue-700 text-xs">
                                                            <span className="font-medium">{field}:</span> {message}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Error Details */}
                        {errorDetails && (
                            <div className="space-y-3 border-t pt-3">
                                {/* Error Meaning */}
                                {errorDetails.meaning && (
                                    <div>
                                        <h4 className="text-sm font-medium text-gray-900 mb-2">What This Means</h4>
                                        <p className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 leading-relaxed break-words">{errorDetails.meaning}</p>
                                    </div>
                                )}

                                {/* Common Causes */}
                                {errorDetails.common_causes && errorDetails.common_causes.length > 0 && (
                                    <div>
                                        <h4 className="text-sm font-medium text-gray-900 mb-2">Common Causes</h4>
                                        <ul className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 space-y-2">
                                            {errorDetails.common_causes.map((cause, index) => (
                                                <li key={index} className="flex items-start">
                                                    <span className="text-red-500 mr-2 text-sm flex-shrink-0"></span>
                                                    <span className="text-sm break-words">{cause}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                {/* Primary Solution */}
                                {errorDetails.primary_solution && (
                                    <div>
                                        <h4 className="text-sm font-medium text-gray-900 mb-2">Primary Solution</h4>
                                        <p className="text-sm text-gray-600 bg-blue-50 rounded-lg p-3 border border-blue-200 leading-relaxed break-words">{errorDetails.primary_solution}</p>
                                    </div>
                                )}

                                {/* Detailed Solutions */}
                                {errorDetails.detailed_solutions && errorDetails.detailed_solutions.length > 0 && (
                                    <div>
                                        <h4 className="text-sm font-medium text-gray-900 mb-2">Detailed Solutions</h4>
                                        <ul className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 space-y-2">
                                            {errorDetails.detailed_solutions.map((solution, index) => (
                                                <li key={index} className="flex items-start">
                                                    <span className="text-blue-500 mr-2 text-sm flex-shrink-0"></span>
                                                    <span className="text-sm break-words">{solution}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between p-4 pt-0 border-t flex-shrink-0 rounded-b-xl">
                    <div className="text-sm text-gray-500">
                        Error ID: {currentError.id || 'N/A'}
                    </div>
                    <div className="flex items-center space-x-3">
                        <button
                            className="inline-flex items-center justify-center gap-1 whitespace-nowrap rounded text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 h-8 px-4 bg-secondary text-secondary-foreground hover:bg-secondary/80"
                            onClick={() => setIsExpanded(false)}
                        >
                            Back to Toast
                        </button>
                        <button
                            className="inline-flex items-center justify-center gap-1 whitespace-nowrap rounded text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 h-8 px-4 bg-primary text-primary-foreground hover:bg-primary/90"
                            onClick={clearError}
                        >
                            Dismiss
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ErrorNotification;

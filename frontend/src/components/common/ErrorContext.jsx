import React, { createContext, useContext, useState, useCallback } from 'react';

const ErrorContext = createContext();

export const useError = () => {
  const context = useContext(ErrorContext);
  if (!context) {
    throw new Error('useError must be used within an ErrorProvider');
  }
  return context;
};

export const ErrorProvider = ({ children }) => {
  const [currentError, setCurrentError] = useState(null);
  const [errorHistory, setErrorHistory] = useState([]);

  // Show error with automatic error code detection
  const showError = useCallback((error, options = {}) => {
    let processedError = error;

    // If it's a string, convert to error object
    if (typeof error === 'string') {
      processedError = {
        message: error,
        error_code: null,
        error_category: '5xx',
        context: {}
      };
    }

    // If it's an API response with error structure, use it
    if (error && error.error_code) {
      processedError = error;
    }

    // If it's a standard HTTP error, try to extract error code
    if (error && error.status) {
      const statusError = mapHttpStatusToError(error.status, error);
      processedError = statusError;
    }

    // Add timestamp and context
    const finalError = {
      ...processedError,
      timestamp: new Date().toISOString(),
      id: Date.now(),
      context: {
        ...processedError.context,
        userAgent: navigator.userAgent,
        url: window.location.href,
        timestamp: new Date().toISOString()
      }
    };

    // Add to history
    setErrorHistory(prev => [...prev.slice(-9), finalError]); // Keep last 10 errors

    // Set as current error
    setCurrentError(finalError);

    // Auto-hide after specified time (default: never for manual errors)
    if (options.autoHide) {
      setTimeout(() => {
        hideError();
      }, options.autoHide);
    }

    // Log error to console
    console.error('Error displayed:', finalError);

    return finalError;
  }, []);

  // Show specific error by code
  const showErrorByCode = useCallback((errorCode, context = {}) => {
    // Get detailed error information from application error mapping
    const appError = getApplicationErrorCode(errorCode);
    
    const error = {
      error_code: errorCode,
      message: appError.message,
      error_category: appError.error_category,
      common_causes: appError.common_causes,
      what_this_means: appError.what_this_means,
      primary_solution: appError.primary_solution,
      troubleshooting_steps: appError.troubleshooting_steps,
      context: {
        ...context,
        error_type: 'application_error'
      }
    };
    
    showError(error);
  }, [showError]);

  // Show FFmpeg-specific error
  const showFFmpegError = useCallback((errorType, context = {}) => {
    const error = {
      error_code: getFFmpegErrorCode(errorType),
      message: `FFmpeg ${errorType.replace('_', ' ')}`,
      error_category: '1xx',
      context: {
        ...context,
        error_type: errorType,
        component: 'ffmpeg'
      }
    };
    
    showError(error);
  }, [showError]);

  // Show SRT-specific error
  const showSRTError = useCallback((errorType, context = {}) => {
    const error = {
      error_code: getSRTErrorCode(errorType),
      message: `SRT ${errorType.replace('_', ' ')}`,
      error_category: '1xx',
      context: {
        ...context,
        error_type: errorType,
        component: 'srt'
      }
    };
    
    showError(error);
  }, [showError]);

  // Show Docker-specific error
  const showDockerError = useCallback((errorType, context = {}) => {
    const error = {
      error_code: getDockerErrorCode(errorType),
      message: `Docker ${errorType.replace('_', ' ')}`,
      error_category: '2xx',
      context: {
        ...context,
        error_type: errorType,
        component: 'docker'
      }
    };
    
    showError(error);
  }, [showError]);

  // Show video-specific error
  const showVideoError = useCallback((errorType, context = {}) => {
    const error = {
      error_code: getVideoErrorCode(errorType),
      message: `Video ${errorType.replace('_', ' ')}`,
      error_category: '3xx',
      context: {
        ...context,
        error_type: errorType,
        component: 'video'
      }
    };
    
    showError(error);
  }, [showError]);

  // Hide current error
  const hideError = useCallback(() => {
    setCurrentError(null);
  }, []);

  // Clear current error (alias for hideError for consistency)
  const clearError = useCallback(() => {
    setCurrentError(null);
  }, []);

  // Clear error history
  const clearErrorHistory = useCallback(() => {
    setErrorHistory([]);
  }, []);

  // Retry last operation (placeholder - implement based on your needs)
  const retryLastOperation = useCallback(() => {
    if (currentError && currentError.context.retryFunction) {
      try {
        currentError.context.retryFunction();
        hideError();
      } catch (error) {
        showError(`Retry failed: ${error.message}`);
      }
    } else {
      // Default retry behavior
      hideError();
      // You could implement a global retry mechanism here
    }
  }, [currentError, hideError, showError]);

  // Handle API errors automatically
  const handleApiError = useCallback((response, context = {}) => {
    if (!response.ok) {
      let errorData = {};
      
      try {
        // Try to parse error response
        const responseText = response.text();
        if (responseText) {
          errorData = JSON.parse(responseText);
        }
      } catch (e) {
        // If parsing fails, use status text
        errorData = { message: response.statusText };
      }

      const error = {
        error_code: response.status,
        message: errorData.message || `HTTP ${response.status}: ${response.statusText}`,
        error_category: getCategoryFromHttpStatus(response.status),
        context: {
          ...context,
          http_status: response.status,
          http_status_text: response.statusText,
          url: response.url,
          method: context.method || 'GET'
        }
      };

      showError(error);
      return error;
    }
    
    return null;
  }, [showError]);

  // Handle fetch errors
  const handleFetchError = useCallback((error, context = {}) => {
    const processedError = {
      message: error.message || 'Network error occurred',
      error_code: 'NETWORK_ERROR',
      error_category: '5xx',
      context: {
        ...context,
        error_type: 'network',
        original_error: error.toString()
      }
    };

    showError(processedError);
    return processedError;
  }, [showError]);

  // Handle promise rejections
  const handlePromiseRejection = useCallback((error, context = {}) => {
    const processedError = {
      message: error.message || 'Promise rejection occurred',
      error_code: 'PROMISE_REJECTION',
      error_category: '5xx',
      context: {
        ...context,
        error_type: 'promise_rejection',
        original_error: error.toString()
      }
    };

    showError(processedError);
    return processedError;
  }, [showError]);

  const value = {
    currentError,
    errorHistory,
    showError,
    showErrorByCode,
    showFFmpegError,
    showSRTError,
    showDockerError,
    showVideoError,
    hideError,
    clearError,
    clearErrorHistory,
    retryLastOperation,
    handleApiError,
    handleFetchError,
    handlePromiseRejection
  };

  return (
    <ErrorContext.Provider value={value}>
      {children}
    </ErrorContext.Provider>
  );
};

// Helper functions
const getCategoryFromCode = (errorCode) => {
  if (typeof errorCode === 'string') return '5xx';
  
  const code = parseInt(errorCode);
  if (code >= 100 && code < 200) return '1xx';
  if (code >= 200 && code < 300) return '2xx';
  if (code >= 300 && code < 400) return '3xx';
  if (code >= 400 && code < 500) return '4xx';
  if (code >= 500 && code < 600) return '5xx';
  return '5xx';
};

const getCategoryFromHttpStatus = (status) => {
  if (status >= 100 && status < 200) return '1xx';
  if (status >= 200 && status < 300) return '2xx';
  if (status >= 300 && status < 400) return '3xx';
  if (status >= 400 && status < 500) return '4xx';
  if (status >= 500 && status < 600) return '5xx';
  return '5xx';
};

const getFFmpegErrorCode = (errorType) => {
  const mapping = {
    'process_failed': 100,
    'process_terminated': 101,
    'startup_timeout': 102,
    'invalid_params': 103,
    'input_not_found': 104,
    'output_error': 105,
    'encoding_error': 106,
    'too_many_errors': 107,
    'critical_error': 108,
    'resources_exhausted': 109
  };
  return mapping[errorType] || 100;
};

const getSRTErrorCode = (errorType) => {
  const mapping = {
    'connection_refused': 120,
    'connection_timeout': 121,
    'connection_reset': 122,
    'broken_pipe': 123,
    'no_route': 124,
    'port_in_use': 125,
    'socket_error': 126,
    'handshake_failure': 127,
    'auth_error': 128,
    'stream_not_found': 129
  };
  return mapping[errorType] || 120;
};

const getDockerErrorCode = (errorType) => {
  const mapping = {
    'service_not_running': 200,
    'connection_failed': 201,
    'permission_denied': 202,
    'operation_timeout': 203,
    'version_incompatible': 204,
    'resources_exhausted': 205,
    'network_error': 206,
    'storage_error': 207,
    'service_unavailable': 208,
    'api_error': 209
  };
  return mapping[errorType] || 200;
};

const getVideoErrorCode = (errorType) => {
  const mapping = {
    'file_not_found': 180,
    'file_corrupted': 181,
    'format_not_supported': 182,
    'codec_not_supported': 183,
    'resolution_invalid': 184,
    'duration_invalid': 185,
    'permission_denied': 186,
    'insufficient_disk_space': 187,
    'processing_failed': 188,
    'metadata_extraction_failed': 189
  };
  return mapping[errorType] || 180;
};

const mapHttpStatusToError = (status, originalError) => {
  const statusMessages = {
    400: 'Bad Request - Invalid parameters provided',
    401: 'Unauthorized - Authentication required',
    403: 'Forbidden - Access denied',
    404: 'Not Found - Resource not available',
    405: 'Method Not Allowed - HTTP method not supported',
    408: 'Request Timeout - Operation took too long',
    409: 'Conflict - Resource conflict detected',
    422: 'Unprocessable Entity - Validation failed',
    429: 'Too Many Requests - Rate limit exceeded',
    500: 'Internal Server Error - Server encountered an error',
    502: 'Bad Gateway - Upstream service error',
    503: 'Service Unavailable - Service temporarily unavailable',
    504: 'Gateway Timeout - Upstream service timeout'
  };

  return {
    error_code: status,
    message: statusMessages[status] || `HTTP ${status} Error`,
    error_category: getCategoryFromHttpStatus(status),
    context: {
      http_status: status,
      original_error: originalError
    }
  };
};

// Add specific error code mappings for common application errors
const getApplicationErrorCode = (errorCode) => {
  const mapping = {
    'DATA_LOAD_FAILED': {
      message: 'Failed to load application data',
      error_category: '5xx',
      common_causes: [
        'Backend server is not running',
        'Network connectivity issues',
        'Database connection problems',
        'API endpoint unavailable',
        'Authentication/authorization failures'
      ],
      what_this_means: 'The application cannot retrieve the necessary data to function properly. This typically indicates a backend service issue or network problem.',
      primary_solution: 'Check if the backend server is running and accessible. Verify network connectivity and ensure all required services are operational.',
      troubleshooting_steps: [
        'Verify backend server is running',
        'Check network connectivity',
        'Review server logs for errors',
        'Ensure database is accessible',
        'Verify API endpoints are working'
      ]
    },
    'DATA_REFRESH_FAILED': {
      message: 'Failed to refresh application data',
      error_category: '5xx',
      common_causes: [
        'Backend server temporarily unavailable',
        'Network timeout',
        'Rate limiting',
        'Service overload'
      ],
      what_this_means: 'The application cannot update its current data. This may be a temporary issue that resolves itself.',
      primary_solution: 'Wait a moment and try refreshing again. If the problem persists, check backend server status.',
      troubleshooting_steps: [
        'Wait and retry the operation',
        'Check backend server status',
        'Verify network connectivity',
        'Check for rate limiting'
      ]
    }
  };
  
  return mapping[errorCode] || {
    message: `Error ${errorCode} occurred`,
    error_category: '5xx',
    common_causes: ['Unknown error'],
    what_this_means: 'An unexpected error occurred.',
    primary_solution: 'Check the application logs for more details.',
    troubleshooting_steps: ['Review error logs', 'Contact support']
  };
};

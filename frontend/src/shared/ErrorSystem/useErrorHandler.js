import { useCallback } from 'react';
import { useError } from './ErrorContext';

/**
 * Custom hook for easy error handling in React components
 * Provides simplified methods for common error scenarios
 */
export const useErrorHandler = () => {
  const {
    showError,
    showErrorByCode,
    showFFmpegError,
    showSRTError,
    showDockerError,
    showVideoError,
    handleApiError,
    handleFetchError,
    handlePromiseRejection
  } = useError();

  /**
   * Handle API calls with automatic error handling
   * @param {Function} apiCall - The API function to call
   * @param {Object} options - Options for error handling
   * @returns {Promise} - Promise that resolves with result or rejects with handled error
   */
  const handleApiCall = useCallback(async (apiCall, options = {}) => {
    try {
      const response = await apiCall();
      
      // Check if response is ok
      if (response && response.ok !== undefined && !response.ok) {
        const error = handleApiError(response, options.context);
        if (options.throwOnError) {
          throw error;
        }
        return null;
      }
      
      return response;
    } catch (error) {
      const processedError = handleFetchError(error, options.context);
      if (options.throwOnError) {
        throw processedError;
      }
      return null;
    }
  }, [handleApiError, handleFetchError]);

  /**
   * Handle fetch calls with automatic error handling
   * @param {string} url - URL to fetch
   * @param {Object} options - Fetch options
   * @param {Object} errorOptions - Error handling options
   * @returns {Promise} - Promise that resolves with result or rejects with handled error
   */
  const handleFetch = useCallback(async (url, options = {}, errorOptions = {}) => {
    try {
      const response = await fetch(url, options);
      
      if (!response.ok) {
        const error = handleApiError(response, {
          ...errorOptions.context,
          url,
          method: options.method || 'GET'
        });
        
        if (errorOptions.throwOnError) {
          throw error;
        }
        return null;
      }
      
      return response;
    } catch (error) {
      const processedError = handleFetchError(error, {
        ...errorOptions.context,
        url,
        method: options.method || 'GET'
      });
      
      if (errorOptions.throwOnError) {
        throw processedError;
      }
      return null;
    }
  }, [handleApiError, handleFetchError]);

  /**
   * Handle async operations with automatic error handling
   * @param {Function} operation - The async operation to perform
   * @param {Object} options - Error handling options
   * @returns {Promise} - Promise that resolves with result or rejects with handled error
   */
  const handleAsyncOperation = useCallback(async (operation, options = {}) => {
    try {
      const result = await operation();
      return result;
    } catch (error) {
      const processedError = handlePromiseRejection(error, options.context);
      
      if (options.throwOnError) {
        throw processedError;
      }
      return null;
    }
  }, [handlePromiseRejection]);

  /**
   * Show a simple error message
   * @param {string} message - Error message to display
   * @param {Object} options - Display options
   */
  const showSimpleError = useCallback((message, options = {}) => {
    showError(message, options);
  }, [showError]);

  /**
   * Show a toast-style error (auto-hiding)
   * @param {string} message - Error message to display
   * @param {number} duration - Duration in milliseconds (default: 5000)
   */
  const showToastError = useCallback((message, duration = 5000) => {
    showError(message, { autoHide: duration });
  }, [showError]);

  /**
   * Handle form validation errors
   * @param {Object} errors - Validation errors object
   * @param {Object} options - Display options
   */
  const handleValidationErrors = useCallback((errors, options = {}) => {
    if (typeof errors === 'object' && errors !== null) {
      const errorMessages = Object.values(errors).flat();
      const message = errorMessages.join(', ');
      showError(message, options);
    } else if (typeof errors === 'string') {
      showError(errors, options);
    }
  }, [showError]);

  /**
   * Handle file upload errors
   * @param {Error} error - File upload error
   * @param {Object} context - Additional context
   */
  const handleFileUploadError = useCallback((error, context = {}) => {
    let errorType = 'processing_failed';
    
    if (error.message.includes('size')) {
      errorType = 'exceeds_size_limit';
    } else if (error.message.includes('format') || error.message.includes('type')) {
      errorType = 'format_not_supported';
    } else if (error.message.includes('permission')) {
      errorType = 'permission_denied';
    } else if (error.message.includes('network') || error.message.includes('fetch')) {
      errorType = 'upload_timeout';
    }
    
    showVideoError(errorType, {
      ...context,
      original_error: error.message
    });
  }, [showVideoError]);

  /**
   * Handle streaming errors
   * @param {Error} error - Streaming error
   * @param {Object} context - Additional context
   */
  const handleStreamingError = useCallback((error, context = {}) => {
    let errorType = 'process_failed';
    
    if (error.message.includes('SRT') || error.message.includes('connection')) {
      errorType = 'connection_timeout';
    } else if (error.message.includes('FFmpeg') || error.message.includes('process')) {
      errorType = 'process_failed';
    } else if (error.message.includes('Docker') || error.message.includes('container')) {
      errorType = 'service_not_running';
    } else if (error.message.includes('video') || error.message.includes('file')) {
      errorType = 'file_not_found';
    }
    
    // Determine which error type to show based on the error
    if (errorType === 'connection_timeout') {
      showSRTError(errorType, context);
    } else if (errorType === 'process_failed') {
      showFFmpegError(errorType, context);
    } else if (errorType === 'service_not_running') {
      showDockerError(errorType, context);
    } else if (errorType === 'file_not_found') {
      showVideoError(errorType, context);
    } else {
      showError(error.message, { context });
    }
  }, [showSRTError, showFFmpegError, showDockerError, showVideoError, showError]);

  /**
   * Handle network errors
   * @param {Error} error - Network error
   * @param {Object} context - Additional context
   */
  const handleNetworkError = useCallback((error, context = {}) => {
    let message = 'Network error occurred';
    
    if (error.message.includes('timeout')) {
      message = 'Request timed out - please check your connection';
    } else if (error.message.includes('fetch')) {
      message = 'Failed to connect to server - please check your internet connection';
    } else if (error.message.includes('CORS')) {
      message = 'Cross-origin request blocked - please contact support';
    }
    
    showError(message, {
      context: {
        ...context,
        error_type: 'network',
        original_error: error.message
      }
    });
  }, [showError]);

  /**
   * Handle authentication errors
   * @param {Error} error - Authentication error
   * @param {Object} context - Additional context
   */
  const handleAuthError = useCallback((error, context = {}) => {
    let message = 'Authentication failed';
    
    if (error.message.includes('token') || error.message.includes('expired')) {
      message = 'Your session has expired - please log in again';
    } else if (error.message.includes('permission') || error.message.includes('access')) {
      message = 'Access denied - insufficient permissions';
    } else if (error.message.includes('credentials')) {
      message = 'Invalid credentials - please check your username and password';
    }
    
    showError(message, {
      context: {
        ...context,
        error_type: 'authentication',
        original_error: error.message
      }
    });
  }, [showError]);

  return {
    // Core error handling
    showError,
    showErrorByCode,
    showFFmpegError,
    showSRTError,
    showDockerError,
    showVideoError,
    
    // Simplified error handling
    showSimpleError,
    showToastError,
    handleValidationErrors,
    handleFileUploadError,
    handleStreamingError,
    handleNetworkError,
    handleAuthError,
    
    // API and operation handling
    handleApiCall,
    handleFetch,
    handleAsyncOperation,
    handleApiError,
    handleFetchError,
    handlePromiseRejection
  };
};

export default useErrorHandler;

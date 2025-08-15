import React, { useState } from 'react';
import useErrorHandler from './useErrorHandler';
import './ErrorSystemExample.css';

/**
 * Example component demonstrating how to use the error system
 * This shows various ways to integrate error handling into your components
 */
const ErrorSystemExample = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    groupId: '',
    videoFiles: []
  });

  // Use the error handler hook
  const {
    showSimpleError,
    showToastError,
    showFFmpegError,
    showSRTError,
    showDockerError,
    showVideoError,
    handleValidationErrors,
    handleFileUploadError,
    handleStreamingError,
    handleApiCall,
    handleFetch
  } = useErrorHandler();

  // Example: Handle form validation errors
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Simulate validation
    const errors = {};
    if (!formData.groupId.trim()) {
      errors.groupId = 'Group ID is required';
    }
    if (formData.videoFiles.length === 0) {
      errors.videoFiles = 'At least one video file is required';
    }
    
    if (Object.keys(errors).length > 0) {
      handleValidationErrors(errors);
      return;
    }
    
    // Simulate API call
    await simulateStreamingStart();
  };

  // Example: Simulate streaming start with error handling
  const simulateStreamingStart = async () => {
    setIsLoading(true);
    
    try {
      // Simulate API call
      const response = await handleApiCall(
        () => fetch('/api/streaming/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        }),
        {
          context: {
            operation: 'start_streaming',
            group_id: formData.groupId,
            video_count: formData.videoFiles.length
          },
          throwOnError: true
        }
      );
      
      if (response) {
        showToastError('Streaming started successfully!', 3000);
      }
    } catch (error) {
      // Error is already handled by handleApiCall
      console.log('Streaming start failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Example: Show different types of errors
  const showExampleErrors = () => {
    return (
      <div className="error-examples">
        <h3>🔍 Error System Examples</h3>
        
        <div className="example-buttons">
          <button 
            onClick={() => showSimpleError('This is a simple error message')}
            className="example-btn simple"
          >
            Simple Error
          </button>
          
          <button 
            onClick={() => showToastError('This is a toast error that auto-hides', 3000)}
            className="example-btn toast"
          >
            Toast Error
          </button>
          
          <button 
            onClick={() => showFFmpegError('process_failed', {
              command: 'ffmpeg -i input.mp4 output.mp4',
              group_id: 'example_group'
            })}
            className="example-btn ffmpeg"
          >
            FFmpeg Error
          </button>
          
          <button 
            onClick={() => showSRTError('connection_timeout', {
              srt_ip: '192.168.1.100',
              srt_port: 9000,
              timeout: 5
            })}
            className="example-btn srt"
          >
            SRT Error
          </button>
          
          <button 
            onClick={() => showDockerError('service_not_running', {
              service_name: 'docker',
              check_command: 'sudo systemctl status docker'
            })}
            className="example-btn docker"
          >
            Docker Error
          </button>
          
          <button 
            onClick={() => showVideoError('file_not_found', {
              file_path: '/path/to/video.mp4',
              requested_by: 'streaming_component'
            })}
            className="example-btn video"
          >
            Video Error
          </button>
        </div>
      </div>
    );
  };

  // Example: Simulate file upload with error handling
  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    
    if (files.length === 0) return;
    
    // Simulate file validation
    for (const file of files) {
      if (file.size > 100 * 1024 * 1024) { // 100MB limit
        handleFileUploadError(new Error('File size exceeds limit'), {
          file_name: file.name,
          file_size: file.size,
          max_size: '100MB'
        });
        return;
      }
      
      if (!file.type.startsWith('video/')) {
        handleFileUploadError(new Error('Invalid file format'), {
          file_name: file.name,
          file_type: file.type,
          allowed_types: 'video/*'
        });
        return;
      }
    }
    
    setFormData(prev => ({
      ...prev,
      videoFiles: [...prev.videoFiles, ...files]
    }));
    
    showToastError(`${files.length} file(s) uploaded successfully!`, 2000);
  };

  // Example: Simulate network error
  const simulateNetworkError = async () => {
    try {
      await handleFetch('/api/nonexistent-endpoint', {}, {
        context: { operation: 'test_network' },
        throwOnError: true
      });
    } catch (error) {
      // Error is already handled
      console.log('Network error simulated:', error);
    }
  };

  // Example: Simulate streaming error
  const simulateStreamingError = () => {
    const error = new Error('SRT connection failed: Connection refused');
    handleStreamingError(error, {
      group_id: 'example_group',
      operation: 'start_streaming',
      timestamp: new Date().toISOString()
    });
  };

  return (
    <div className="error-system-example">
      <div className="example-header">
        <h2>🚀 Error System Integration Examples</h2>
        <p>This component demonstrates how to use the comprehensive error handling system</p>
      </div>

      {/* Error Examples Section */}
      {showExampleErrors()}

      {/* Form Example Section */}
      <div className="form-example">
        <h3>📝 Form with Error Handling</h3>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="groupId">Group ID:</label>
            <input
              type="text"
              id="groupId"
              value={formData.groupId}
              onChange={(e) => setFormData(prev => ({ ...prev, groupId: e.target.value }))}
              placeholder="Enter group ID"
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="videoFiles">Video Files:</label>
            <input
              type="file"
              id="videoFiles"
              multiple
              accept="video/*"
              onChange={handleFileUpload}
            />
            {formData.videoFiles.length > 0 && (
              <div className="file-list">
                <p>Selected files: {formData.videoFiles.length}</p>
                <ul>
                  {formData.videoFiles.map((file, index) => (
                    <li key={index}>{file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          
          <button 
            type="submit" 
            disabled={isLoading}
            className="submit-btn"
          >
            {isLoading ? 'Starting Stream...' : 'Start Streaming'}
          </button>
        </form>
      </div>

      {/* Additional Examples Section */}
      <div className="additional-examples">
        <h3>🔧 Additional Error Scenarios</h3>
        
        <div className="example-buttons">
          <button 
            onClick={simulateNetworkError}
            className="example-btn network"
          >
            Simulate Network Error
          </button>
          
          <button 
            onClick={simulateStreamingError}
            className="example-btn streaming"
          >
            Simulate Streaming Error
          </button>
          
          <button 
            onClick={() => showErrorByCode(143, {
              group_id: 'example_group',
              operation: 'docker_check'
            })}
            className="example-btn code"
          >
            Show Error by Code (143)
          </button>
        </div>
      </div>

      {/* Usage Instructions */}
      <div className="usage-instructions">
        <h3>📚 How to Use This Error System</h3>
        
        <div className="instructions-grid">
          <div className="instruction-card">
            <h4>1. Setup</h4>
            <p>Wrap your app with <code>ErrorProvider</code> in your main App component</p>
            <pre>{`<ErrorProvider>
  <App />
</ErrorProvider>`}</pre>
          </div>
          
          <div className="instruction-card">
            <h4>2. Use Hook</h4>
            <p>Import and use the <code>useErrorHandler</code> hook in your components</p>
            <pre>{`const { showError, handleApiCall } = useErrorHandler();`}</pre>
          </div>
          
          <div className="instruction-card">
            <h4>3. Handle Errors</h4>
            <p>Use the provided methods to handle different types of errors</p>
            <pre>{`try {
  await handleApiCall(apiFunction);
} catch (error) {
  // Error is automatically handled and displayed
}`}</pre>
          </div>
          
          <div className="instruction-card">
            <h4>4. Custom Errors</h4>
            <p>Show specific error types with context information</p>
            <pre>{`showFFmpegError('process_failed', {
  command: 'ffmpeg -i input.mp4 output.mp4',
  group_id: 'group_123'
});`}</pre>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ErrorSystemExample;

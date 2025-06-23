import React, { useState } from 'react';

interface FileUploadProps {
  setOutput: (message: string) => void;
  onUploadComplete?: () => void;
}

interface UploadProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const FileUploadSection: React.FC<FileUploadProps> = ({ setOutput, onUploadComplete }) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress[]>([]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files);
      setSelectedFiles(filesArray);
      
      // Initialize progress tracking for each file
      const initialProgress = filesArray.map(file => ({
        file,
        progress: 0,
        status: 'pending' as const
      }));
      setUploadProgress(initialProgress);
    }
  };

  const uploadSingleFile = async (file: File, index: number): Promise<void> => {
    return new Promise((resolve, reject) => {
      const formData = new FormData();
      formData.append('file', file);

      const xhr = new XMLHttpRequest();
      
      xhr.open('POST', `${API_BASE_URL}/upload_video`, true);
      
      // Update progress for this specific file
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percentComplete = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(prev => prev.map((item, i) => 
            i === index ? { ...item, progress: percentComplete, status: 'uploading' } : item
          ));
        }
      };
      
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          setUploadProgress(prev => prev.map((item, i) => 
            i === index ? { ...item, progress: 100, status: 'completed' } : item
          ));
          resolve();
        } else {
          let errorMessage;
          try {
            const response = JSON.parse(xhr.responseText);
            errorMessage = response.message || `Upload failed with status: ${xhr.status}`;
          } catch (e) {
            errorMessage = `Upload failed with status: ${xhr.status}`;
          }
          setUploadProgress(prev => prev.map((item, i) => 
            i === index ? { ...item, status: 'error', error: errorMessage } : item
          ));
          reject(new Error(errorMessage));
        }
      };
      
      xhr.onerror = () => {
        const errorMessage = 'Network failure during upload';
        setUploadProgress(prev => prev.map((item, i) => 
          i === index ? { ...item, status: 'error', error: errorMessage } : item
        ));
        reject(new Error(errorMessage));
      };
      
      xhr.send(formData);
    });
  };

  const uploadAllFiles = async () => {
    if (selectedFiles.length === 0) {
      setOutput('Please select files to upload');
      return;
    }

    try {
      setUploading(true);
      setOutput(`Starting upload of ${selectedFiles.length} file(s)...`);

      // Upload files sequentially to avoid overwhelming the server
      for (let i = 0; i < selectedFiles.length; i++) {
        try {
          await uploadSingleFile(selectedFiles[i], i);
          setOutput(`Uploaded ${i + 1}/${selectedFiles.length}: ${selectedFiles[i].name}`);
        } catch (error) {
          setOutput(`Failed to upload ${selectedFiles[i].name}: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
      }

      // Check results
      const completed = uploadProgress.filter(p => p.status === 'completed').length;
      const failed = uploadProgress.filter(p => p.status === 'error').length;
      
      if (completed === selectedFiles.length) {
        setOutput(`All ${selectedFiles.length} files uploaded successfully!`);
      } else if (completed > 0) {
        setOutput(`Upload completed: ${completed} successful, ${failed} failed`);
      } else {
        setOutput(`Upload failed: All ${selectedFiles.length} files failed to upload`);
      }

      // Reset selection
      setSelectedFiles([]);
      setUploadProgress([]);
      
      // Reset the file input
      const fileInput = document.getElementById('file-upload') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
      
      // Call completion callback
      if (onUploadComplete) onUploadComplete();
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      setOutput(`Error during batch upload: ${errorMessage}`);
    } finally {
      setUploading(false);
    }
  };

  const removeFile = (index: number) => {
    const newFiles = selectedFiles.filter((_, i) => i !== index);
    setSelectedFiles(newFiles);
    
    const newProgress = uploadProgress.filter((_, i) => i !== index);
    setUploadProgress(newProgress);
  };

  const clearAllFiles = () => {
    setSelectedFiles([]);
    setUploadProgress([]);
    
    const fileInput = document.getElementById('file-upload') as HTMLInputElement;
    if (fileInput) fileInput.value = '';
  };

  // Helper function to format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const getStatusIcon = (status: UploadProgress['status']) => {
    switch (status) {
      case 'pending': return '⏳';
      case 'uploading': return '🔄';
      case 'completed': return '✅';
      case 'error': return '❌';
      default: return '⏳';
    }
  };

  const getTotalSize = () => {
    return selectedFiles.reduce((total, file) => total + file.size, 0);
  };

  const getOverallProgress = () => {
    if (uploadProgress.length === 0) return 0;
    const totalProgress = uploadProgress.reduce((sum, item) => sum + item.progress, 0);
    return Math.round(totalProgress / uploadProgress.length);
  };

  return (
    <div className="file-upload-section">
      <h3>Upload Video Files</h3>
      
      <div className="upload-form">
        <input
          type="file"
          id="file-upload"
          onChange={handleFileChange}
          accept="video/*"
          multiple
          disabled={uploading}
          className="file-input"
        />
        <button
          onClick={uploadAllFiles}
          disabled={selectedFiles.length === 0 || uploading}
          className="upload-button"
        >
          {uploading ? `Uploading... (${getOverallProgress()}%)` : `Upload ${selectedFiles.length} File(s)`}
        </button>
        {selectedFiles.length > 0 && (
          <button
            onClick={clearAllFiles}
            disabled={uploading}
            className="clear-button"
            style={{ marginLeft: '10px', backgroundColor: '#dc3545' }}
          >
            Clear All
          </button>
        )}
      </div>
      
      {/* Overall Progress Bar (when uploading) */}
      {uploading && (
        <div className="progress-container">
          <div className="progress-bar" style={{ width: `${getOverallProgress()}%` }}></div>
          <div className="progress-text">{getOverallProgress()}%</div>
        </div>
      )}
      
      {/* Selected Files List */}
      {selectedFiles.length > 0 && (
        <div className="selected-files">
          <h4>Selected Files ({selectedFiles.length})</h4>
          <div className="files-summary">
            <p><strong>Total size:</strong> {formatFileSize(getTotalSize())}</p>
          </div>
          
          <div className="files-list">
            {selectedFiles.map((file, index) => {
              const progressInfo = uploadProgress[index];
              
              return (
                <div key={`${file.name}-${index}`} className="file-item">
                  <div className="file-info">
                    <div className="file-header">
                      <span className="file-name">{file.name}</span>
                      <span className="file-status">{progressInfo ? getStatusIcon(progressInfo.status) : '⏳'}</span>
                      {!uploading && (
                        <button
                          onClick={() => removeFile(index)}
                          className="remove-file-btn"
                          title="Remove file"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                    
                    <div className="file-details">
                      <span className="file-size">{formatFileSize(file.size)}</span>
                      <span className="file-type">{file.type}</span>
                    </div>
                    
                    {/* Individual Progress Bar */}
                    {progressInfo && progressInfo.status === 'uploading' && (
                      <div className="individual-progress">
                        <div className="progress-bar-small" style={{ width: `${progressInfo.progress}%` }}></div>
                        <span className="progress-text-small">{progressInfo.progress}%</span>
                      </div>
                    )}
                    
                    {/* Error Message */}
                    {progressInfo && progressInfo.status === 'error' && (
                      <div className="error-message">
                        <span>Error: {progressInfo.error}</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <style jsx>{`
        .selected-files {
          margin-top: 20px;
          padding: 15px;
          border: 1px solid #ddd;
          border-radius: 8px;
          background-color: #f9f9f9;
        }
        
        .files-summary {
          margin-bottom: 15px;
          font-size: 14px;
          color: #666;
        }
        
        .files-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        
        .file-item {
          padding: 10px;
          border: 1px solid #e0e0e0;
          border-radius: 6px;
          background-color: white;
        }
        
        .file-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 5px;
        }
        
        .file-name {
          font-weight: 500;
          flex: 1;
          margin-right: 10px;
        }
        
        .file-status {
          font-size: 16px;
          margin-right: 10px;
        }
        
        .remove-file-btn {
          background: #dc3545;
          color: white;
          border: none;
          border-radius: 4px;
          width: 24px;
          height: 24px;
          cursor: pointer;
          font-size: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        
        .remove-file-btn:hover {
          background: #c82333;
        }
        
        .file-details {
          display: flex;
          gap: 15px;
          font-size: 12px;
          color: #666;
        }
        
        .individual-progress {
          margin-top: 8px;
          position: relative;
          height: 8px;
          background-color: #e9ecef;
          border-radius: 4px;
          overflow: hidden;
        }
        
        .progress-bar-small {
          height: 100%;
          background: linear-gradient(90deg, #28a745, #20c997);
          transition: width 0.3s ease;
        }
        
        .progress-text-small {
          position: absolute;
          top: -20px;
          right: 0;
          font-size: 10px;
          color: #666;
        }
        
        .error-message {
          margin-top: 5px;
          padding: 5px;
          background-color: #f8d7da;
          color: #721c24;
          border-radius: 4px;
          font-size: 12px;
        }
        
        .clear-button:hover {
          background-color: #c82333 !important;
        }
      `}</style>
    </div>
  );
};

export default FileUploadSection;
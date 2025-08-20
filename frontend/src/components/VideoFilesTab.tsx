import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Upload, Trash2, File, FileVideo, AlertCircle, CheckCircle, RefreshCw } from "lucide-react";
import { useErrorHandler } from '@/components/ErrorSystem/useErrorHandler';
import { videoApi } from '@/API/api';

// Updated type definitions for new sequential API responses
interface UploadResponse {
  successful: Array<{
    original_filename: string;
    saved_filename: string;
    size_mb: number;
    status: string;
    path: string;
    processing_time_seconds: number;
  }>;
  failed: Array<{
    filename: string;
    error: string;
  }>;
  summary: {
    total: number;
    successful: number;
    failed: number;
  };
  timing: {
    total_time_seconds: number;
    started_at: string;
    completed_at: string;
    individual_uploads: Array<{
      filename: string;
      upload_time_seconds: number;
      file_size_mb: number;
    }>;
  };
}

interface VideosResponse {
  videos: Array<{
    id?: string;
    name: string;
    size?: number;
    duration?: string;
    resolution?: string;
    upload_date?: string;
  }>;
  total_videos?: number;
  success?: boolean;
}

interface VideoFile {
  id: string;
  name: string;
  size: number;
  duration?: string;
  format: string;
  resolution?: string;
  uploadDate: string;
  status: 'ready' | 'processing' | 'error';
}

interface UploadingFile {
  name: string;
  progress: number;
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  size: number;
  error?: string;
  isCurrentFile?: boolean;
}

interface DeleteResponse {
  success: boolean;
  message: string;
  deleted_files?: string[];
  errors?: string[];
  searched_locations?: string[];
}

const VideoFilesTab = () => {
  const { showError, handleFileUploadError, handleApiError } = useErrorHandler();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadingFiles, setUploadingFiles] = useState<Record<string, UploadingFile>>({});
  const [videoFiles, setVideoFiles] = useState<VideoFile[]>([]);
  const [isLoadingVideos, setIsLoadingVideos] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [overallProgress, setOverallProgress] = useState(0);
  const [currentUploadInfo, setCurrentUploadInfo] = useState<{
    currentFile: string;
    completedFiles: number;
    totalFiles: number;
  } | null>(null);

  // File mapping for sequential uploads
  const fileUploadMapRef = useRef<Map<File, string>>(new Map());

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const generateFileId = (file: File, index: number) => {
    return `${file.name}-${Date.now()}-${index}-${Math.random().toString(36).substr(2, 9)}`;
  };

  const validateFile = (file: File) => {
    const supportedFormats = ['mp4', 'avi', 'mov', 'mkv', 'webm'];
    const maxSize = 2 * 1024 * 1024 * 1024; // 2GB
    const fileExtension = file.name.split('.').pop()?.toLowerCase();

    if (!fileExtension || !supportedFormats.includes(fileExtension)) {
      return { valid: false, error: 'Unsupported format' };
    }

    if (file.size > maxSize) {
      return { valid: false, error: 'File too large (max 2GB)' };
    }

    return { valid: true };
  };

  const handleSequentialUpload = async (validFiles: File[]) => {
    try {
      console.log(` Starting sequential upload of ${validFiles.length} files`);

      // Check if videoApi exists
      if (!videoApi?.uploadVideo) {
        throw new Error("Video upload API not available");
      }

      // Upload all files sequentially with progress tracking
      const response = await videoApi.uploadVideo(validFiles, (progress) => {
        // Update overall progress
        setOverallProgress(progress.overallProgress);
        setCurrentUploadInfo({
          currentFile: progress.currentFile,
          completedFiles: progress.completedFiles,
          totalFiles: progress.totalFiles
        });

        // Find the current file being uploaded
        const currentFile = validFiles[progress.currentFileIndex];
        const currentFileId = fileUploadMapRef.current.get(currentFile);

        if (currentFileId) {
          // Update upload progress
          setUploadingFiles(prev => {
            const newState = { ...prev };

            // Reset all files to not current
            Object.keys(newState).forEach(fileId => {
              newState[fileId] = {
                ...newState[fileId],
                isCurrentFile: false
              };
            });

            // Update current file
            newState[currentFileId] = {
              ...newState[currentFileId],
              progress: progress.currentFileProgress,
              status: progress.currentFileProgress === 100 ? 'processing' : 'uploading',
              isCurrentFile: true
            };

            return newState;
          });
        }

        console.log(` Overall: ${progress.overallProgress.toFixed(1)}% | Current: ${progress.currentFile} (${progress.currentFileProgress.toFixed(1)}%)`);
      }) as UploadResponse;

      console.log(` Sequential upload complete:`, response);

      // Process successful uploads
      if (response.successful && response.successful.length > 0) {
        response.successful.forEach((uploadResult) => {
          const originalFile = validFiles.find(f => f.name === uploadResult.original_filename);
          const fileId = originalFile ? fileUploadMapRef.current.get(originalFile) : null;

          if (fileId && originalFile) {
            // Mark as completed
            setUploadingFiles(prev => ({
              ...prev,
              [fileId]: {
                ...prev[fileId],
                progress: 100,
                status: 'completed',
                isCurrentFile: false
              }
            }));

            // Create new video file entry
            const newVideo: VideoFile = {
              id: `${uploadResult.saved_filename || originalFile.name}-${Date.now()}`,
              name: uploadResult.saved_filename || originalFile.name,
              size: originalFile.size,
              duration: '0:00',
              format: originalFile.name.split('.').pop()?.toUpperCase() || 'MP4',
              resolution: 'Original',
              uploadDate: new Date().toISOString().split('T')[0],
              status: 'ready'
            };

            setVideoFiles(prev => [newVideo, ...prev]);

            // Remove from upload tracking after delay
            setTimeout(() => {
              setUploadingFiles(prev => {
                const newState = { ...prev };
                delete newState[fileId];
                return newState;
              });
            }, 2000);
          }
        });
      }

      // Process failed uploads
      if (response.failed && response.failed.length > 0) {
        response.failed.forEach((failedUpload) => {
          const originalFile = validFiles.find(f => f.name === failedUpload.filename);
          const fileId = originalFile ? fileUploadMapRef.current.get(originalFile) : null;

          if (fileId) {
            setUploadingFiles(prev => ({
              ...prev,
              [fileId]: {
                ...prev[fileId],
                status: 'failed',
                error: failedUpload.error,
                isCurrentFile: false
              }
            }));

            // Remove from tracking after delay
            setTimeout(() => {
              setUploadingFiles(prev => {
                const newState = { ...prev };
                delete newState[fileId];
                return newState;
              });
            }, 5000);
          }
        });
      }

      // Summary toast and cleanup
      const { successful, failed, total } = response.summary;

      if (total > 1) {
        showError({
          message: `Upload Complete: ${successful}/${total} files uploaded successfully${failed > 0 ? `, ${failed} failed` : ''} in ${response.timing.total_time_seconds}s`,
          error_code: 'UPLOAD_COMPLETE',
          error_category: 'INFO',
          context: {
            component: 'VideoFilesTab',
            operation: 'handleSequentialUpload',
            timestamp: new Date().toISOString(),
            total_files: total,
            successful_files: successful,
            failed_files: failed,
            total_time_seconds: response.timing.total_time_seconds
          }
        });
      } else if (successful === 1) {
        showError({
          message: `File uploaded successfully in ${response.timing.total_time_seconds}s`,
          error_code: 'UPLOAD_SUCCESSFUL',
          error_category: 'INFO',
          context: {
            component: 'VideoFilesTab',
            operation: 'handleSequentialUpload',
            timestamp: new Date().toISOString(),
            total_time_seconds: response.timing.total_time_seconds
          }
        });
      }

      console.log(` Upload Summary: ${successful}/${total} successful in ${response.timing.total_time_seconds}s`);

      // Reset progress tracking
      setOverallProgress(0);
      setCurrentUploadInfo(null);

    } catch (error: any) {
      console.error(` Sequential upload failed:`, error);

      // Mark all files as failed
      validFiles.forEach(file => {
        const fileId = fileUploadMapRef.current.get(file);
        if (fileId) {
          setUploadingFiles(prev => ({
            ...prev,
            [fileId]: {
              ...prev[fileId],
              status: 'failed',
              error: error.message || 'Upload failed',
              isCurrentFile: false
            }
          }));

          // Remove from tracking after delay
          setTimeout(() => {
            setUploadingFiles(prev => {
              const newState = { ...prev };
              delete newState[fileId];
              return newState;
            });
          }, 5000);
        }
      });

      // Use error system for better error handling
      showError({
        message: error.message || "All uploads failed",
        error_code: 'FILE_UPLOAD_FAILED',
        error_category: '5xx',
        context: {
          component: 'VideoFilesTab',
          operation: 'handleSequentialUpload',
          timestamp: new Date().toISOString(),
          original_error: error.message,
          stack: error.stack
        }
      });

      handleApiError({
        message: error.message || "All uploads failed",
        error_code: 'FILE_UPLOAD_FAILED',
        error_category: '5xx',
        context: {
          component: 'VideoFilesTab',
          operation: 'handleSequentialUpload',
          timestamp: new Date().toISOString(),
          original_error: error.message,
          stack: error.stack
        }
      });

      // Reset progress tracking
      setOverallProgress(0);
      setCurrentUploadInfo(null);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    console.log(` Starting upload of ${files.length} file(s)`);

    // Validate files
    const validFiles: File[] = [];
    const invalidFiles: string[] = [];

    Array.from(files).forEach((file) => {
      const validation = validateFile(file);
      if (validation.valid) {
        validFiles.push(file);
      } else {
        invalidFiles.push(`${file.name} (${validation.error})`);
      }
    });

    // Show validation errors
    if (invalidFiles.length > 0) {
      showError({
        message: `Some files were skipped: ${invalidFiles.join(', ')}`,
        error_code: 'FILE_VALIDATION_FAILED',
        error_category: '4xx',
        context: {
          component: 'VideoFilesTab',
          operation: 'handleFileUpload',
          timestamp: new Date().toISOString(),
          invalid_files: invalidFiles
        }
      });
    }

    if (validFiles.length === 0) return;

    // Initialize upload tracking
    fileUploadMapRef.current.clear();
    const initialUploadStates: Record<string, UploadingFile> = {};

    validFiles.forEach((file, index) => {
      const fileId = generateFileId(file, index);
      fileUploadMapRef.current.set(file, fileId);
      initialUploadStates[fileId] = {
        name: file.name,
        progress: 0,
        status: 'uploading',
        size: file.size,
        isCurrentFile: false
      };
    });

    setUploadingFiles(initialUploadStates);

    showError({
      message: `Uploading ${validFiles.length} file(s) sequentially...`,
      error_code: 'UPLOAD_STARTED',
      error_category: 'INFO',
      context: {
        component: 'VideoFilesTab',
        operation: 'handleFileUpload',
        timestamp: new Date().toISOString(),
        total_files: validFiles.length
      }
    });

    // Start sequential upload
    await handleSequentialUpload(validFiles);

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeVideo = async (videoId: string, videoName: string) => {
    console.log(` Attempting to delete video: ${videoName}`);

    try {
      if (!videoApi?.deleteVideo) {
        throw new Error("Delete API not available");
      }

      const response = await videoApi.deleteVideo(videoName);
      console.log('Delete response:', response);

      if (response?.success) {
        // Remove from local state
        setVideoFiles(prev => prev.filter(v => v.id !== videoId));

        showError({
          message: `${videoName} has been deleted successfully.`,
          error_code: 'VIDEO_DELETED',
          error_category: 'INFO',
          context: {
            component: 'VideoFilesTab',
            operation: 'removeVideo',
            video_id: videoId,
            video_name: videoName,
            timestamp: new Date().toISOString()
          }
        });

      } else {
        throw new Error(response?.message || 'Failed to delete video - unknown error');
      }

    } catch (error: any) {
      console.error(` Delete failed for ${videoName}:`, error);

      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

      // Use error system for better error handling
      showError({
        message: `Failed to delete ${videoName}: ${errorMessage}`,
        error_code: 'VIDEO_DELETION_FAILED',
        error_category: '5xx',
        context: {
          component: 'VideoFilesTab',
          operation: 'removeVideo',
          video_id: videoId,
          video_name: videoName,
          timestamp: new Date().toISOString(),
          original_error: errorMessage,
          stack: error?.stack
        }
      });

      handleApiError({
        message: `Failed to delete ${videoName}: ${errorMessage}`,
        error_code: 'VIDEO_DELETION_FAILED',
        error_category: '5xx',
        context: {
          component: 'VideoFilesTab',
          operation: 'removeVideo',
          video_id: videoId,
          video_name: videoName,
          timestamp: new Date().toISOString(),
          original_error: errorMessage,
          stack: error?.stack
        }
      });
    }
  };

  const fetchVideos = async () => {
    try {
      console.log(' Fetching videos from server...');

      if (!videoApi?.getVideos) {
        console.warn(' videoApi.getVideos not available');
        setVideoFiles([]);
        return;
      }

      const response = await videoApi.getVideos() as VideosResponse;

      if (Array.isArray(response.videos)) {
        const transformedVideos: VideoFile[] = response.videos.map((video: any, index: number) => ({
          id: video.id || `${video.name}-${index}`,
          name: video.name || `video-${index}`,
          size: video.size || 0,
          duration: video.duration || '0:00',
          format: video.name?.split('.').pop()?.toUpperCase() || 'MP4',
          resolution: video.resolution || '1920x1080',
          uploadDate: video.upload_date || new Date().toISOString().split('T')[0],
          status: 'ready' as const
        }));

        setVideoFiles(transformedVideos);
        console.log(` Loaded ${transformedVideos.length} videos`);
      } else {
        console.log(' No videos found or invalid response structure');
        setVideoFiles([]);
      }
    } catch (error: any) {
      console.error(' Error fetching videos:', error);

      // Use error system for better error handling
      showError({
        message: "Failed to load videos. Please check your connection.",
        error_code: 'VIDEO_FETCH_FAILED',
        error_category: '5xx',
        context: {
          component: 'VideoFilesTab',
          operation: 'fetchVideos',
          timestamp: new Date().toISOString(),
          original_error: error?.message,
          stack: error?.stack
        }
      });

      handleApiError({
        message: "Failed to load videos. Please check your connection.",
        error_code: 'VIDEO_FETCH_FAILED',
        error_category: '5xx',
        context: {
          component: 'VideoFilesTab',
          operation: 'fetchVideos',
          timestamp: new Date().toISOString(),
          original_error: error?.message,
          stack: error?.stack
        }
      });
      setVideoFiles([]);
    }
  };

  const refreshVideos = async () => {
    setIsRefreshing(true);
    await fetchVideos();
    setIsRefreshing(false);
  };

  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  };

  const getStatusIcon = (status: VideoFile['status']) => {
    switch (status) {
      case 'ready':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'processing':
        return <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
    }
  };

  const getStatusBadge = (status: VideoFile['status']) => {
    const baseClasses = "flex items-center gap-1";

    switch (status) {
      case 'ready':
        return (
          <Badge className={`${baseClasses} bg-green-100 text-green-800 border-green-200`}>
            {getStatusIcon(status)}
            Ready
          </Badge>
        );
      case 'processing':
        return (
          <Badge className={`${baseClasses} bg-blue-100 text-blue-800 border-blue-200`}>
            {getStatusIcon(status)}
            Processing
          </Badge>
        );
      case 'error':
        return (
          <Badge className={`${baseClasses} bg-red-100 text-red-800 border-red-200`}>
            {getStatusIcon(status)}
            Error
          </Badge>
        );
      default:
        return (
          <Badge className={`${baseClasses} bg-gray-100 text-gray-800 border-gray-200`}>
            Unknown
          </Badge>
        );
    }
  };

  // Load videos on component mount
  useEffect(() => {
    const loadInitialVideos = async () => {
      setIsLoadingVideos(true);
      await fetchVideos();
      setIsLoadingVideos(false);
    };

    loadInitialVideos();
  }, []);

  const totalSize = videoFiles.reduce((total, file) => total + file.size, 0);
  const readyFiles = videoFiles.filter(v => v.status === 'ready').length;
  const processingFiles = videoFiles.filter(v => v.status === 'processing').length;
  const activeUploads = Object.keys(uploadingFiles).length;

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Total Files</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-600">{videoFiles.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Ready</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{readyFiles}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Processing</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-yellow-600">{processingFiles}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Total Size</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-purple-600">{formatFileSize(totalSize)}</div>
          </CardContent>
        </Card>
      </div>

      {/* Upload Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Upload Video Files
          </CardTitle>
          <CardDescription>
            Upload MP4, AVI, MOV, MKV, or WebM files to stream to your displays
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div
              className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-gray-400 transition-colors cursor-pointer"
              onClick={triggerFileUpload}
            >
              <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-700 mb-2">Click to upload or drag and drop</p>
              <p className="text-gray-500 text-sm">Supported: MP4, AVI, MOV, MKV, WebM (Max 2GB each)</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".mp4,.avi,.mov,.mkv,.webm"
                onChange={handleFileUpload}
                className="hidden"
                multiple
              />
            </div>

            {/* Overall Progress for Multiple Files */}
            {currentUploadInfo && currentUploadInfo.totalFiles > 1 && (
              <div className="space-y-2 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex justify-between text-sm text-blue-700 font-medium">
                  <span>Sequential Upload Progress</span>
                  <span>{currentUploadInfo.completedFiles}/{currentUploadInfo.totalFiles} files</span>
                </div>
                <Progress value={overallProgress} className="w-full h-3" />
                {currentUploadInfo.currentFile && (
                  <p className="text-sm text-blue-600">
                    Currently uploading: <span className="font-medium">{currentUploadInfo.currentFile}</span>
                  </p>
                )}
              </div>
            )}

            {/* Upload Progress */}
            {activeUploads > 0 && (
              <div className="space-y-3">
                <div className="text-sm font-medium text-gray-700">
                  {currentUploadInfo && currentUploadInfo.totalFiles > 1
                    ? `Sequential Upload: ${activeUploads} file(s) in queue`
                    : `Uploading ${activeUploads} file(s):`
                  }
                </div>

                {Object.entries(uploadingFiles).map(([fileId, fileInfo]) => (
                  <div key={fileId} className={`space-y-2 p-3 rounded-lg border ${fileInfo.isCurrentFile
                    ? 'border-blue-500 bg-blue-50 shadow-sm'
                    : 'bg-gray-50 border-gray-200'
                    }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FileVideo className={`w-4 h-4 ${fileInfo.isCurrentFile ? 'text-blue-500' : 'text-gray-500'}`} />
                        <span className="text-sm font-medium truncate max-w-xs">
                          {fileInfo.name}
                        </span>
                        {fileInfo.isCurrentFile && (
                          <Badge variant="outline" className="text-xs bg-blue-100 text-blue-700 border-blue-300">
                            Uploading Now
                          </Badge>
                        )}
                        {fileInfo.status === 'uploading' && !fileInfo.isCurrentFile && (
                          <Badge variant="outline" className="text-xs bg-gray-100 text-gray-600">
                            Waiting
                          </Badge>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        {fileInfo.status === 'uploading' && fileInfo.isCurrentFile && (
                          <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                        )}
                        {fileInfo.status === 'processing' && (
                          <div className="w-4 h-4 border-2 border-yellow-600 border-t-transparent rounded-full animate-spin" />
                        )}
                        {fileInfo.status === 'completed' && (
                          <CheckCircle className="w-4 h-4 text-green-600" />
                        )}
                        {fileInfo.status === 'failed' && (
                          <AlertCircle className="w-4 h-4 text-red-600" />
                        )}

                        <span className="text-xs text-gray-500 min-w-[3rem] text-right">
                          {Math.round(fileInfo.progress)}%
                        </span>
                      </div>
                    </div>

                    <Progress
                      value={fileInfo.progress}
                      className="h-2"
                    />

                    <div className="flex justify-between text-xs text-gray-500">
                      <span>
                        {fileInfo.status === 'uploading' && fileInfo.isCurrentFile ? 'Uploading...' :
                          fileInfo.status === 'uploading' && !fileInfo.isCurrentFile ? 'Waiting in queue...' :
                            fileInfo.status === 'processing' ? 'Processing...' :
                              fileInfo.status === 'completed' ? 'Completed!' :
                                fileInfo.status === 'failed' ? `Failed: ${fileInfo.error || 'Unknown error'}` : 'Unknown'}
                      </span>
                      <span>{formatFileSize(fileInfo.size)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Video Library */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Video Library</CardTitle>
              <CardDescription>
                All video files available for streaming
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={refreshVideos}
              disabled={isRefreshing}
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoadingVideos ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mr-4" />
              <span className="text-gray-600">Loading videos...</span>
            </div>
          ) : videoFiles.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <File className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No video files found.</p>
              <p className="text-sm mt-2">Upload your first video to get started.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {videoFiles.map((video) => (
                <div
                  key={video.id}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="flex items-center justify-center w-12 h-12 bg-gray-200 rounded-lg">
                      <FileVideo className="w-6 h-6 text-gray-600" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium">{video.name}</h3>
                        {getStatusBadge(video.status)}
                      </div>
                      <div className="text-sm text-gray-600">
                        {formatFileSize(video.size)}  {video.duration}  {video.format}
                        {video.resolution && `  ${video.resolution}`}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        Uploaded: {video.uploadDate}
                      </div>
                    </div>
                  </div>

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => removeVideo(video.id, video.name)}
                    className="border-red-300 text-red-600 hover:bg-red-50"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default VideoFilesTab;
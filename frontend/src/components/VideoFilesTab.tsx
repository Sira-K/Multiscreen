import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Upload, Trash2, File, FileVideo, AlertCircle, CheckCircle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { videoApi } from '@/API/api';

interface VideoFile {
  id: string;
  name: string;
  size: number;
  duration: string;
  format: string;
  resolution: string;
  uploadDate: string;
  status: 'ready' | 'processing' | 'error';
}

const VideoFilesTab = () => {
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadingFiles, setUploadingFiles] = useState<Record<string, {
    name: string;
    progress: number;
    status: 'uploading' | 'processing' | 'completed' | 'failed';
    size: number;
  }>>({});
  
  const [videoFiles, setVideoFiles] = useState<VideoFile[]>([]);
  const [isLoadingVideos, setIsLoadingVideos] = useState(true);

  // Debug logging function
  const debugLog = (message: string, data?: any) => {
    console.log(`🐛 DEBUG [VideoFilesTab]: ${message}`, data || '');
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    debugLog("Upload function triggered");
    
    const files = event.target.files;
    if (!files || files.length === 0) {
      debugLog("No files selected");
      return;
    }

    debugLog(`${files.length} file(s) selected`, Array.from(files).map(f => ({
      name: f.name,
      size: f.size,
      type: f.type,
      lastModified: f.lastModified
    })));

    const supportedFormats = ['mp4', 'avi', 'mov', 'mkv'];
    const maxSize = 2 * 1024 * 1024 * 1024; // 2GB
    
    // Validate all files first
    const validFiles: File[] = [];
    const invalidFiles: string[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const fileExtension = file.name.split('.').pop()?.toLowerCase();
      
      debugLog(`Validating file ${i + 1}`, {
        name: file.name,
        extension: fileExtension,
        size: file.size,
        sizeFormatted: formatFileSize(file.size),
        isValidFormat: fileExtension && supportedFormats.includes(fileExtension),
        isValidSize: file.size <= maxSize
      });

      if (!fileExtension || !supportedFormats.includes(fileExtension)) {
        invalidFiles.push(`${file.name} (unsupported format)`);
        debugLog(`File rejected - unsupported format: ${fileExtension}`);
        continue;
      }

      if (file.size > maxSize) {
        invalidFiles.push(`${file.name} (file too large)`);
        debugLog(`File rejected - too large: ${formatFileSize(file.size)}`);
        continue;
      }

      validFiles.push(file);
      debugLog(`File accepted: ${file.name}`);
    }

    debugLog(`Validation complete. Valid: ${validFiles.length}, Invalid: ${invalidFiles.length}`);

    // Show validation errors if any
    if (invalidFiles.length > 0) {
      debugLog("Showing validation error toast");
      toast({
        title: "Some files were skipped",
        description: `Invalid files: ${invalidFiles.join(', ')}`,
        variant: "destructive"
      });
    }

    if (validFiles.length === 0) {
      debugLog("No valid files to upload, exiting");
      return;
    }

    // Create unique file IDs for tracking
    const fileUploadMap = new Map();
    validFiles.forEach((file, index) => {
      const fileId = `${file.name}-${Date.now()}-${index}-${Math.random().toString(36).substr(2, 9)}`;
      fileUploadMap.set(file, fileId);
      debugLog(`Created fileId for ${file.name}: ${fileId}`);
    });

    // Initialize upload tracking
    const initialUploadStates: Record<string, any> = {};
    fileUploadMap.forEach((fileId, file) => {
      initialUploadStates[fileId] = {
        name: file.name,
        progress: 0,
        status: 'uploading',
        size: file.size
      };
    });
    
    debugLog("Setting upload states", initialUploadStates);
    setUploadingFiles(initialUploadStates);

    debugLog("Showing upload started toast");
    toast({
      title: "Upload Started",
      description: `Uploading ${validFiles.length} file(s)...`
    });

    // Upload all files
    const uploadPromises = validFiles.map(async (file, index) => {
      const fileId = fileUploadMap.get(file);
      debugLog(`Starting upload for file ${index + 1}/${validFiles.length}: ${file.name} (${fileId})`);
      
      try {
        // Check if videoApi exists
        if (!videoApi) {
          throw new Error("videoApi is not defined");
        }
        
        if (!videoApi.uploadVideo) {
          throw new Error("videoApi.uploadVideo function is not defined");
        }

        debugLog(`videoApi found, calling uploadVideo for ${file.name}`);
        debugLog(`File details before upload`, {
          name: file.name,
          size: file.size,
          type: file.type,
          lastModified: new Date(file.lastModified).toISOString()
        });

        // Simulate upload progress
        const progressInterval = setInterval(() => {
          setUploadingFiles(prev => {
            if (prev[fileId] && prev[fileId].status === 'uploading') {
              const newProgress = Math.min(prev[fileId].progress + Math.random() * 15, 90);
              return {
                ...prev,
                [fileId]: {
                  ...prev[fileId],
                  progress: newProgress
                }
              };
            }
            return prev;
          });
        }, 300);

        // Upload the file
        debugLog(`Calling videoApi.uploadVideo(${file.name})`);
        const response = await videoApi.uploadVideo(file);
        clearInterval(progressInterval);
        
        debugLog(`Upload response for ${file.name}`, {
          response: response,
          success: response?.success,
          uploads: response?.uploads,
          message: response?.message,
          error: response?.error
        });

        // Fixed condition - check response.success first, then uploads
        if (response.success) {
          // Check if uploads array exists and has content
          if (response.uploads && response.uploads.length > 0) {
            debugLog(`Upload successful for ${file.name}`);
            
            // Mark as completed immediately
            setUploadingFiles(prev => ({
              ...prev,
              [fileId]: {
                ...prev[fileId],
                progress: 100,
                status: 'completed'
              }
            }));

            // Add the new file to the video list using data from response
            const uploadResult = response.uploads[0]; // Get the first (and likely only) upload result
            const newFile: VideoFile = {
              id: `${uploadResult.saved_filename || file.name}-${Date.now()}`,
              name: uploadResult.saved_filename || file.name,
              size: file.size,
              duration: '0:00',
              format: file.name.split('.').pop()?.toUpperCase() || 'MP4',
              resolution: 'Original',
              uploadDate: new Date().toISOString().split('T')[0],
              status: 'ready'
            };

            debugLog(`Adding new file to video list`, newFile);
            setVideoFiles(prev => [newFile, ...prev]);
            
            // Remove from upload tracking after showing completion
            setTimeout(() => {
              debugLog(`Removing ${file.name} from upload tracking`);
              setUploadingFiles(prev => {
                const newState = { ...prev };
                delete newState[fileId];
                return newState;
              });
            }, 2000);
            
          } else {
            // Success but no uploads array - this shouldn't happen but handle it
            debugLog(`Upload marked successful but no uploads array for ${file.name}`, response);
            throw new Error(response.message || 'Upload successful but no file information returned');
          }
        } else {
          // Upload failed
          debugLog(`Upload failed for ${file.name} - backend returned success: false`, response);
          throw new Error(response.message || 'Upload failed - server returned error');
        }
      } catch (error: any) {
        debugLog(`Upload error for ${file.name}`, {
          error: error,
          message: error?.message,
          stack: error?.stack,
          name: error?.name,
          response: error?.response,
          status: error?.response?.status,
          statusText: error?.response?.statusText,
          data: error?.response?.data
        });
        
        // Mark as failed
        setUploadingFiles(prev => ({
          ...prev,
          [fileId]: {
            ...prev[fileId],
            status: 'failed'
          }
        }));
        
        toast({
          title: "Upload Failed",
          description: `${file.name}: ${error.message || "Upload failed"}`,
          variant: "destructive"
        });

        // Remove from tracking after delay
        setTimeout(() => {
          debugLog(`Removing failed upload ${file.name} from tracking`);
          setUploadingFiles(prev => {
            const newState = { ...prev };
            delete newState[fileId];
            return newState;
          });
        }, 3000);
      }
    });

    // Wait for all uploads to complete
    try {
      debugLog(`Waiting for all ${uploadPromises.length} uploads to complete`);
      await Promise.all(uploadPromises);
      debugLog("All uploads completed successfully");
      toast({
        title: "Upload Complete",
        description: `Successfully uploaded ${validFiles.length} file(s)`
      });
    } catch (error) {
      debugLog('Some uploads failed in Promise.all', error);
    }

    // Reset file input
    if (fileInputRef.current) {
      debugLog("Resetting file input");
      fileInputRef.current.value = '';
    }
    
    debugLog("Upload function completed");
  };

  const removeVideo = async (videoId: string) => {
    const video = videoFiles.find(v => v.id === videoId);
    if (!video) {
      debugLog(`Video not found for deletion: ${videoId}`);
      return;
    }

    debugLog(`Attempting to delete video: ${video.name}`, {
      videoId,
      videoName: video.name,
      apiEndpoint: `${import.meta.env.VITE_API_BASE_URL}/delete_video`
    });

    try {
      // Call backend to delete the file
      const response = await videoApi.deleteVideo(video.name);
      
      debugLog(`Delete response for ${video.name}`, {
        response: response,
        success: response?.success,
        message: response?.message,
        error: response?.error,
        deleted_files: response?.deleted_files
      });
      
      if (response.success) {
        // Remove from frontend state only if backend deletion succeeded
        setVideoFiles(videoFiles.filter(v => v.id !== videoId));
        
        debugLog(`Video deleted successfully: ${video.name}`);
        toast({
          title: "Video Removed",
          description: `${video.name} has been deleted from the server.`
        });
      } else {
        throw new Error(response.message || 'Failed to delete video');
      }
    } catch (error: any) {
      debugLog(`Error deleting video: ${video.name}`, {
        error: error,
        message: error?.message,
        status: error?.response?.status,
        statusText: error?.response?.statusText,
        responseData: error?.response?.data
      });
      
      toast({
        title: "Delete Failed", 
        description: error.message || `Failed to delete ${video.name} from the server.`,
        variant: "destructive"
      });
    }
  };

  const triggerFileUpload = () => {
    debugLog("File upload triggered via click");
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
    switch (status) {
      case 'ready':
        return (
          <Badge className="flex items-center gap-1 bg-green-100 text-green-800 border-green-200">
            {getStatusIcon(status)}
            Ready
          </Badge>
        );
      case 'processing':
        return (
          <Badge className="flex items-center gap-1 bg-blue-100 text-blue-800 border-blue-200">
            {getStatusIcon(status)}
            Processing
          </Badge>
        );
      case 'error':
        return (
          <Badge className="flex items-center gap-1 bg-red-100 text-red-800 border-red-200">
            {getStatusIcon(status)}
            Error
          </Badge>
        );
      default:
        return (
          <Badge className="flex items-center gap-1 bg-gray-100 text-gray-800 border-gray-200">
            {getStatusIcon(status)}
            Unknown
          </Badge>
        );
    }
  };

  useEffect(() => {
    debugLog("Component mounted, checking environment");
    debugLog("Current URL", window.location.href);
    
    // Fixed: Use import.meta.env instead of process.env
    const environment = {
      NODE_ENV: import.meta.env.MODE || 'development',
      VITE_API_URL: import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL
    };
    
    debugLog("Environment", environment);
    
    // Check videoApi availability
    debugLog("videoApi inspection", {
      videoApi: videoApi,
      uploadVideo: videoApi?.uploadVideo,
      getVideos: videoApi?.getVideos,
      deleteVideo: videoApi?.deleteVideo,
      apiMethods: videoApi ? Object.keys(videoApi) : 'videoApi is undefined'
    });
    
    // Test basic fetch capability
    debugLog("Testing basic fetch...");
    fetch('/api/test')
      .then(response => {
        debugLog("Fetch test response", {
          status: response.status,
          statusText: response.statusText,
          ok: response.ok,
          url: response.url
        });
        return response.text();
      })
      .then(text => {
        debugLog("Fetch test body", text);
      })
      .catch(error => {
        debugLog("Fetch test failed", error);
      });

    const fetchVideos = async () => {
      setIsLoadingVideos(true);
      try {
        debugLog('Fetching videos from server...');
        
        // Test videoApi.getVideos() 
        if (videoApi?.getVideos) {
          const response = await videoApi.getVideos();
          debugLog("getVideos() response", response);
          
          if (response.success && response.videos) {
            const transformedVideos: VideoFile[] = response.videos.map((video: any) => {
              const fileExtension = video.name.split('.').pop()?.toUpperCase() || 'MP4';
              const videoId = video.id || `${video.name}-${video.size || Date.now()}`;
              
              return {
                id: videoId,
                name: video.name,
                size: video.size || 0,
                duration: video.duration || '0:00',
                format: fileExtension,
                resolution: video.resolution || '1920x1080',
                uploadDate: video.upload_date || new Date().toISOString().split('T')[0],
                status: 'ready' as const
              };
            });
            
            setVideoFiles(transformedVideos);
            debugLog(`Loaded ${transformedVideos.length} videos from server`);
          } else {
            debugLog("No videos found or invalid response", response);
            setVideoFiles([]);
          }
        } else {
          debugLog("videoApi.getVideos is not available");
          setVideoFiles([]);
        }
      } catch (error: any) {
        debugLog('Error fetching videos from server', error);
        toast({
          title: "Loading Error",
          description: "Failed to load video files from server. Please check your connection.",
          variant: "destructive"
        });
        setVideoFiles([]);
      } finally {
        setIsLoadingVideos(false);
      }
    };
    
    fetchVideos();
  }, [toast]);

  const totalSize = videoFiles.reduce((total, file) => total + file.size, 0);
  const readyFiles = videoFiles.filter(v => v.status === 'ready').length;
  const processingFiles = videoFiles.filter(v => v.status === 'processing').length;

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-white border border-gray-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-gray-800 text-lg">Total Files</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-600">{videoFiles.length}</div>
          </CardContent>
        </Card>
        <Card className="bg-white border border-gray-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-gray-800 text-lg">Ready</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{readyFiles}</div>
          </CardContent>
        </Card>
        <Card className="bg-white border border-gray-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-gray-800 text-lg">Processing</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-yellow-600">{processingFiles}</div>
          </CardContent>
        </Card>
        <Card className="bg-white border border-gray-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-gray-800 text-lg">Total Size</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-purple-600">{formatFileSize(totalSize)}</div>
          </CardContent>
        </Card>
      </div>

      {/* Upload Section */}
      <Card className="bg-white border border-gray-200">
        <CardHeader>
          <CardTitle className="text-gray-800 flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Upload Video Files
          </CardTitle>
          <CardDescription className="text-gray-600">
            Upload MP4, AVI, MOV, or MKV files to stream to your displays
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
              <p className="text-gray-500 text-sm">Supported formats: MP4, AVI, MOV, MKV (Max 2GB)</p>
              <input
                ref={fileInputRef}
                type="file"
                name="file"
                accept=".mp4,.avi,.mov,.mkv"
                onChange={handleFileUpload}
                className="hidden"
                multiple
              />
            </div>

            {/* Upload Progress */}
            {Object.keys(uploadingFiles).length > 0 && (
              <div className="space-y-3">
                <div className="text-sm font-medium text-gray-700">
                  Uploading {Object.keys(uploadingFiles).length} file(s):
                </div>
                
                {Object.entries(uploadingFiles).map(([fileId, fileInfo]) => (
                  <div key={fileId} className="space-y-2 p-3 bg-gray-50 rounded-lg border">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FileVideo className="w-4 h-4 text-gray-500" />
                        <span className="text-sm font-medium text-gray-700 truncate max-w-xs">
                          {fileInfo.name}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        {fileInfo.status === 'uploading' && (
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
                    
                    <div className="space-y-1">
                      <Progress 
                        value={fileInfo.progress} 
                        className={`h-2 ${
                          fileInfo.status === 'failed' ? 'bg-red-100' :
                          fileInfo.status === 'completed' ? 'bg-green-100' :
                          fileInfo.status === 'processing' ? 'bg-yellow-100' :
                          'bg-gray-200'
                        }`}
                      />
                      
                      <div className="flex justify-between text-xs text-gray-500">
                        <span>
                          {fileInfo.status === 'uploading' ? 'Uploading...' :
                          fileInfo.status === 'processing' ? 'Processing...' :
                          fileInfo.status === 'completed' ? 'Completed!' :
                          fileInfo.status === 'failed' ? 'Failed' : 'Unknown'}
                        </span>
                        <span>{(fileInfo.size / (1024 * 1024)).toFixed(1)} MB</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Video Library */}
      <Card className="bg-white border border-gray-200">
        <CardHeader>
          <CardTitle className="text-gray-800">Video Library</CardTitle>
          <CardDescription className="text-gray-600">
            All video files stored on the server
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingVideos ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mr-4" />
              <span className="text-gray-600">Loading videos from server...</span>
            </div>
          ) : (
            <div className="space-y-3">
              {videoFiles.map((video) => (
                <div
                  key={video.id}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="flex items-center justify-center w-12 h-12 bg-gray-200 rounded-lg">
                      <FileVideo className="w-6 h-6 text-gray-600" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium text-gray-800">{video.name}</h3>
                        {getStatusBadge(video.status)}
                      </div>
                      <div className="text-sm text-gray-600">
                        {formatFileSize(video.size)} • {video.duration} • {video.format} • {video.resolution}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        Uploaded: {video.uploadDate}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => removeVideo(video.id)}
                      className="border-red-300 text-red-600 hover:bg-red-50 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}

              {videoFiles.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <File className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No video files uploaded yet.</p>
                  <p className="text-sm mt-2">Upload your first video to get started.</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default VideoFilesTab;
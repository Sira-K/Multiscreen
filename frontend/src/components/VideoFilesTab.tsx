import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Upload, Trash2, File, FileVideo, AlertCircle, CheckCircle, RefreshCw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { videoApi } from '@/API/api';

// Type definitions for API responses
interface UploadResponse {
  success?: boolean;
  uploads?: Array<{
    saved_filename: string;
    original_filename: string;
    size: number;
  }>;
  message?: string;
  error?: string;
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

interface DeleteResponse {
  success?: boolean;
  message?: string;
  deleted_files?: string[];
  error?: string;
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
}

const VideoFilesTab = () => {
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadingFiles, setUploadingFiles] = useState<Record<string, UploadingFile>>({});
  const [videoFiles, setVideoFiles] = useState<VideoFile[]>([]);
  const [isLoadingVideos, setIsLoadingVideos] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

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

  const simulateProgress = (fileId: string) => {
    const interval = setInterval(() => {
      setUploadingFiles(prev => {
        const current = prev[fileId];
        if (!current || current.status !== 'uploading') {
          clearInterval(interval);
          return prev;
        }
        
        const increment = Math.random() * 10 + 5; // 5-15% increments
        const newProgress = Math.min(current.progress + increment, 85); // Stop at 85% until real upload completes
        
        return {
          ...prev,
          [fileId]: {
            ...current,
            progress: newProgress
          }
        };
      });
    }, 500);
    
    return interval;
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    console.log(`📁 Starting upload of ${files.length} file(s)`);

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
      toast({
        title: "Some files were skipped",
        description: `Invalid files: ${invalidFiles.join(', ')}`,
        variant: "destructive"
      });
    }

    if (validFiles.length === 0) return;

    // Initialize upload tracking
    const fileUploadMap = new Map<File, string>();
    const initialUploadStates: Record<string, UploadingFile> = {};
    
    validFiles.forEach((file, index) => {
      const fileId = generateFileId(file, index);
      fileUploadMap.set(file, fileId);
      initialUploadStates[fileId] = {
        name: file.name,
        progress: 0,
        status: 'uploading',
        size: file.size
      };
    });

    setUploadingFiles(initialUploadStates);

    toast({
      title: "Upload Started",
      description: `Uploading ${validFiles.length} file(s)...`
    });

    // Upload files concurrently
    const uploadPromises = validFiles.map(async (file) => {
      const fileId = fileUploadMap.get(file)!;
      const progressInterval = simulateProgress(fileId);
      
      try {
        console.log(`⬆️ Uploading ${file.name} (${formatFileSize(file.size)})`);
        
        // Check if videoApi exists
        if (!videoApi?.uploadVideo) {
          throw new Error("Video upload API not available");
        }

        const response = await videoApi.uploadVideo(file) as UploadResponse;
        clearInterval(progressInterval);
        
        console.log(`✅ Upload response for ${file.name}:`, response);

        if (response?.success) {
          // Mark as completed
          setUploadingFiles(prev => ({
            ...prev,
            [fileId]: {
              ...prev[fileId],
              progress: 100,
              status: 'completed'
            }
          }));

          // Create new video file entry
          const uploadResult = response.uploads?.[0];
          if (uploadResult) {
            const newVideo: VideoFile = {
              id: `${uploadResult.saved_filename || file.name}-${Date.now()}`,
              name: uploadResult.saved_filename || file.name,
              size: file.size,
              duration: '0:00',
              format: file.name.split('.').pop()?.toUpperCase() || 'MP4',
              resolution: 'Original',
              uploadDate: new Date().toISOString().split('T')[0],
              status: 'ready'
            };

            setVideoFiles(prev => [newVideo, ...prev]);
          }
          
          // Remove from upload tracking after delay
          setTimeout(() => {
            setUploadingFiles(prev => {
              const newState = { ...prev };
              delete newState[fileId];
              return newState;
            });
          }, 2000);
          
        } else {
          throw new Error(response?.message || 'Upload failed');
        }
      } catch (error: any) {
        clearInterval(progressInterval);
        console.error(`❌ Upload failed for ${file.name}:`, error);
        
        setUploadingFiles(prev => ({
          ...prev,
          [fileId]: {
            ...prev[fileId],
            status: 'failed',
            error: error.message
          }
        }));
        
        toast({
          title: "Upload Failed",
          description: `${file.name}: ${error.message || "Upload failed"}`,
          variant: "destructive"
        });

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

    try {
      await Promise.allSettled(uploadPromises);
      const successCount = validFiles.length - Object.values(uploadingFiles).filter(f => f.status === 'failed').length;
      
      if (successCount > 0) {
        toast({
          title: "Upload Complete",
          description: `Successfully uploaded ${successCount} of ${validFiles.length} file(s)`
        });
      }
    } catch (error) {
      console.error('Upload batch error:', error);
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeVideo = async (videoId: string, videoName: string) => {
    console.log(`🗑️ Attempting to delete video: ${videoName}`);

    try {
      // Create a delete video function if it doesn't exist
      const deleteVideo = async (filename: string): Promise<DeleteResponse> => {
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/delete_video`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ filename }),
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
      };

      const response = await deleteVideo(videoName);
      
      if (response?.success) {
        setVideoFiles(prev => prev.filter(v => v.id !== videoId));
        
        toast({
          title: "Video Removed",
          description: `${videoName} has been deleted.`
        });
      } else {
        throw new Error(response?.message || 'Failed to delete video');
      }
    } catch (error: any) {
      console.error(`❌ Delete failed for ${videoName}:`, error);
      
      toast({
        title: "Delete Failed", 
        description: error.message || `Failed to delete ${videoName}.`,
        variant: "destructive"
      });
    }
  };

  const fetchVideos = async () => {
    try {
      console.log('📋 Fetching videos from server...');
      
      if (!videoApi?.getVideos) {
        console.warn('⚠️ videoApi.getVideos not available');
        setVideoFiles([]);
        return;
      }

      const response = await videoApi.getVideos() as VideosResponse;
      
      // Handle the actual API response structure
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
        console.log(`✅ Loaded ${transformedVideos.length} videos`);
      } else {
        console.log('📭 No videos found or invalid response structure');
        setVideoFiles([]);
      }
    } catch (error: any) {
      console.error('❌ Error fetching videos:', error);
      toast({
        title: "Loading Error",
        description: "Failed to load videos. Please check your connection.",
        variant: "destructive"
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
    const initializeVideos = async () => {
      setIsLoadingVideos(true);
      await fetchVideos();
      setIsLoadingVideos(false);
    };
    
    initializeVideos();
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

            {/* Upload Progress */}
            {activeUploads > 0 && (
              <div className="space-y-3">
                <div className="text-sm font-medium text-gray-700">
                  Uploading {activeUploads} file(s):
                </div>
                
                {Object.entries(uploadingFiles).map(([fileId, fileInfo]) => (
                  <div key={fileId} className="space-y-2 p-3 bg-gray-50 rounded-lg border">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FileVideo className="w-4 h-4 text-gray-500" />
                        <span className="text-sm font-medium truncate max-w-xs">
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
                    
                    <Progress 
                      value={fileInfo.progress} 
                      className="h-2"
                    />
                    
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>
                        {fileInfo.status === 'uploading' ? 'Uploading...' :
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
                        {formatFileSize(video.size)} • {video.duration} • {video.format}
                        {video.resolution && ` • ${video.resolution}`}
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
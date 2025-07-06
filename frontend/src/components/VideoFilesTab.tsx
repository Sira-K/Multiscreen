import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Upload, X, Play, Trash2, File, FileVideo, AlertCircle, CheckCircle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { videoApi } from '@/lib/api';

interface VideoFile {
  id: string;
  name: string;
  size: number;
  duration: string;
  format: string;
  resolution: string;
  uploadDate: string;
  status: 'ready' | 'processing' | 'error';
  thumbnail?: string;
}

const VideoFilesTab = () => {
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [activeUploads, setActiveUploads] = useState<string[]>([]);
  const [uploadingFiles, setUploadingFiles] = useState<Record<string, {
    name: string;
    progress: number;
    status: 'uploading' | 'processing' | 'completed' | 'failed';
    size: number;
  }>>({});
  
  const [videoFiles, setVideoFiles] = useState<VideoFile[]>([]);
  const [isLoadingVideos, setIsLoadingVideos] = useState(true);

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const supportedFormats = ['mp4', 'avi', 'mov', 'mkv'];
    const maxSize = 2 * 1024 * 1024 * 1024; // 2GB
    
    // Validate all files first
    const validFiles: File[] = [];
    const invalidFiles: string[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const fileExtension = file.name.split('.').pop()?.toLowerCase();

      if (!fileExtension || !supportedFormats.includes(fileExtension)) {
        invalidFiles.push(`${file.name} (unsupported format)`);
        continue;
      }

      if (file.size > maxSize) {
        invalidFiles.push(`${file.name} (file too large)`);
        continue;
      }

      validFiles.push(file);
    }

    // Show validation errors if any
    if (invalidFiles.length > 0) {
      toast({
        title: "Some files were skipped",
        description: `Invalid files: ${invalidFiles.join(', ')}`,
        variant: "destructive"
      });
    }

    if (validFiles.length === 0) {
      return;
    }

    // Create unique file IDs for tracking
    const fileUploadMap = new Map();
    validFiles.forEach((file, index) => {
      const fileId = `${file.name}-${Date.now()}-${index}-${Math.random().toString(36).substr(2, 9)}`;
      fileUploadMap.set(file, fileId);
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
    
    setUploadingFiles(initialUploadStates);

    toast({
      title: "Upload Started",
      description: `Uploading ${validFiles.length} file(s)...`
    });

    // Upload all files
    const uploadPromises = validFiles.map(async (file) => {
      const fileId = fileUploadMap.get(file);
      
      try {
        // Simulate upload progress
        const progressInterval = setInterval(() => {
          setUploadingFiles(prev => {
            if (prev[fileId] && prev[fileId].status === 'uploading') {
              return {
                ...prev,
                [fileId]: {
                  ...prev[fileId],
                  progress: Math.min(prev[fileId].progress + Math.random() * 15, 90)
                }
              };
            }
            return prev;
          });
        }, 300);

        // Upload the file
        const response = await videoApi.uploadVideo(file);
        clearInterval(progressInterval);

        if (response.success && response.uploads && response.uploads.length > 0) {
          // Mark as completed immediately
          setUploadingFiles(prev => ({
            ...prev,
            [fileId]: {
              ...prev[fileId],
              progress: 100,
              status: 'completed'
            }
          }));

          // Add the new file to the video list
          const newFile: VideoFile = {
            id: `${file.name}-${Date.now()}`,
            name: file.name,
            size: file.size,
            duration: '0:00',
            format: file.name.split('.').pop()?.toUpperCase() || 'MP4',
            resolution: 'Original',
            uploadDate: new Date().toISOString().split('T')[0],
            status: 'ready'
          };

          setVideoFiles(prev => [newFile, ...prev]);
          
          // Remove from upload tracking after showing completion
          setTimeout(() => {
            setUploadingFiles(prev => {
              const newState = { ...prev };
              delete newState[fileId];
              return newState;
            });
          }, 2000);
          
        } else {
          throw new Error(response.message || 'Upload failed');
        }
      } catch (error: any) {
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
      await Promise.all(uploadPromises);
      toast({
        title: "Upload Complete",
        description: `Successfully uploaded ${validFiles.length} file(s)`
      });
    } catch (error) {
      console.error('Some uploads failed:', error);
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeVideo = async (videoId: string) => {
    const video = videoFiles.find(v => v.id === videoId);
    if (!video) return;

    try {
      // Call backend to delete the file
      const response = await videoApi.deleteVideo(video.name);
      
      if (response.success) {
        // Remove from frontend state only if backend deletion succeeded
        setVideoFiles(videoFiles.filter(v => v.id !== videoId));
        
        toast({
          title: "Video Removed",
          description: `${video.name} has been deleted from the server.`
        });
      } else {
        throw new Error(response.message || 'Failed to delete video');
      }
    } catch (error: any) {
      console.error('Error deleting video:', error);
      toast({
        title: "Delete Failed", 
        description: error.message || `Failed to delete ${video.name} from the server.`,
        variant: "destructive"
      });
    }
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
    const fetchVideos = async () => {
      setIsLoadingVideos(true);
      try {
        console.log('Fetching videos from server...');
        const response = await videoApi.getVideos();
        
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
          console.log(`Loaded ${transformedVideos.length} videos from server`);
        } else {
          setVideoFiles([]);
        }
      } catch (error: any) {
        console.error('Error fetching videos from server:', error);
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
            <CardTitle className="text-gray-800 text-lg">Ready to Stream</CardTitle>
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
                accept=".mp4,.avi,.mov,.mkv"
                onChange={handleFileUpload}
                className="hidden"
                multiple
              />
            </div>

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
          {isLoadingVideos ? (
            <Card className="bg-white border border-gray-200">
              <CardContent className="p-8">
                <div className="flex items-center justify-center">
                  <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mr-4" />
                  <span className="text-gray-600">Loading videos from server...</span>
                </div>
              </CardContent>
            </Card>
          ) : (
            // Your existing video library card
            <Card className="bg-white border border-gray-200">
              <CardHeader>
                <CardTitle className="text-gray-800">Video Library</CardTitle>
                // ... rest of your video library content
              </CardHeader>
            </Card>
          )}
          </div>
        </CardContent>
      </Card>


      {/* Video Files List */}
      <Card className="bg-white border border-gray-200">
        <CardHeader>
          <CardTitle className="text-gray-800">Video Library</CardTitle>
          <CardDescription className="text-gray-600">
            Manage your video files and stream them to connected displays
          </CardDescription>
        </CardHeader>
        <CardContent>
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
                  {video.status === 'ready' && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-gray-300 text-gray-700 hover:bg-gray-100"
                    >
                      <Play className="w-4 h-4 mr-1" />
                      Stream
                    </Button>
                  )}
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
          </div>

          {videoFiles.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <File className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No video files uploaded yet.</p>
              <p className="text-sm mt-2">Upload your first video to get started.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default VideoFilesTab;

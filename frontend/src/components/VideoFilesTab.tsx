
import { useState, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Upload, X, Play, Trash2, File, FileVideo, AlertCircle, CheckCircle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

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
  const [videoFiles, setVideoFiles] = useState<VideoFile[]>([
    {
      id: '1',
      name: 'welcome_video.mp4',
      size: 145830912, // 139 MB
      duration: '2:35',
      format: 'MP4',
      resolution: '1920x1080',
      uploadDate: '2024-01-15',
      status: 'ready'
    },
    {
      id: '2',
      name: 'corporate_presentation.avi',
      size: 523048960, // 498 MB
      duration: '12:45',
      format: 'AVI',
      resolution: '3840x2160',
      uploadDate: '2024-01-14',
      status: 'ready'
    },
    {
      id: '3',
      name: 'advertisement_loop.mov',
      size: 78643200, // 75 MB
      duration: '0:30',
      format: 'MOV',
      resolution: '1920x1080',
      uploadDate: '2024-01-13',
      status: 'processing'
    },
    {
      id: '4',
      name: 'training_material.mkv',
      size: 1073741824, // 1 GB
      duration: '45:20',
      format: 'MKV',
      resolution: '2560x1440',
      uploadDate: '2024-01-12',
      status: 'error'
    }
  ]);

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    const supportedFormats = ['mp4', 'avi', 'mov', 'mkv'];
    const fileExtension = file.name.split('.').pop()?.toLowerCase();

    if (!fileExtension || !supportedFormats.includes(fileExtension)) {
      toast({
        title: "Unsupported Format",
        description: "Please upload MP4, AVI, MOV, or MKV files only.",
        variant: "destructive"
      });
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    // Simulate upload progress
    const interval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsUploading(false);
          
          // Add the new file to the list
          const newFile: VideoFile = {
            id: Date.now().toString(),
            name: file.name,
            size: file.size,
            duration: '0:00', // Would be determined by video processing
            format: fileExtension.toUpperCase(),
            resolution: '1920x1080', // Would be determined by video analysis
            uploadDate: new Date().toISOString().split('T')[0],
            status: 'processing'
          };

          setVideoFiles(prev => [newFile, ...prev]);
          
          toast({
            title: "Upload Complete",
            description: `${file.name} has been uploaded and is being processed.`
          });

          // Simulate processing completion
          setTimeout(() => {
            setVideoFiles(prev => prev.map(vf => 
              vf.id === newFile.id ? { ...vf, status: 'ready' } : vf
            ));
          }, 3000);

          return 100;
        }
        return prev + Math.random() * 15;
      });
    }, 200);

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeVideo = (videoId: string) => {
    const video = videoFiles.find(v => v.id === videoId);
    setVideoFiles(videoFiles.filter(v => v.id !== videoId));
    toast({
      title: "Video Removed",
      description: `${video?.name} has been deleted from the server.`
    });
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
    const statusConfig = {
      ready: { label: 'Ready', className: 'bg-green-600 hover:bg-green-700' },
      processing: { label: 'Processing', className: 'bg-blue-600 hover:bg-blue-700' },
      error: { label: 'Error', className: 'bg-red-600 hover:bg-red-700' }
    };

    const config = statusConfig[status];
    return (
      <Badge className={`flex items-center gap-1 ${config.className}`}>
        {getStatusIcon(status)}
        {config.label}
      </Badge>
    );
  };

  const totalSize = videoFiles.reduce((total, file) => total + file.size, 0);
  const readyFiles = videoFiles.filter(v => v.status === 'ready').length;
  const processingFiles = videoFiles.filter(v => v.status === 'processing').length;

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-slate-200 text-lg">Total Files</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-400">{videoFiles.length}</div>
          </CardContent>
        </Card>
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-slate-200 text-lg">Ready to Stream</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-400">{readyFiles}</div>
          </CardContent>
        </Card>
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-slate-200 text-lg">Processing</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-yellow-400">{processingFiles}</div>
          </CardContent>
        </Card>
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-slate-200 text-lg">Total Size</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-purple-400">{formatFileSize(totalSize)}</div>
          </CardContent>
        </Card>
      </div>

      {/* Upload Section */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-200 flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Upload Video Files
          </CardTitle>
          <CardDescription className="text-slate-400">
            Upload MP4, AVI, MOV, or MKV files to stream to your displays
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div 
              className="border-2 border-dashed border-slate-600 rounded-lg p-8 text-center hover:border-slate-500 transition-colors cursor-pointer"
              onClick={triggerFileUpload}
            >
              <Upload className="w-12 h-12 text-slate-400 mx-auto mb-4" />
              <p className="text-slate-300 mb-2">Click to upload or drag and drop</p>
              <p className="text-slate-500 text-sm">Supported formats: MP4, AVI, MOV, MKV (Max 2GB)</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".mp4,.avi,.mov,.mkv"
                onChange={handleFileUpload}
                className="hidden"
              />
            </div>

            {isUploading && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-300">Uploading...</span>
                  <span className="text-slate-400">{Math.round(uploadProgress)}%</span>
                </div>
                <Progress value={uploadProgress} className="bg-slate-700" />
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Video Files List */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-200">Video Library</CardTitle>
          <CardDescription className="text-slate-400">
            Manage your video files and stream them to connected displays
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {videoFiles.map((video) => (
              <div
                key={video.id}
                className="flex items-center justify-between p-4 bg-slate-700 rounded-lg border border-slate-600 hover:bg-slate-650 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="flex items-center justify-center w-12 h-12 bg-slate-600 rounded-lg">
                    <FileVideo className="w-6 h-6 text-slate-300" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-medium text-slate-200">{video.name}</h3>
                      {getStatusBadge(video.status)}
                    </div>
                    <div className="text-sm text-slate-400">
                      {formatFileSize(video.size)} • {video.duration} • {video.format} • {video.resolution}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      Uploaded: {video.uploadDate}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {video.status === 'ready' && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-slate-600 text-slate-300 hover:bg-slate-600"
                    >
                      <Play className="w-4 h-4 mr-1" />
                      Stream
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => removeVideo(video.id)}
                    className="border-red-600 text-red-400 hover:bg-red-600 hover:text-white"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>

          {videoFiles.length === 0 && (
            <div className="text-center py-8 text-slate-400">
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

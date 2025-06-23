// Updated VideoSelector.tsx
import React from 'react';

interface VideoFile {
  name: string;
  path: string;
  size?: number;
  size_mb?: number;
}

interface VideoSelectorProps {
  availableVideos: VideoFile[];
  fetchVideos: () => Promise<void>;
  onVideoSelect: (videoFile: string) => void;
  selectedVideo: string;
  loading: boolean;
  setOutput?: (message: string) => void;
  showDeleteOption?: boolean;
}

const VideoSelector: React.FC<VideoSelectorProps> = ({
  availableVideos,
  fetchVideos,
  onVideoSelect,
  selectedVideo,
  loading
}) => {
  // Format file size for display
  const formatFileSize = (size?: number) => {
    if (!size) return 'Unknown';
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`;
    return `${(size / (1024 * 1024)).toFixed(2)} MB`;
  };

  // We've removed the useEffect that was fetching videos on mount
  // since this is now handled by the centralized hook

  return (
    <div className="video-selector">
      <h3>Select Video for SRT Stream</h3>
      
      <div className="video-selector-container">
        <select
          value={selectedVideo}
          onChange={(e) => onVideoSelect(e.target.value)}
          disabled={loading}
          className="video-select"
        >
          <option value="">-- Test Pattern --</option>
          {availableVideos.map((video) => (
            <option key={video.name} value={video.name}>
              {video.name} {video.size_mb ? `(${video.size_mb} MB)` : ''}
            </option>
          ))}
        </select>
        
        <button 
          onClick={fetchVideos} 
          disabled={loading}
          className="refresh-button"
        >
          {loading ? 'Loading...' : '↻ Refresh'}
        </button>
      </div>
      
      {selectedVideo ? (
        <div className="selected-video-info">
          <p><strong>Selected Video:</strong> {selectedVideo}</p>
          {availableVideos.find(v => v.name === selectedVideo)?.size && (
            <p><strong>Size:</strong> {formatFileSize(availableVideos.find(v => v.name === selectedVideo)?.size)}</p>
          )}
        </div>
      ) : (
        <div className="selected-video-info">
          <p><strong>Using test pattern</strong> (Default)</p>
        </div>
      )}
      
      {availableVideos.length === 0 && (
        <div className="no-videos-message">
          <p>No videos available. Upload a video file using the File Upload section.</p>
        </div>
      )}
    </div>
  );
};

export default VideoSelector;
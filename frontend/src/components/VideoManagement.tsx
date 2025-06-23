import React, { useState, useEffect } from 'react';

interface VideoFile {
  name: string;
  path: string;
  size?: number;
  size_mb?: number;
}

interface VideoManagementProps {
  setOutput: (message: string) => void;
  onVideosChanged?: () => void;
}

const VideoManagement: React.FC<VideoManagementProps> = ({ setOutput, onVideosChanged }) => {
  const [videos, setVideos] = useState<VideoFile[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null);
  const [showConfirmDelete, setShowConfirmDelete] = useState<string | null>(null);

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

  const fetchVideos = async () => {
    setLoading(true);
    try {
		console.log('Fetching videos from:', `${API_BASE_URL}/get_videos`);
		const response = await fetch(`${API_BASE_URL}/get_videos`);
		console.log('Response status:', response.status);
		const data = await response.json();
		console.log('Response data:', data);
      
      if (data.success) {
        setVideos(data.videos || []);
        setOutput(`Loaded ${data.videos?.length || 0} videos`);
      } else {
        setOutput(`Error loading videos: ${data.message}`);
      }
    } catch (error) {
		console.error('Fetch error:', error);
      	setOutput(`Network error loading videos: ${error}`);
    } finally {
      	setLoading(false);
    }
  };

  const deleteVideo = async (filename: string) => {
    setDeleteLoading(filename);
    try {
      const response = await fetch(`${API_BASE_URL}/delete_video/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      });
      
      const data = await response.json();
      
      if (data.success) {
        setOutput(`Successfully deleted video: ${filename}`);
        await fetchVideos();
        if (onVideosChanged) onVideosChanged();
      } else {
        setOutput(`Error deleting video: ${data.message}`);
      }
    } catch (error) {
      setOutput(`Network error deleting video: ${error}`);
    } finally {
      setDeleteLoading(null);
      setShowConfirmDelete(null);
    }
  };

  
  useEffect(() => {
    fetchVideos();
  }, []);

  return (
    <div className="video-management">
      <div className="video-header">
        <h2>Video Management ({videos.length})</h2>
        <button className="refresh-button" onClick={fetchVideos} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {videos.length === 0 ? (
        <div className="no-videos">
          <p>No videos uploaded yet. Upload a video file using the File Upload section.</p>
        </div>
      ) : (
        <div className="videos-grid">
          {videos.map((video) => (
            <div key={video.name} className="video-card">
              <div className="video-info">
                <h4>{video.name}</h4>
                <span className="file-size">
                  Size: {video.size_mb ? `${video.size_mb} MB` : 'Unknown'}
                </span>
              </div>
              
              <div className="video-actions">
                <button
                  className="download-button"
                  onClick={() => window.open(`${API_BASE_URL}${video.path}`, '_blank')}
                >
                  📥 Download
                </button>
                
                <button
                  className="delete-button"
                  onClick={() => setShowConfirmDelete(video.name)}
                  disabled={deleteLoading === video.name}
                >
                  {deleteLoading === video.name ? '⏳' : '🗑️'} Delete
                </button>
              </div>

              {showConfirmDelete === video.name && (
                <div className="confirm-delete-overlay">
                  <div className="confirm-delete-modal">
                    <h4>Confirm Delete</h4>
                    <p>Are you sure you want to delete <strong>{video.name}</strong>?</p>
                    <div className="modal-buttons">
                      <button onClick={() => setShowConfirmDelete(null)}>Cancel</button>
                      <button onClick={() => deleteVideo(video.name)}>Delete</button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default VideoManagement;
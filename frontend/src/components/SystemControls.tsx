// Updated SystemControls.tsx to match the README architecture
import React, { useState } from 'react';
import VideoSelector from './VideoSelector';

interface VideoFile {
  name: string;
  path: string;
  size?: number;
  size_mb?: number;
}

interface SystemControlsProps {
  setOutput: (msg: string) => void;
  activeButton?: string | null;
  systemStatus: {
    srt: boolean;
    server: boolean;
  };
  handleSystemCommand: (command: string) => Promise<void>;
  availableVideos?: VideoFile[];
  fetchVideos?: () => Promise<void>;
  videoLoading?: boolean;
}

/**
 * SystemControls component 
 * Updated to use the exact Docker and FFmpeg commands from the README
 */
const SystemControls: React.FC<SystemControlsProps> = ({ 
  setOutput, 
  activeButton, 
  systemStatus, 
  handleSystemCommand,
  availableVideos = [],
  fetchVideos = async () => {},
  videoLoading = false
}) => {
  const [selectedVideo, setSelectedVideo] = useState<string>('');
  
  // Function to start Docker SRT Server
  const handleStartDocker = async () => {
    try {
      setOutput("Starting SRT Server Docker container...");
      
      // This will call the backend start_docker endpoint
      // which uses the exact Docker command from the README
      await handleSystemCommand('startServerStream');
      
    } catch (error) {
      console.error('Error starting Docker:', error);
      setOutput(`Failed to start Docker: ${error}`);
    }
  };
  
  // Function to stop Docker SRT Server
  const handleStopDocker = async () => {
    try {
      setOutput("Stopping SRT Server Docker container...");
      
      // This will call the backend stop_docker endpoint
      await handleSystemCommand('stopSystem');
      
    } catch (error) {
      console.error('Error stopping Docker:', error);
      setOutput(`Failed to stop Docker: ${error}`);
    }
  };
  
  // Function to start the SRT stream
  const handleStartSRT = async () => {
    try {
      setOutput(`Starting SRT stream${selectedVideo ? ' with video: ' + selectedVideo : ' with test pattern'}...`);
      
      // Make API call to backend to start SRT with the FFmpeg command from the README
      const apiUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/start_srt`;
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          mp4_file: selectedVideo ? `uploads/${selectedVideo}` : null 
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setOutput(`SRT stream started successfully${selectedVideo ? ' with video: ' + selectedVideo : ' with test pattern'}`);
        // Update system status
        handleSystemCommand('startSrtServer');
      } else {
        const errorData = await response.json();
        setOutput(`Failed to start SRT stream: ${errorData.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error starting SRT:', error);
      setOutput(`Failed to start SRT: ${error}`);
    }
  };
  
  // Function to stop the SRT stream
  const handleStopSRT = async () => {
    try {
      setOutput("Stopping SRT stream...");
      
      const apiUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/stop_srt`;
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setOutput("SRT stream stopped successfully");
        // Update system status
        handleSystemCommand('stopSystem');
      } else {
        const errorData = await response.json();
        setOutput(`Failed to stop SRT stream: ${errorData.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error stopping SRT:', error);
      setOutput(`Failed to stop SRT: ${error}`);
    }
  };
  
  return (
    <div className="system-controls">
      <h3>System Controls</h3>
      
      {/* Video Selector for choosing input source */}
      {fetchVideos && (
        <VideoSelector
            availableVideos={availableVideos}
            fetchVideos={fetchVideos}
            onVideoSelect={setSelectedVideo}
            selectedVideo={selectedVideo}
            loading={videoLoading}
            setOutput={setOutput}
            showDeleteOption={true}
          />
      )}
      
      <div className="controls-grid">
        {/* Docker SRT Server controls */}
        <button 
          onClick={handleStartDocker}
          disabled={activeButton === 'startServerStream' || systemStatus.server}
          className={`control-button ${systemStatus.server ? 'active' : ''}`}
        >
          {activeButton === 'startServerStream' ? 'Starting...' : 'Start SRT Server'}
        </button>
        
        <button 
          onClick={handleStopDocker}
          disabled={activeButton === 'stopSystem' || !systemStatus.server}
          className="control-button"
        >
          {activeButton === 'stopSystem' ? 'Stopping...' : 'Stop SRT Server'}
        </button>
        
        {/* FFmpeg SRT Stream controls */}
        <button 
          onClick={handleStartSRT}
          // disabled={activeButton === 'startSrtServer' || systemStatus.srt || !systemStatus.server}
          className={`control-button ${systemStatus.srt ? 'active' : ''}`}
        >
          {activeButton === 'startSrtServer' ? 'Starting...' : 'Start SRT Stream'}
        </button>
        
        <button 
          onClick={handleStopSRT}
          disabled={activeButton === 'stopSystem' || !systemStatus.srt}
          className="control-button"
        >
          {activeButton === 'stopSystem' ? 'Stopping...' : 'Stop SRT Stream'}
        </button>
      </div>
    </div>
  );
};

export default SystemControls;
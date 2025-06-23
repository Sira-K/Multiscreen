// components/GroupSRTControlPanel.tsx - Dedicated SRT Control Panel for Groups
import React, { useState, useEffect, useCallback } from 'react';

interface Group {
  id: string;
  name: string;
  description: string;
  screen_count: number;
  orientation: 'horizontal' | 'vertical';
  status: 'inactive' | 'starting' | 'active' | 'stopping';
  created_at: number;
  created_at_formatted: string;
  total_clients: number;
  active_clients: number;
  available_streams: string[];
  ports?: {
    srt_port: number;
    rtmp_port: number;
    http_port: number;
    api_port: number;
  };
  docker_container_id?: string;
  ffmpeg_process_id?: number;
  current_video?: string;
}

interface VideoFile {
  name: string;
  path: string;
  size?: number;
  size_mb?: number;
}

interface SRTStatus {
  group_name: string;
  streaming: boolean;
  process_id?: number;
  available_streams: string[];
  current_video?: string;
  ports: any;
  active_clients: number;
  message?: string;
}

interface GroupSRTControlPanelProps {
  setOutput: (message: string) => void;
}

const GroupSRTControlPanel: React.FC<GroupSRTControlPanelProps> = ({ setOutput }) => {
  const [groups, setGroups] = useState<Group[]>([]);
  const [srtStatus, setSrtStatus] = useState<{[key: string]: SRTStatus}>({});
  const [availableVideos, setAvailableVideos] = useState<VideoFile[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [videoLoading, setVideoLoading] = useState<boolean>(false);
  
  // SRT Configuration state for each group
  const [groupConfigs, setGroupConfigs] = useState<{[key: string]: {
    selectedVideo: string;
    enableLooping: boolean;
    loopMode: 'infinite' | 'finite' | 'once';
    loopCount: number;
  }}>({});

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

  /**
   * Fetch groups from the server
   */
  const fetchGroups = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/get_groups`);
      const data = await response.json();
      
      if (response.ok) {
        setGroups(data.groups || []);
        
        // Initialize group configurations
        const newConfigs = { ...groupConfigs };
        data.groups?.forEach((group: Group) => {
          if (!newConfigs[group.id]) {
            newConfigs[group.id] = {
              selectedVideo: '',
              enableLooping: true,
              loopMode: 'infinite',
              loopCount: 5
            };
          }
        });
        setGroupConfigs(newConfigs);
      } else {
        setOutput(`Error fetching groups: ${data.error}`);
      }
    } catch (error) {
      setOutput(`Network error fetching groups: ${error}`);
    }
  }, [API_BASE_URL, setOutput, groupConfigs]);

  /**
   * Fetch SRT status for all groups
   */
  const fetchSRTStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/get_group_srt_status`);
      const data = await response.json();
      
      if (response.ok) {
        setSrtStatus(data.srt_status || {});
      } else {
        console.error('Error fetching SRT status:', data.error);
      }
    } catch (error) {
      console.error('Network error fetching SRT status:', error);
    }
  }, [API_BASE_URL]);

  /**
   * Fetch available videos
   */
  const fetchVideos = useCallback(async () => {
    setVideoLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/get_videos`);
      const data = await response.json();
      
      if (response.ok) {
        setAvailableVideos(data.videos || []);
      } else {
        setOutput(`Error fetching videos: ${data.message}`);
      }
    } catch (error) {
      setOutput(`Network error fetching videos: ${error}`);
    } finally {
      setVideoLoading(false);
    }
  }, [API_BASE_URL, setOutput]);

  /**
   * Start SRT stream for a group
   */
  const startGroupSRT = async (groupId: string, groupName: string) => {
    const config = groupConfigs[groupId];
    if (!config) return;

    try {
      setLoading(true);
      setOutput(`Starting SRT stream for group "${groupName}"...`);
      
      const payload = {
        group_id: groupId,
        video_file: config.selectedVideo || null,
        enable_looping: config.enableLooping,
        loop_count: config.loopMode === 'infinite' ? -1 : 
                   config.loopMode === 'once' ? 0 : config.loopCount
      };
      
      const response = await fetch(`${API_BASE_URL}/start_group_srt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (response.ok) {
        setOutput(`SRT stream started for group "${groupName}"`);
        await fetchGroups();
        await fetchSRTStatus();
      } else {
        setOutput(`Error starting SRT stream: ${data.error}`);
      }
    } catch (error) {
      setOutput(`Network error starting SRT stream: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Stop SRT stream for a group
   */
  const stopGroupSRT = async (groupId: string, groupName: string) => {
    try {
      setLoading(true);
      setOutput(`Stopping SRT stream for group "${groupName}"...`);
      
      const response = await fetch(`${API_BASE_URL}/stop_group_srt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group_id: groupId })
      });

      const data = await response.json();

      if (response.ok) {
        setOutput(`SRT stream stopped for group "${groupName}"`);
        await fetchGroups();
        await fetchSRTStatus();
      } else {
        setOutput(`Error stopping SRT stream: ${data.error}`);
      }
    } catch (error) {
      setOutput(`Network error stopping SRT stream: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Update group configuration
   */
  const updateGroupConfig = (groupId: string, updates: Partial<typeof groupConfigs[string]>) => {
    setGroupConfigs(prev => ({
      ...prev,
      [groupId]: {
        ...prev[groupId],
        ...updates
      }
    }));
  };

  /**
   * Get status badge class
   */
  const getStatusBadgeClass = (isStreaming: boolean, dockerRunning: boolean) => {
    if (isStreaming) return 'status-active';
    if (dockerRunning) return 'status-starting';
    return 'status-inactive';
  };

  /**
   * Get status text
   */
  const getStatusText = (isStreaming: boolean, dockerRunning: boolean) => {
    if (isStreaming) return 'Streaming';
    if (dockerRunning) return 'Ready';
    return 'Stopped';
  };

  /**
   * Format file size
   */
  const formatFileSize = (size?: number) => {
    if (!size) return 'Unknown';
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`;
    return `${(size / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Load data on component mount
  useEffect(() => {
    fetchGroups();
    fetchVideos();
    fetchSRTStatus();
  }, [fetchGroups, fetchVideos, fetchSRTStatus]);

  // Poll SRT status every 10 seconds
  useEffect(() => {
    const interval = setInterval(fetchSRTStatus, 10000);
    return () => clearInterval(interval);
  }, [fetchSRTStatus]);

  return (
    <div className="group-srt-control-panel">
      <div className="panel-header">
        <h2>Group SRT Control Panel</h2>
        <div className="header-controls">
          <button 
            className="refresh-button" 
            onClick={() => {
              fetchGroups();
              fetchVideos();
              fetchSRTStatus();
            }}
            disabled={loading}
          >
            {loading ? 'Refreshing...' : '🔄 Refresh All'}
          </button>
        </div>
      </div>

      {groups.length === 0 ? (
        <div className="no-groups">
          <p>No groups available. Create a group first to control SRT streams.</p>
        </div>
      ) : (
        <div className="srt-groups-grid">
          {groups.map((group) => {
            const status = srtStatus[group.id];
            const config = groupConfigs[group.id] || {
              selectedVideo: '',
              enableLooping: true,
              loopMode: 'infinite' as const,
              loopCount: 5
            };
            const isStreaming = status?.streaming || false;
            const dockerRunning = !!group.docker_container_id;

            return (
              <div key={group.id} className="srt-group-card">
                {/* Group Header */}
                <div className="srt-group-header">
                  <div className="group-info">
                    <h3>{group.name}</h3>
                    <span className={`status-badge ${getStatusBadgeClass(isStreaming, dockerRunning)}`}>
                      {getStatusText(isStreaming, dockerRunning)}
                    </span>
                  </div>
                  <div className="group-stats">
                    <span className="stat">Clients: {group.active_clients}/{group.total_clients}</span>
                    <span className="stat">Port: {group.ports?.srt_port || 10080}</span>
                  </div>
                </div>

                {/* Current Status Info */}
                {status && (
                  <div className="current-status">
                    {status.streaming ? (
                      <div className="streaming-info">
                        <p><strong>🎥 Currently Streaming:</strong> {status.current_video || 'Test Pattern'}</p>
                        <p><strong>📡 Available Streams:</strong> {status.available_streams.length}</p>
                        {status.available_streams.length > 0 && (
                          <div className="streams-list">
                            {status.available_streams.map(stream => (
                              <span key={stream} className="stream-badge">{stream}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="ready-info">
                        <p><strong>Status:</strong> {dockerRunning ? 'Ready to stream' : 'Docker container required'}</p>
                      </div>
                    )}
                  </div>
                )}

                {/* SRT Configuration */}
                {!isStreaming && dockerRunning && (
                  <div className="srt-configuration">
                    <h4>Stream Configuration</h4>
                    
                    {/* Video Selection */}
                    <div className="config-section">
                      <label>Video Source:</label>
                      <select
                        value={config.selectedVideo}
                        onChange={(e) => updateGroupConfig(group.id, { selectedVideo: e.target.value })}
                        disabled={loading}
                      >
                        <option value="">Test Pattern</option>
                        {availableVideos.map((video) => (
                          <option key={video.name} value={video.name}>
                            {video.name} ({formatFileSize(video.size)})
                          </option>
                        ))}
                      </select>
                      <button
                        className="refresh-videos-button"
                        onClick={fetchVideos}
                        disabled={videoLoading}
                        title="Refresh video list"
                      >
                        {videoLoading ? '⏳' : '🔄'}
                      </button>
                    </div>

                    {/* Looping Configuration */}
                    <div className="config-section">
                      <label className="checkbox-label">
                        <input
                          type="checkbox"
                          checked={config.enableLooping}
                          onChange={(e) => updateGroupConfig(group.id, { enableLooping: e.target.checked })}
                          disabled={loading}
                        />
                        Enable Video Looping
                      </label>
                    </div>

                    {config.enableLooping && (
                      <div className="config-section">
                        <label>Loop Mode:</label>
                        <select
                          value={config.loopMode}
                          onChange={(e) => updateGroupConfig(group.id, { loopMode: e.target.value as 'infinite' | 'finite' | 'once' })}
                          disabled={loading}
                        >
                          <option value="infinite">Infinite Loop</option>
                          <option value="finite">Loop Specific Times</option>
                          <option value="once">Play Once</option>
                        </select>

                        {config.loopMode === 'finite' && (
                          <div className="loop-count-config">
                            <label>Loop Count:</label>
                            <input
                              type="number"
                              min="1"
                              max="100"
                              value={config.loopCount}
                              onChange={(e) => updateGroupConfig(group.id, { loopCount: parseInt(e.target.value) || 1 })}
                              disabled={loading}
                            />
                            <span className="loop-explanation">
                              (Total plays: {config.loopCount + 1})
                            </span>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Configuration Summary */}
                    <div className="config-summary">
                      <strong>Configuration:</strong>
                      <ul>
                        <li>Video: {config.selectedVideo || 'Test Pattern'}</li>
                        <li>Layout: {group.orientation} ({group.screen_count} screens)</li>
                        <li>
                          Looping: {
                            !config.enableLooping || config.loopMode === 'once' 
                              ? 'Disabled (plays once)'
                              : config.loopMode === 'infinite' 
                                ? 'Infinite loop'
                                : `${config.loopCount} loops (${config.loopCount + 1} total plays)`
                          }
                        </li>
                      </ul>
                    </div>
                  </div>
                )}

                {/* Control Buttons */}
                <div className="srt-controls">
                  {isStreaming ? (
                    <button
                      className="stop-srt-button danger-button"
                      onClick={() => stopGroupSRT(group.id, group.name)}
                      disabled={loading}
                    >
                      {loading ? 'Stopping...' : '⏹️ Stop SRT Stream'}
                    </button>
                  ) : dockerRunning ? (
                    <button
                      className="start-srt-button success-button"
                      onClick={() => startGroupSRT(group.id, group.name)}
                      disabled={loading}
                    >
                      {loading ? 'Starting...' : '▶️ Start SRT Stream'}
                    </button>
                  ) : (
                    <div className="docker-required">
                      <p>⚠️ Docker container must be running to start SRT stream</p>
                      <p>Go to Group Management to start the Docker container first.</p>
                    </div>
                  )}
                </div>

                {/* Stream URLs for Reference */}
                {isStreaming && status?.available_streams && (
                  <div className="stream-urls">
                    <h5>Stream URLs for Clients:</h5>
                    <div className="urls-list">
                      {status.available_streams.map(stream => {
                        const streamUrl = `srt://${import.meta.env.VITE_SRT_IP || 'SERVER_IP'}:${group.ports?.srt_port || 10080}?streamid=#!::r=${stream},m=request,latency=5000000`;
                        return (
                          <div key={stream} className="url-item">
                            <span className="stream-name">{stream}:</span>
                            <code className="stream-url">{streamUrl}</code>
                            <button
                              className="copy-url-button"
                              onClick={() => {
                                navigator.clipboard.writeText(streamUrl);
                                setOutput(`Stream URL copied to clipboard: ${stream}`);
                              }}
                              title="Copy URL to clipboard"
                            >
                              📋
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default GroupSRTControlPanel;
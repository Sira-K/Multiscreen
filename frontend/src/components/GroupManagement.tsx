// components/GroupManagement.tsx - Enhanced with Video Selectors
import React, { useState, useEffect } from 'react';

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

interface GroupManagementProps {
  setOutput: (message: string) => void;
}

const GroupManagement: React.FC<GroupManagementProps> = ({ setOutput }) => {
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  
  // Create group form state
  const [showCreateForm, setShowCreateForm] = useState<boolean>(false);
  const [newGroupName, setNewGroupName] = useState<string>('');
  const [newGroupDescription, setNewGroupDescription] = useState<string>('');
  const [newGroupScreenCount, setNewGroupScreenCount] = useState<number>(2);
  const [newGroupOrientation, setNewGroupOrientation] = useState<'horizontal' | 'vertical'>('horizontal');
  
  // Edit group state
  const [editingGroup, setEditingGroup] = useState<string | null>(null);
  const [editFormData, setEditFormData] = useState<Partial<Group>>({});

  // NEW: Video management state
  const [availableVideos, setAvailableVideos] = useState<VideoFile[]>([]);
  const [videoLoading, setVideoLoading] = useState<boolean>(false);
  const [groupVideoConfigs, setGroupVideoConfigs] = useState<{[key: string]: {
    selectedVideo: string;
    enableLooping: boolean;
    loopMode: 'infinite' | 'finite' | 'once';
    loopCount: number;
  }}>({});

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

  /**
   * Fetch all groups from the server
   */
  const fetchGroups = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/get_groups`);
      const data = await response.json();
      
      if (response.ok) {
        setGroups(data.groups || []);
        
        // Initialize video configs for new groups
        const newConfigs = { ...groupVideoConfigs };
        data.groups?.forEach((group: Group) => {
          if (!newConfigs[group.id]) {
            newConfigs[group.id] = {
              selectedVideo: group.current_video || '',
              enableLooping: true,
              loopMode: 'infinite',
              loopCount: 5
            };
          }
        });
        setGroupVideoConfigs(newConfigs);
        
        setOutput(`Loaded ${data.groups?.length || 0} groups`);
      } else {
        setOutput(`Error fetching groups: ${data.error}`);
      }
    } catch (error) {
      setOutput(`Network error fetching groups: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  /**
   * NEW: Fetch available videos
   */
  const fetchVideos = async () => {
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
  };

  /**
   * NEW: Update group video configuration
   */
  const updateGroupVideoConfig = (groupId: string, updates: Partial<typeof groupVideoConfigs[string]>) => {
    setGroupVideoConfigs(prev => ({
      ...prev,
      [groupId]: {
        ...prev[groupId],
        ...updates
      }
    }));
  };

  /**
   * Create a new group
   */
  const createGroup = async () => {
    if (!newGroupName.trim()) {
      setOutput('Group name is required');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/create_group`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newGroupName,
          description: newGroupDescription,
          screen_count: newGroupScreenCount,
          orientation: newGroupOrientation
        })
      });

      const data = await response.json();

      if (response.ok) {
        setOutput(`Group "${newGroupName}" created successfully`);
        setShowCreateForm(false);
        resetCreateForm();
        await fetchGroups();
      } else {
        setOutput(`Error creating group: ${data.error}`);
      }
    } catch (error) {
      setOutput(`Network error creating group: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Update an existing group
   */
  const updateGroup = async (groupId: string) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/update_group/${groupId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editFormData)
      });

      const data = await response.json();

      if (response.ok) {
        setOutput(`Group updated successfully`);
        setEditingGroup(null);
        setEditFormData({});
        await fetchGroups();
      } else {
        setOutput(`Error updating group: ${data.error}`);
      }
    } catch (error) {
      setOutput(`Network error updating group: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Delete a group
   */
  const deleteGroup = async (groupId: string, groupName: string) => {
    if (!confirm(`Are you sure you want to delete group "${groupName}"?`)) {
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/delete_group/${groupId}`, {
        method: 'DELETE'
      });

      const data = await response.json();

      if (response.ok) {
        setOutput(`Group "${groupName}" deleted successfully`);
        await fetchGroups();
      } else {
        setOutput(`Error deleting group: ${data.error}`);
      }
    } catch (error) {
      setOutput(`Network error deleting group: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Start Docker container for a group
   */
  const startGroupDocker = async (groupId: string, groupName: string) => {
    try {
      setLoading(true);
      setOutput(`Starting Docker container for group "${groupName}"...`);
      
      const response = await fetch(`${API_BASE_URL}/start_group_docker`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group_id: groupId })
      });

      const data = await response.json();

      if (response.ok) {
        setOutput(`Docker container started for group "${groupName}"`);
        await fetchGroups();
      } else {
        setOutput(`Error starting Docker: ${data.error}`);
      }
    } catch (error) {
      setOutput(`Network error starting Docker: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Stop Docker container for a group
   */
  const stopGroupDocker = async (groupId: string, groupName: string) => {
    try {
      setLoading(true);
      setOutput(`Stopping Docker container for group "${groupName}"...`);
      
      const response = await fetch(`${API_BASE_URL}/stop_group_docker`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group_id: groupId })
      });

      const data = await response.json();

      if (response.ok) {
        setOutput(`Docker container stopped for group "${groupName}"`);
        await fetchGroups();
      } else {
        setOutput(`Error stopping Docker: ${data.error}`);
      }
    } catch (error) {
      setOutput(`Network error stopping Docker: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  /**
   * NEW: Start SRT stream for a group with video configuration
   */
  const startGroupStream = async (groupId: string, groupName: string) => {
    try {
      setLoading(true);
      setOutput(`Starting SRT stream for group "${groupName}"...`);
      
      const config = groupVideoConfigs[groupId] || {
        selectedVideo: '',
        enableLooping: true,
        loopMode: 'infinite',
        loopCount: 5
      };
      
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
  const stopGroupStream = async (groupId: string, groupName: string) => {
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
   * Reset create form
   */
  const resetCreateForm = () => {
    setNewGroupName('');
    setNewGroupDescription('');
    setNewGroupScreenCount(2);
    setNewGroupOrientation('horizontal');
  };

  /**
   * Start editing a group
   */
  const startEditing = (group: Group) => {
    setEditingGroup(group.id);
    setEditFormData({
      name: group.name,
      description: group.description,
      screen_count: group.screen_count,
      orientation: group.orientation
    });
  };

  /**
   * Cancel editing
   */
  const cancelEditing = () => {
    setEditingGroup(null);
    setEditFormData({});
  };

  /**
   * Get status badge color
   */
  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'active': return 'status-active';
      case 'starting': return 'status-starting';
      case 'stopping': return 'status-stopping';
      case 'inactive':
      default: return 'status-inactive';
    }
  };

  /**
   * Check if group can start services
   */
  const canStartServices = (group: Group) => {
    return group.status === 'inactive' && !group.docker_container_id;
  };

  /**
   * Check if group can stop services
   */
  const canStopServices = (group: Group) => {
    return group.status === 'active' || group.docker_container_id || group.ffmpeg_process_id;
  };

  /**
   * NEW: Format file size
   */
  const formatFileSize = (size?: number) => {
    if (!size) return 'Unknown';
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`;
    return `${(size / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Load groups and videos on component mount
  useEffect(() => {
    fetchGroups();
    fetchVideos();
  }, []);

  return (
    <div className="group-management">
      <div className="group-header">
        <h2>Group Management ({groups.length})</h2>
        <div className="header-buttons">
          <button 
            className="create-group-button" 
            onClick={() => setShowCreateForm(true)}
            disabled={loading}
          >
            Create New Group
          </button>
          <button 
            className="refresh-button" 
            onClick={() => {
              fetchGroups();
              fetchVideos();
            }}
            disabled={loading}
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Create Group Form */}
      {showCreateForm && (
        <div className="create-group-form">
          <h3>Create New Group</h3>
          <div className="form-grid">
            <div className="form-field">
              <label>Group Name *</label>
              <input
                type="text"
                value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
                placeholder="Enter group name"
                maxLength={50}
              />
            </div>
            <div className="form-field">
              <label>Description</label>
              <input
                type="text"
                value={newGroupDescription}
                onChange={(e) => setNewGroupDescription(e.target.value)}
                placeholder="Optional description"
                maxLength={200}
              />
            </div>
            <div className="form-field">
              <label>Screen Count</label>
              <select
                value={newGroupScreenCount}
                onChange={(e) => setNewGroupScreenCount(parseInt(e.target.value))}
              >
                <option value={1}>1 Screen</option>
                <option value={2}>2 Screens</option>
                <option value={3}>3 Screens</option>
                <option value={4}>4 Screens</option>
              </select>
            </div>
            <div className="form-field">
              <label>Orientation</label>
              <select
                value={newGroupOrientation}
                onChange={(e) => setNewGroupOrientation(e.target.value as 'horizontal' | 'vertical')}
              >
                <option value="horizontal">Horizontal</option>
                <option value="vertical">Vertical</option>
              </select>
            </div>
          </div>
          <div className="form-buttons">
            <button 
              className="save-button" 
              onClick={createGroup}
              disabled={loading || !newGroupName.trim()}
            >
              Create Group
            </button>
            <button 
              className="cancel-button" 
              onClick={() => {
                setShowCreateForm(false);
                resetCreateForm();
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Groups List */}
      {groups.length === 0 ? (
        <div className="no-groups">
          <p>No groups created yet. Create your first group to manage multiple screen setups.</p>
        </div>
      ) : (
        <div className="groups-grid">
          {groups.map((group) => {
            const config = groupVideoConfigs[group.id] || {
              selectedVideo: '',
              enableLooping: true,
              loopMode: 'infinite' as const,
              loopCount: 5
            };

            return (
              <div key={group.id} className={`group-card ${selectedGroup === group.id ? 'selected' : ''}`}>
                {/* Group Header */}
                <div className="group-card-header">
                  <div className="group-info">
                    {editingGroup === group.id ? (
                      <input
                        type="text"
                        value={editFormData.name || ''}
                        onChange={(e) => setEditFormData({...editFormData, name: e.target.value})}
                        className="edit-name-input"
                      />
                    ) : (
                      <h3>{group.name}</h3>
                    )}
                    <span className={`status-badge ${getStatusBadgeClass(group.status)}`}>
                      {group.status.charAt(0).toUpperCase() + group.status.slice(1)}
                    </span>
                  </div>
                  <div className="group-actions">
                    {editingGroup === group.id ? (
                      <>
                        <button 
                          className="save-edit-button"
                          onClick={() => updateGroup(group.id)}
                          disabled={loading}
                        >
                          Save
                        </button>
                        <button 
                          className="cancel-edit-button"
                          onClick={cancelEditing}
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <>
                        <button 
                          className="edit-button"
                          onClick={() => startEditing(group)}
                          disabled={loading || group.status === 'active'}
                        >
                          ✏️
                        </button>
                        <button 
                          className="delete-button"
                          onClick={() => deleteGroup(group.id, group.name)}
                          disabled={loading || group.status === 'active'}
                        >
                          🗑️
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Group Details */}
                <div className="group-details">
                  {editingGroup === group.id ? (
                    <div className="edit-form">
                      <div className="form-field">
                        <label>Description</label>
                        <input
                          type="text"
                          value={editFormData.description || ''}
                          onChange={(e) => setEditFormData({...editFormData, description: e.target.value})}
                        />
                      </div>
                      <div className="form-field">
                        <label>Screen Count</label>
                        <select
                          value={editFormData.screen_count || 2}
                          onChange={(e) => setEditFormData({...editFormData, screen_count: parseInt(e.target.value)})}
                        >
                          <option value={1}>1 Screen</option>
                          <option value={2}>2 Screens</option>
                          <option value={3}>3 Screens</option>
                          <option value={4}>4 Screens</option>
                        </select>
                      </div>
                      <div className="form-field">
                        <label>Orientation</label>
                        <select
                          value={editFormData.orientation || 'horizontal'}
                          onChange={(e) => setEditFormData({...editFormData, orientation: e.target.value as 'horizontal' | 'vertical'})}
                        >
                          <option value="horizontal">Horizontal</option>
                          <option value="vertical">Vertical</option>
                        </select>
                      </div>
                    </div>
                  ) : (
                    <>
                      <p className="group-description">{group.description || 'No description'}</p>
                      
                      <div className="group-stats">
                        <div className="stat">
                          <strong>Screens:</strong> {group.screen_count} ({group.orientation})
                        </div>
                        <div className="stat">
                          <strong>Clients:</strong> {group.active_clients}/{group.total_clients}
                        </div>
                        <div className="stat">
                          <strong>Created:</strong> {group.created_at_formatted}
                        </div>
                      </div>

                      {/* Port Information */}
                      {group.ports && (
                        <div className="port-info">
                          <strong>Ports:</strong> SRT: {group.ports.srt_port}, API: {group.ports.api_port}
                        </div>
                      )}

                      {/* NEW: Video Configuration Section */}
                      {group.docker_container_id && !group.ffmpeg_process_id && (
                        <div className="video-config-section">
                          <h4>🎥 Video Configuration</h4>
                          
                          {/* Video Selection */}
                          <div className="video-selector">
                            <label>Video Source:</label>
                            <div className="video-selector-row">
                              <select
                                value={config.selectedVideo}
                                onChange={(e) => updateGroupVideoConfig(group.id, { selectedVideo: e.target.value })}
                                disabled={loading}
                                className="video-select"
                              >
                                <option value="">Test Pattern</option>
                                {availableVideos.map((video) => (
                                  <option key={video.name} value={video.name}>
                                    {video.name} ({formatFileSize(video.size)})
                                  </option>
                                ))}
                              </select>
                              <button
                                className="refresh-videos-btn"
                                onClick={fetchVideos}
                                disabled={videoLoading}
                                title="Refresh video list"
                              >
                                {videoLoading ? '⏳' : '🔄'}
                              </button>
                            </div>
                          </div>

                          {/* Looping Configuration */}
                          <div className="looping-config">
                            <label className="checkbox-label">
                              <input
                                type="checkbox"
                                checked={config.enableLooping}
                                onChange={(e) => updateGroupVideoConfig(group.id, { enableLooping: e.target.checked })}
                                disabled={loading}
                              />
                              Enable Video Looping
                            </label>

                            {config.enableLooping && (
                              <div className="loop-options">
                                <select
                                  value={config.loopMode}
                                  onChange={(e) => updateGroupVideoConfig(group.id, { loopMode: e.target.value as 'infinite' | 'finite' | 'once' })}
                                  disabled={loading}
                                  className="loop-mode-select"
                                >
                                  <option value="infinite">Infinite Loop</option>
                                  <option value="finite">Loop Specific Times</option>
                                  <option value="once">Play Once</option>
                                </select>

                                {config.loopMode === 'finite' && (
                                  <div className="loop-count-input">
                                    <input
                                      type="number"
                                      min="1"
                                      max="100"
                                      value={config.loopCount}
                                      onChange={(e) => updateGroupVideoConfig(group.id, { loopCount: parseInt(e.target.value) || 1 })}
                                      disabled={loading}
                                    />
                                    <span>loops</span>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>

                          {/* Configuration Summary */}
                          <div className="config-preview">
                            <strong>Will stream:</strong> {config.selectedVideo || 'Test Pattern'} 
                            {config.enableLooping && config.loopMode === 'infinite' && ' (infinite loop)'}
                            {config.enableLooping && config.loopMode === 'finite' && ` (${config.loopCount} loops)`}
                            {(!config.enableLooping || config.loopMode === 'once') && ' (play once)'}
                          </div>
                        </div>
                      )}

                      {/* Available Streams */}
                      {group.available_streams && group.available_streams.length > 0 && (
                        <div className="streams-info">
                          <strong>Available Streams:</strong>
                          <div className="streams-list">
                            {group.available_streams.map(stream => (
                              <span key={stream} className="stream-tag">{stream}</span>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>

                {/* Service Controls */}
                {editingGroup !== group.id && (
                  <div className="service-controls">
                    <div className="control-row">
                      <span className="service-label">Docker Container:</span>
                      <div className="service-buttons">
                        <button
                          className="start-service-button"
                          onClick={() => startGroupDocker(group.id, group.name)}
                          disabled={loading || !!group.docker_container_id}
                        >
                          Start Docker
                        </button>
                        <button
                          className="stop-service-button"
                          onClick={() => stopGroupDocker(group.id, group.name)}
                          disabled={loading || !group.docker_container_id}
                        >
                          Stop Docker
                        </button>
                      </div>
                    </div>
                    
                    <div className="control-row">
                      <span className="service-label">SRT Stream:</span>
                      <div className="service-buttons">
                        <button
                          className="start-service-button"
                          onClick={() => startGroupStream(group.id, group.name)}
                          disabled={loading || !!group.ffmpeg_process_id || !group.docker_container_id}
                        >
                          Start Stream
                        </button>
                        <button
                          className="stop-service-button"
                          onClick={() => stopGroupStream(group.id, group.name)}
                          disabled={loading || !group.ffmpeg_process_id}
                        >
                          Stop Stream
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Click to select group */}
                <div 
                  className="group-select-overlay"
                  onClick={() => setSelectedGroup(selectedGroup === group.id ? null : group.id)}
                >
                  {selectedGroup === group.id && <div className="selected-indicator">Selected</div>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default GroupManagement;
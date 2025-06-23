// SRTControlPanel.tsx - Updated without System Controls Tab
import React, { useState, useEffect, useCallback, useRef } from 'react';
import StatusDisplay from './components/StatusDisplay';
import FileUploadSection from './components/FileUpload';
import ClientManagement from './components/ClientManagement';
import GroupManagement from './components/GroupManagement';
import VideoManagement from './components/VideoManagement';
import './index.css';

// ===== TYPE DEFINITIONS =====
interface ClientInfo {
  id: string;
  ip: string;
  hostname: string;
  status: 'active' | 'inactive';
  stream_id: string | null;
  group_id: string | null;
  group_name: string | null;
  group_status: string | null;
  srt_port: number;
  display_name?: string | null;
  mac_address?: string;
  platform?: string;
  last_seen: number;
  last_seen_formatted: string;
  time_since_seen?: number;
}

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

interface StreamSettings {
  resolution: string;
  framerate: number;
  seiUuid: string;
}

interface SystemStatus {
  srt: boolean;
  server: boolean;
}

// ===== MAIN COMPONENT =====
const SRTControlPanel: React.FC = () => {
  // ===== STATE MANAGEMENT =====
  
  // Basic UI state - removed 'system' from the type
  const [output, setOutput] = useState<string>('SRT Control Panel initialized...');
  const [currentView, setCurrentView] = useState<'groups' | 'clients' | 'videos'>('groups');
  const [lastError, setLastError] = useState<string | null>(null);
  
  // Video management
  const [availableVideos, setAvailableVideos] = useState<VideoFile[]>([]);
  const [videoLoading, setVideoLoading] = useState<boolean>(false);
  
  // Group management
  const [groups, setGroups] = useState<Group[]>([]);
  const [groupsLoading, setGroupsLoading] = useState<boolean>(false);
  const [selectedGroupFilter, setSelectedGroupFilter] = useState<string | null>(null);
  
  // Client management
  const [clients, setClients] = useState<ClientInfo[]>([]);
  const [availableStreams, setAvailableStreams] = useState<string[]>([]);
  const [streamingMode, setStreamingMode] = useState<string>('');
  const [splitCount, setSplitCount] = useState<number>(0);
  const [clientsLoading, setClientsLoading] = useState<boolean>(false);
  const [lastFetchTime, setLastFetchTime] = useState<number>(0);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState<boolean>(true);
  
  // System state (kept for internal use but no longer exposed as a tab)
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    srt: false,
    server: false
  });
  const [activeButton, setActiveButton] = useState<string | null>(null);
  
  // Stream settings
  const [streamSettings, setStreamSettings] = useState<StreamSettings>({
    resolution: '3840x1080',
    framerate: 30,
    seiUuid: 'unique-uuid-here'
  });
  


  // ===== REFS =====
  const mountedRef = useRef<boolean>(true);
  const lastFetchRef = useRef<number>(0);
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isRequestInProgress = useRef<boolean>(false);
  
  // ===== CONSTANTS =====
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';
  const defaultStreams = ['test', 'test1', 'test2', 'test3'];
  
  // Timing constants - much slower to reduce API calls
  const AUTO_REFRESH_INTERVAL = 60 * 1000; // 5 minutes instead of 1 minute
  const MIN_FETCH_INTERVAL = 2 * 60 * 1000;    // 2 minutes minimum between calls
  const DEBOUNCE_INTERVAL = 10 * 1000;         // 10 seconds for manual operations
  
  // ===== LIFECYCLE =====  
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);
  
  // ===== API FUNCTIONS =====
  
  const apiCall = useCallback(async <T,>(
    url: string,
    options: RequestInit = {}
  ): Promise<T> => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000);

      const response = await fetch(`${API_BASE_URL}${url}`, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!mountedRef.current) {
        throw new Error('Component unmounted');
      }

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API Error: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      setLastError(null);
      return data;
    } catch (error) {
      if (!mountedRef.current) {
        return Promise.reject(new Error('Component unmounted'));
      }
      
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setLastError(errorMessage);
      
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      
      throw error;
    }
  }, [API_BASE_URL]);

  // ===== DATA FETCHING =====
  
  const fetchVideos = useCallback(async () => {
    const now = Date.now();
    if (now - lastFetchRef.current < 2000) return;
    lastFetchRef.current = now;

    setVideoLoading(true);
    try {
      const data = await apiCall<{videos: VideoFile[]}>('/get_videos');
      if (mountedRef.current) {
        setAvailableVideos(data.videos || []);
      }
    } catch (error) {
      console.error('Error fetching videos:', error);
      if (mountedRef.current) {
        setOutput(`Error fetching videos: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    } finally {
      if (mountedRef.current) {
        setVideoLoading(false);
      }
    }
  }, [apiCall]);

  const fetchGroups = useCallback(async () => {
    if (groupsLoading) return;
    
    setGroupsLoading(true);
    try {
      const data = await apiCall<{groups: Group[]}>('/get_groups');
      if (mountedRef.current) {
        setGroups(data.groups || []);
      }
    } catch (error) {
      console.error('Error fetching groups:', error);
      if (mountedRef.current) {
        setOutput(`Error fetching groups: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    } finally {
      if (mountedRef.current) {
        setGroupsLoading(false);
      }
    }
  }, [apiCall, groupsLoading]);

  const fetchClients = useCallback(async (forceRefresh: boolean = false) => {
    // Prevent multiple simultaneous requests
    if (isRequestInProgress.current && !forceRefresh) {
      console.log('Skipping client fetch - request already in progress');
      return;
    }

    // Respect minimum fetch interval unless forced
    const timeSinceLastFetch = Date.now() - lastFetchTime;
    if (!forceRefresh && timeSinceLastFetch < MIN_FETCH_INTERVAL) {
      console.log(`Skipping client fetch - only ${Math.floor(timeSinceLastFetch/1000)}s since last fetch (min: ${MIN_FETCH_INTERVAL/1000}s)`);
      return;
    }

    if (!mountedRef.current) return;

    try {
      isRequestInProgress.current = true;
      setClientsLoading(true);
      
      console.log('Fetching clients from API...');
      const data = await apiCall<{
        clients: ClientInfo[];
        available_streams?: string[];
        streaming_mode?: string;
        split_count?: number;
      }>('/get_clients');
      
      if (!mountedRef.current) return;
      
      setClients(data.clients || []);
      
      if (data.available_streams) {
        const cleanStreams = data.available_streams.map(s => s.replace('live/', ''));
        setAvailableStreams(cleanStreams);
      }
      
      if (data.streaming_mode) setStreamingMode(data.streaming_mode);
      if (typeof data.split_count === 'number') setSplitCount(data.split_count);
      
      setLastFetchTime(Date.now());
      
      if (forceRefresh) {
        setOutput(`Manual refresh: ${data.clients.length} clients found`);
      } else {
        console.log(`Auto refresh: ${data.clients.length} clients found`);
      }
      
    } catch (error) {
      if (!mountedRef.current) return;
      
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setOutput(`Error fetching clients: ${errorMessage}`);
      console.error('Fetch clients error:', error);
    } finally {
      if (mountedRef.current) {
        setClientsLoading(false);
        isRequestInProgress.current = false;
      }
    }
  }, [apiCall, lastFetchTime, MIN_FETCH_INTERVAL]);

  // ===== CLIENT ACTIONS =====
  
  // Debounced refresh to prevent too many calls after operations
  const debouncedRefresh = useCallback(async () => {
    const timeSinceLastFetch = Date.now() - lastFetchTime;
    if (timeSinceLastFetch < DEBOUNCE_INTERVAL) {
      console.log('Skipping refresh after operation - too soon since last fetch');
      return;
    }
    await fetchClients(true);
  }, [fetchClients, lastFetchTime, DEBOUNCE_INTERVAL]);
  
  const assignStreamToClient = useCallback(async (clientId: string, streamId: string) => {
    try {
      await apiCall('/assign_stream', {
        method: 'POST',
        body: JSON.stringify({ client_id: clientId, stream_id: streamId })
      });
      
      // Only refresh if enough time has passed
      await debouncedRefresh();
      setOutput(`Stream assigned to client successfully`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setOutput(`Error assigning stream: ${errorMessage}`);
      throw error;
    }
  }, [apiCall, debouncedRefresh]);

  const assignClientToGroup = useCallback(async (clientId: string, groupId: string | null) => {
    try {
      await apiCall('/assign_client_to_group', {
        method: 'POST',
        body: JSON.stringify({ client_id: clientId, group_id: groupId })
      });
      
      // Refresh groups immediately but debounce client refresh
      await fetchGroups();
      await debouncedRefresh();
      setOutput(`Client assigned to group successfully`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setOutput(`Error assigning client to group: ${errorMessage}`);
      throw error;
    }
  }, [apiCall, fetchGroups, debouncedRefresh]);

  const renameClient = useCallback(async (clientId: string, newName: string) => {
    try {
      await apiCall('/rename_client', {
        method: 'POST',
        body: JSON.stringify({ client_id: clientId, new_name: newName })
      });
      
      // Only refresh if enough time has passed
      await debouncedRefresh();
      setOutput(`Client renamed to "${newName}" successfully`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setOutput(`Error renaming client: ${errorMessage}`);
      throw error;
    }
  }, [apiCall, debouncedRefresh]);

  const removeClient = useCallback(async (clientId: string) => {
    try {
      await apiCall('/remove_client', {
        method: 'POST',
        body: JSON.stringify({ client_id: clientId })
      });
      
      // Refresh data after removal
      await debouncedRefresh();
      await fetchGroups();
      setOutput(`Client removed successfully`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setOutput(`Error removing client: ${errorMessage}`);
      throw error;
    }
  }, [apiCall, debouncedRefresh, fetchGroups]);

  // ===== STREAM SETTINGS =====
  
  const updateSetting = useCallback((setting: keyof StreamSettings, value: string | number) => {
    setStreamSettings(prev => ({ ...prev, [setting]: value }));
  }, []);

  const handleFileUpload = useCallback(async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`${API_BASE_URL}/upload_video`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        updateSetting('resolution', data.resolution);
        updateSetting('framerate', data.framerate);
        await fetchVideos();
        setOutput(`Video uploaded successfully: ${file.name}`);
      } else {
        setOutput(`Upload failed: ${data.error}`);
      }
    } catch (error) {
      setOutput(`Upload error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }, [API_BASE_URL, updateSetting, fetchVideos]);

  
  // ===== AUTO REFRESH =====
  
  const toggleAutoRefresh = useCallback(() => {
    setAutoRefreshEnabled(prev => !prev);
  }, []);

  const getTimeSinceLastFetch = useCallback(() => {
    if (lastFetchTime === 0) return 'Never';
    const seconds = Math.floor((Date.now() - lastFetchTime) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m ${seconds % 60}s ago`;
  }, [lastFetchTime]);

  // Auto-refresh setup with much slower interval
  useEffect(() => {
    if (!autoRefreshEnabled || !mountedRef.current) {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      return;
    }

    // Only fetch on initial setup, not every time auto-refresh changes
    if (lastFetchTime === 0) {
      console.log('Initial client fetch on auto-refresh setup');
      fetchClients();
    }
    
    pollingIntervalRef.current = setInterval(() => {
      if (autoRefreshEnabled && !isRequestInProgress.current && mountedRef.current) {
        console.log('Auto-refresh interval triggered');
        fetchClients();
      }
    }, AUTO_REFRESH_INTERVAL); // Now 5 minutes instead of 1 minute
    
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [autoRefreshEnabled]); // Removed fetchClients from dependencies to prevent restarts

  // ===== INITIALIZATION =====
  
  useEffect(() => {
    const initializeData = async () => {
      if (!mountedRef.current) return;
      
      try {
        console.log('Initializing data on component mount');
        // Stagger the initial calls to reduce server load
        await fetchVideos();
        await new Promise(resolve => setTimeout(resolve, 1000)); // 1 second delay
        await fetchGroups();
        await new Promise(resolve => setTimeout(resolve, 1000)); // 1 second delay
        await fetchClients(true); // Force initial fetch
      } catch (error) {
        console.error('Initialization error:', error);
        setOutput('Warning: Some data failed to load');
      }
    };

    initializeData();
  }, []); // Only run once on mount

  // ===== COMPUTED VALUES =====
  
  const allStreams = availableStreams.length > 0 ? availableStreams : defaultStreams;
  
  const filteredClients = selectedGroupFilter 
    ? clients.filter(client => client.group_id === selectedGroupFilter)
    : clients;
  
  const activeGroups = groups.filter(group => group.status === 'active');
  const activeClients = clients.filter(client => client.status === 'active');

  // ===== ERROR DISPLAY =====
  
  const ErrorDisplay = lastError ? (
    <div style={{
      padding: '10px',
      margin: '10px 0',
      backgroundColor: '#f8d7da',
      border: '1px solid #f5c6cb',
      borderRadius: '4px',
      color: '#721c24'
    }}>
      <strong>Connection Issue:</strong> {lastError}
      <button 
        onClick={() => setLastError(null)}
        style={{
          float: 'right',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: '0 5px',
          fontSize: '16px'
        }}
      >
        ✕
      </button>
    </div>
  ) : null;

  // ===== RENDER =====
  
  return (
    <div className="srt-control-panel">
      {ErrorDisplay}
      
      {/* Navigation Tabs - Removed System Controls */}
      <div className="navigation-tabs">
        <button 
          className={`nav-tab ${currentView === 'groups' ? 'active' : ''}`}
          onClick={() => setCurrentView('groups')}
        >
          <span className="tab-icon">📊</span>
          <span className="tab-label">Group Management</span>
          <span className="client-count-badge">{groups.length}</span>
        </button>
        <button 
          className={`nav-tab ${currentView === 'clients' ? 'active' : ''}`}
          onClick={() => setCurrentView('clients')}
        >
          <span className="tab-icon">👥</span>
          <span className="tab-label">Client Management</span>
          <span className="client-count-badge">{clients.length}</span>
        </button>
        <button 
          className={`nav-tab ${currentView === 'videos' ? 'active' : ''}`}
          onClick={() => setCurrentView('videos')}
        >
          <span className="tab-icon">🎥</span>
          <span className="tab-label">Video Management</span>
          <span className="client-count-badge">{availableVideos.length}</span>
        </button>
      </div>

      {/* Tab Content Container */}
      <div className="tab-content-container">
        <div className="tab-content">
          {/* Groups View */}
          {currentView === 'groups' && (
            <GroupManagement setOutput={setOutput} />
          )}

          {/* Clients View */}
          {currentView === 'clients' && (
            <>
              <div className="client-management-section">
                <div className="section-header">
                  <div className="section-info">
                    <h3>Client Management</h3>
                    {selectedGroupFilter && (
                      <span className="filter-info">
                        Filtered by: {groups.find(g => g.id === selectedGroupFilter)?.name || 'Unknown Group'}
                      </span>
                    )}
                  </div>
                  <div className="refresh-controls">
                    <span className="refresh-status">
                      Auto-refresh: {autoRefreshEnabled ? '✅ On (5min)' : '❌ Off'}
                    </span>
                    <button 
                      className="toggle-refresh-button"
                      onClick={toggleAutoRefresh}
                      title={`${autoRefreshEnabled ? 'Disable' : 'Enable'} auto-refresh (5 minute interval)`}
                    >
                      {autoRefreshEnabled ? '⏸️ Pause' : '▶️ Resume'}
                    </button>
                    <button 
                      onClick={() => fetchClients(true)}
                      disabled={clientsLoading}
                      title="Manual refresh (bypasses 2-minute minimum)"
                      style={{
                        padding: '6px 12px',
                        fontSize: '12px',
                        backgroundColor: '#28a745',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: clientsLoading ? 'not-allowed' : 'pointer'
                      }}
                    >
                      {clientsLoading ? '🔄' : '🔄 Refresh Now'}
                    </button>
                    <span className="last-fetch">
                      Last updated: {getTimeSinceLastFetch()}
                    </span>
                  </div>
                </div>
                
                {streamingMode && (
                  <div className="streaming-status">
                    <span className="streaming-mode">Mode: {streamingMode}</span>
                    <span className="split-info">
                      {splitCount > 0 ? `${splitCount} video sections` : 'Full video only'}
                    </span>
                  </div>
                )}
              </div>
             
              <ClientManagement
                clients={filteredClients}
                groups={groups}
                availableStreams={allStreams}
                assignStreamToClient={assignStreamToClient}
                assignClientToGroup={assignClientToGroup}
                renameClient={renameClient}
                removeClient={removeClient}  // Add this new prop
                fetchClients={() => fetchClients(true)}
                fetchGroups={fetchGroups}
                loading={clientsLoading || groupsLoading}
                setOutput={setOutput}
                selectedGroupFilter={selectedGroupFilter}
                onGroupFilterChange={setSelectedGroupFilter}
              />
            </>
          )}
        
          {/* Videos View - Now includes File Upload */}
          {currentView === 'videos' && (
            <>
              <VideoManagement
                setOutput={setOutput}
                onVideosChanged={fetchVideos}
              />
              
              <FileUploadSection
                setOutput={setOutput}
                onUploadComplete={fetchVideos}
              />
            </>
          )}
        </div>
      </div>

      {/* Always Visible Components */}
      
      <StatusDisplay
        output={output}
        streamSettings={streamSettings}
        updateSetting={updateSetting}
        setOutput={setOutput}
        handleFileUpload={handleFileUpload}
      />

      {/* Quick Stats Panel */}
      <div className="quick-stats">
        <div className="stats-grid">
          <div className="stat-card">
            <h4>Groups</h4>
            <div className="stat-value">{groups.length}</div>
            <div className="stat-label">Total Groups</div>
          </div>
          <div className="stat-card">
            <h4>Active Groups</h4>
            <div className="stat-value">{activeGroups.length}</div>
            <div className="stat-label">Running</div>
          </div>
          <div className="stat-card">
            <h4>Clients</h4>
            <div className="stat-value">{clients.length}</div>
            <div className="stat-label">Total Clients</div>
          </div>
          <div className="stat-card">
            <h4>Active Clients</h4>
            <div className="stat-value">{activeClients.length}</div>
            <div className="stat-label">Connected</div>
          </div>
          <div className="stat-card">
            <h4>Videos</h4>
            <div className="stat-value">{availableVideos.length}</div>
            <div className="stat-label">Available</div>
          </div>
        </div>
      </div>

      {/* Global Status Bar */}
      <div className="global-status-bar">
        <div className="status-item">
          <span className="status-label">Groups:</span>
          <span className={`status-value ${activeGroups.length > 0 ? 'active' : 'inactive'}`}>
            {activeGroups.length}/{groups.length}
          </span>
        </div>
        <div className="status-item">
          <span className="status-label">Clients:</span>
          <span className={`status-value ${activeClients.length > 0 ? 'active' : 'inactive'}`}>
            {activeClients.length}/{clients.length}
          </span>
        </div>
        <div className="status-item">
          <span className="status-label">Videos:</span>
          <span className="status-value">{availableVideos.length}</span>
        </div>
        <div className="status-item">
          <span className="status-label">Auto-refresh:</span>
          <span className={`status-value ${autoRefreshEnabled ? 'active' : 'inactive'}`}>
            {autoRefreshEnabled ? 'ON' : 'OFF'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default SRTControlPanel;
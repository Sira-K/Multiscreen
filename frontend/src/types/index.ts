// frontend/src/types/index.ts - Updated with complete unified Client interface

// Group interface updated for Docker discovery
export interface Group {
  id: string;
  name: string;
  description?: string;
  screen_count: number;
  orientation: 'horizontal' | 'vertical' | 'grid';
  streaming_mode?: 'multi_video' | 'single_video_split'; // NEW: streaming mode
  
  // Docker-related fields (from Docker discovery)
  docker_running?: boolean;
  docker_status?: 'running' | 'stopped' | 'starting' | 'stopping';
  container_id?: string;
  container_name?: string;
  
  // Ports from Docker container
  ports?: {
    rtmp_port: number;
    http_port: number;
    api_port: number;
    srt_port: number;
  };
  
  // Status for frontend (derived from docker_running)
  status: 'active' | 'inactive' | 'starting' | 'stopping';
  
  // Stream-related (populated separately from stream management)
  available_streams?: string[];
  current_video?: string;
  streaming_active?: boolean;  // Whether FFmpeg is running
  ffmpeg_process_id?: number | null;
  
  // Client counts (calculated from client data)
  active_clients?: number;
  total_clients?: number;
  srt_port?: number;
  
  // Timestamps
  created_at?: number;
  created_at_formatted?: string;
}

// UNIFIED Client interface - combines all requirements
export interface Client {
  // Required fields
  id: string;                    // For frontend compatibility
  client_id: string;             // Primary identifier
  hostname: string;
  ip_address: string;            // Changed from 'ip' to 'ip_address' to match backend
  
  // Optional display info
  display_name?: string;
  platform?: string;
  
  // Connection status (from app state)
  is_active: boolean;
  status: 'active' | 'inactive';
  last_seen: number;
  seconds_ago?: number;
  last_seen_formatted?: string;
  
  // Group assignment (references Docker groups)
  group_id?: string | null;
  group_name?: string | null;
  group_docker_running?: boolean;
  group_docker_status?: string;
  
  // Stream assignment
  stream_assignment?: string | null;  // Backend uses this
  stream_id?: string | null;          // Frontend might expect this (alias)
  stream_url?: string | null;
  screen_number?: number;             // NEW: for screen assignments
  
  // Timestamps
  registered_at?: number;
  assigned_at?: number;
  
  // Legacy/compatibility fields
  order?: number;                     // For ClientsTab ordering
}

// Video interface (unchanged)
export interface Video {
  name: string;
  path: string;
  size_mb: number;
  duration?: number;
  resolution?: string;
  created_at?: string;
}

// System status updated for hybrid architecture
export interface SystemStatus {
  timestamp: number;
  architecture: 'hybrid_docker_discovery';
  
  groups: {
    total: number;
    active: number;  // Docker containers running
    docker_containers: number;
    streaming_active?: number;  // FFmpeg processes running
  };
  
  clients: {
    total: number;
    active: number;
  };
  
  docker?: {
    available: boolean;
    version?: string;
  };
}

// API Response types
export interface GroupsResponse {
  groups: Group[];
  total: number;
  discovery_timestamp: number;
  source: 'docker_discovery';
}

export interface ClientsResponse {
  clients: Client[];
  total_clients: number;
  active_clients: number;
  groups_available: number;
  timestamp: number;
}

export interface VideosResponse {
  videos: Video[];
  total: number;
  upload_folder: string;
}

// Group creation/update types
export interface CreateGroupRequest {
  name: string;
  description?: string;
  screen_count: number;
  orientation: 'horizontal' | 'vertical' | 'grid';
  streaming_mode: 'multi_video' | 'single_video_split'; // NEW: streaming mode
}

export interface CreateGroupResponse {
  message: string;
  group: Group;
  total_groups: number;
}

// Stream management types
export interface StartStreamRequest {
  group_id: string;
  streaming_mode?: 'multi_video' | 'single_video_split';
  video_file?: string; // For single video split mode
  video_files?: Array<{screen: number, file: string}>; // For multi-video mode
  enable_looping?: boolean;
  video_width?: number;
  video_height?: number;
  framerate?: number;
}

export interface StartStreamResponse {
  message: string;
  group_id: string;
  group_name: string;
  process_id: number;
  screen_count: number;
  orientation: string;
  persistent_streams: Record<string, string>;
  available_streams: string[];
  client_stream_urls: Record<string, string>;
  status: 'active';
  ffmpeg_command: string;
  active_clients: number;
  split_count: number;
  video_source: string;
  srt_port: number;
  docker_status: string;
}

// Client management types
export interface RegisterClientRequest {
  hostname: string;
  ip_address: string;
  display_name?: string;
}

export interface AssignClientRequest {
  client_id: string;
  group_id: string;
}

export interface AssignClientToScreenRequest {
  client_id: string;
  group_id: string;
  screen_number: number;
}

export interface ClientStatusRequest {
  client_id: string;
}

export interface ClientStatusResponse {
  client_id: string;
  assigned: boolean;
  group_id?: string;
  group_name?: string;
  docker_status?: string;
  docker_running?: boolean;
  stream_url?: string;
  available_streams?: string[];
  active_clients_in_group?: number;
  error?: string;
}

// Error response type
export interface ApiError {
  error: string;
  details?: any;
  suggestion?: string;
  available_groups?: string[];
  traceback?: string;
}

// Health check response
export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: number;
  architecture: 'hybrid_docker_discovery';
  checks: {
    app_state: boolean;
    upload_folder: boolean;
    download_folder: boolean;
    docker_discovery: boolean;
    client_management: boolean;
  };
  stats: {
    groups_discovered: number;
    clients_connected: number;
  };
}

// Operation status for UI
export interface OperationStatus {
  type: 'create' | 'delete' | 'start' | 'stop' | 'assign';
  target_id: string;
  target_name?: string;
  in_progress: boolean;
  error?: string;
}

// UI State types
export interface UIState {
  loading: boolean;
  showCreateForm: boolean;
  operationInProgress: string | null;
  selectedVideos: Record<string, string>;  // groupId -> videoFile
  searchTerm: string;
  sortBy: 'name' | 'created_at' | 'status';
  sortOrder: 'asc' | 'desc';
}

// Form state for group creation
export interface GroupFormState {
  name: string;
  description: string;
  screen_count: number;
  orientation: 'horizontal' | 'vertical' | 'grid';
  streaming_mode: 'multi_video' | 'single_video_split'; // NEW: streaming mode
}

// Toast message types
export interface ToastMessage {
  title: string;
  description?: string;
  variant?: 'default' | 'destructive' | 'success';
  duration?: number;
}
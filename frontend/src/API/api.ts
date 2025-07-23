// frontend/src/lib/api.ts - Fixed to match actual backend responses

// Fix the API base URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';

// Helper function to handle API responses with better error reporting
async function handleApiResponse(response: Response, endpoint: string) {
  const contentType = response.headers.get('content-type');
  
  console.log(`API ${endpoint}:`, {
    status: response.status,
    statusText: response.statusText,
    contentType,
    url: response.url
  });

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    
    try {
      if (contentType && contentType.includes('application/json')) {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.message || errorMessage;
      } else {
        const textResponse = await response.text();
        console.error(`Non-JSON error response for ${endpoint}:`, textResponse.substring(0, 500));
        errorMessage = `Server returned ${contentType || 'unknown content type'} instead of JSON`;
      }
    } catch (parseError) {
      console.error(`Failed to parse error response for ${endpoint}:`, parseError);
    }
    
    throw new Error(errorMessage);
  }

  if (!contentType || !contentType.includes('application/json')) {
    const textResponse = await response.text();
    console.error(`Expected JSON but got ${contentType} for ${endpoint}:`, textResponse.substring(0, 500));
    throw new SyntaxError(`Server returned ${contentType || 'unknown content type'} instead of JSON`);
  }

  try {
    return await response.json();
  } catch (jsonError) {
    console.error(`Failed to parse JSON response for ${endpoint}:`, jsonError);
    throw new SyntaxError(`Invalid JSON response from ${endpoint}`);
  }
}

export const groupApi = {
  async getGroups() {
    const response = await fetch(`${API_BASE_URL}/get_groups`);
    const data = await handleApiResponse(response, 'GET /get_groups');
   
    // Fix: Backend returns "total", not "total_groups"
    return {
      groups: data.groups.map((group: any) => ({
        id: group.id,
        name: group.name,
        description: group.description || '',
        screen_count: group.screen_count,
        orientation: group.orientation,
        status: group.docker_running ? 'active' : 'inactive',
        docker_container_id: group.container_id,
        container_id: group.container_id || 'unknown',
        docker_running: group.docker_running,
        docker_status: group.docker_status,
        container_name: group.container_name || 'unknown',
        ffmpeg_process_id: null,
        available_streams: group.available_streams || [],
        current_video: null,
        active_clients: 0,
        total_clients: 0,
        srt_port: group.ports?.srt_port || 10080,
        created_at_formatted: group.created_at_formatted,
        ports: group.ports || {
          rtmp_port: 1935,
          http_port: 1985,
          api_port: 8080,
          srt_port: 10080
        }
      })),
      total_groups: data.total // Fix: use "total" from backend
    };
  },

  async createGroup(groupData: {
    name: string;
    description?: string;
    screen_count: number;
    orientation: string;
  }) {
    const response = await fetch(`${API_BASE_URL}/create_group`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(groupData),
    });
    return await handleApiResponse(response, 'POST /create_group');
  },

  async deleteGroup(groupId: string) {
    const response = await fetch(`${API_BASE_URL}/delete_group`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ group_id: groupId }),
    });
    return await handleApiResponse(response, 'POST /delete_group');
  },

  async startMultiVideoGroup(groupId: string, videoFiles: Array<{screen: number, file: string}>, config?: any) {
    try {
      console.log(`🎬 Starting multi-video stream for group ${groupId} with ${videoFiles.length} videos`);
      
      const requestData = {
        group_id: groupId,
        video_files: videoFiles,
        screen_count: config?.screen_count || videoFiles.length,
        orientation: config?.orientation || 'horizontal',
        output_width: config?.output_width || 3840,
        output_height: config?.output_height || 1080,
        grid_rows: config?.grid_rows || 2,
        grid_cols: config?.grid_cols || 2,
        srt_ip: config?.srt_ip || '127.0.0.1',
        srt_port: config?.srt_port || 10080,
        sei: config?.sei || '681d5c8f-80cd-4847-930a-99b9484b4a32+000000'
      };

      console.log('📡 Request data:', requestData);

      const response = await fetch(`${API_BASE_URL}/start_multi_video_srt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      });

      const result = await handleApiResponse(response, 'POST /start_multi_video_srt');
      console.log('✅ Multi-video stream started successfully:', result);
      
      return result;
    } catch (error) {
      console.error('❌ Error starting multi-video stream:', error);
      throw error;
    }
  },

  async stopGroup(groupId: string) {
    try {
      console.log(`🛑 Stopping streams for group ${groupId}`);
      
      const response = await fetch(`${API_BASE_URL}/stop_group_srt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ group_id: groupId }),
      });

      const result = await handleApiResponse(response, 'POST /stop_group_srt');
      console.log('✅ Group streams stopped successfully:', result);
      
      return result;
    } catch (error) {
      console.error('❌ Error stopping group streams:', error);
      throw error;
    }
  },

  async getStreamingStatus(groupId: string) {
    try {
      const response = await fetch(`${API_BASE_URL}/streaming_status/${groupId}`);
      const result = await handleApiResponse(response, `GET /streaming_status/${groupId}`);
      
      return {
        is_streaming: result.is_streaming || false,
        process_id: result.process_id || null,
        available_streams: result.available_streams || [],
        client_stream_urls: result.client_stream_urls || {},
        status: result.status || 'inactive'
      };
    } catch (error) {
      console.error(`❌ Error getting streaming status for group ${groupId}:`, error);
      return { is_streaming: false };
    }
  },

  async getAllStreamingStatuses() {
    try {
      const response = await fetch(`${API_BASE_URL}/all_streaming_statuses`);
      const result = await handleApiResponse(response, 'GET /all_streaming_statuses');
      
      return {
        streaming_statuses: result.streaming_statuses || {}
      };
    } catch (error) {
      console.error('❌ Error getting all streaming statuses:', error);
      return { streaming_statuses: {} };
    }
  }
};

// FIXED Client API - matching actual backend responses
export const clientApi = {
  async getClients() {
    const response = await fetch(`${API_BASE_URL}/get_clients`);
    const data = await handleApiResponse(response, 'GET /get_clients');
    
    // Backend response format is already correct
    return {
      clients: data.clients.map((client: any) => ({
        id: client.client_id,
        client_id: client.client_id,
        display_name: client.display_name,
        hostname: client.hostname,
        ip: client.ip_address,
        status: client.is_active ? 'active' : 'inactive',
        stream_id: client.stream_assignment,
        group_id: client.group_id,
        group_name: client.group_name,
        screen_number: client.screen_number,
        last_seen_formatted: client.seconds_ago ? `${client.seconds_ago}s ago` : 'Unknown',
        docker_running: client.group_docker_running
      })),
      total_clients: data.total_clients,
      active_clients: data.active_clients
    };
  },

  async registerClient(clientData: {
    hostname: string;
    ip_address: string;
    display_name?: string;
  }) {
    // Fix: Backend expects different format based on test results
    const response = await fetch(`${API_BASE_URL}/register_client`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      // Backend needs client_id and client_info format
      body: JSON.stringify({
        client_id: `client-${Date.now()}`, // Generate a client ID
        client_info: clientData
      }),
    });

    return await handleApiResponse(response, 'POST /register_client');
  },

  async assignClientToGroup(clientId: string, groupId: string) {
    const response = await fetch(`${API_BASE_URL}/assign_client_to_group`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        client_id: clientId,
        group_id: groupId
      }),
    });

    return await handleApiResponse(response, 'POST /assign_client_to_group');
  },

  // REMOVED: These endpoints don't exist in backend (return 404)
  // - assignClientToScreen
  // - autoAssignScreens  
  // - getClientStatus

  // TODO: Add these when backend implements them
  async assignClientToScreen(clientId: string, groupId: string, screenNumber: number) {
    console.warn('assignClientToScreen: Backend endpoint not implemented yet');
    throw new Error('Screen assignment not implemented in backend yet');
  },

  async autoAssignScreens(groupId: string) {
    console.warn('autoAssignScreens: Backend endpoint not implemented yet');
    throw new Error('Auto screen assignment not implemented in backend yet');
  }
};

// FIXED Video API - matching actual backend responses
export const videoApi = {
  async getVideos() {
    const response = await fetch(`${API_BASE_URL}/get_videos`);
    const data = await handleApiResponse(response, 'GET /get_videos');
    
    // Backend returns { success: true, videos: [...] }
    return {
      videos: data.videos || [],
      total_videos: data.videos?.length || 0
    };
  },

  async uploadVideo(file: File, onProgress?: (progress: number) => void) {
    const formData = new FormData();
    formData.append('video', file);

    const xhr = new XMLHttpRequest();
    
    return new Promise((resolve, reject) => {
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable && onProgress) {
          const progress = (e.loaded / e.total) * 100;
          onProgress(progress);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch (e) {
            reject(new SyntaxError('Invalid JSON response from upload'));
          }
        } else {
          try {
            const error = JSON.parse(xhr.responseText);
            reject(new Error(error.error || 'Failed to upload video'));
          } catch (e) {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Network error occurred'));
      });

      xhr.open('POST', `${API_BASE_URL}/upload_video`);
      xhr.send(formData);
    });
  }

  // REMOVED: These endpoints don't exist in backend
  // - deleteVideo (returns 404)
  // - getVideoInfo (returns 404)
  // - validateMultiVideo
  // - getMultiVideoPreview
  // - uploadMultipleVideos
};

// System API - these work fine
export const systemApi = {
  async getSystemStatus() {
    const response = await fetch(`${API_BASE_URL}/system_status`);
    return await handleApiResponse(response, 'GET /system_status');
  },

  async getHealth() {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    return await handleApiResponse(response, 'GET /api/health');
  },

  async ping() {
    const response = await fetch(`${API_BASE_URL}/ping`);
    return await handleApiResponse(response, 'GET /ping');
  }
};

// Combined API object
export const api = {
  group: groupApi,
  client: clientApi,
  video: videoApi,
  system: systemApi
};

// Debug function
export const debugApiMethods = () => {
  console.log('🔍 API Methods Debug (Fixed Version):');
  console.log('Available backend endpoints from test:', [
    '/get_groups ✓',
    '/get_videos ✓', 
    '/get_clients ✓',
    '/create_group ✓',
    '/delete_group ✓',
    '/register_client ✓',
    '/assign_client_to_group ✓',
    '/start_multi_video_srt ❌ (missing)',
    '/stop_group_srt ❌ (missing)',
    '/assign_client_to_screen ❌ (missing)',
    '/auto_assign_screens ❌ (missing)'
  ]);
};
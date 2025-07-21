// frontend/src/lib/api.ts - Fixed version ensuring all methods are properly exported

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

// Updated Group API for pure Docker discovery
export const groupApi = {
  // Get groups from Docker discovery (updated endpoint response)
  async getGroups() {
    const response = await fetch(`${API_BASE_URL}/get_groups`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    
    // Map Docker discovery response to frontend format
    return {
      groups: data.groups.map((group: any) => ({
        id: group.id,
        name: group.name,
        description: group.description || '',
        screen_count: group.screen_count,
        orientation: group.orientation,
        status: group.docker_running ? 'active' : 'inactive',
        docker_container_id: group.container_id,
        container_id: group.container_id || 'unknown', // Add fallback
        docker_running: group.docker_running,
        docker_status: group.docker_status,
        container_name: group.container_name || 'unknown', // Add fallback
        ffmpeg_process_id: null, // Not tracked in group state anymore
        available_streams: group.available_streams || [],
        current_video: null, // This comes from stream management now
        active_clients: 0, // Will be calculated separately
        total_clients: 0, // Will be calculated separately
        srt_port: group.ports?.srt_port || 10080,
        created_at_formatted: group.created_at_formatted,
        ports: group.ports || {
          rtmp_port: 1935,
          http_port: 1985,
          api_port: 8080,
          srt_port: 10080
        }
      }))
    };
  },

  // Create group (unchanged)
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

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to create group');
    }

    return response.json();
  },

  // Delete group (unchanged)
  async deleteGroup(groupId: string) {
    const response = await fetch(`${API_BASE_URL}/delete_group`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ group_id: groupId }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to delete group');
    }

    return response.json();
  },

  // Start group streaming (updated to use stream management)
  async startGroup(groupId: string, videoFile?: string) {
    const response = await fetch(`${API_BASE_URL}/start_group_srt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        group_id: groupId,
        video_file: videoFile || undefined
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to start group');
    }

    return response.json();
  },

  // Stop group streaming (updated to use stream management)
  async stopGroup(groupId: string) {
    const response = await fetch(`${API_BASE_URL}/stop_group_srt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ group_id: groupId }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to stop group');
    }

    return response.json();
  }
};

// Fixed Client API with explicit method definitions
export const clientApi = {
  // Get clients (updated response format)
  async getClients() {
    const response = await fetch(`${API_BASE_URL}/get_clients`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    
    return {
      clients: data.clients.map((client: any) => ({
        id: client.client_id, // Map to 'id' for frontend compatibility
        client_id: client.client_id,
        display_name: client.display_name,
        hostname: client.hostname,
        ip: client.ip_address, // Map ip_address to ip
        status: client.is_active ? 'active' : 'inactive',
        stream_id: client.stream_assignment,
        group_id: client.group_id,
        group_name: client.group_name,
        last_seen_formatted: client.seconds_ago ? `${client.seconds_ago}s ago` : 'Unknown',
        docker_running: client.group_docker_running
      })),
      total_clients: data.total_clients,
      active_clients: data.active_clients
    };
  },

  // Register client (unchanged)
  async registerClient(clientData: {
    hostname: string;
    ip_address: string;
    display_name?: string;
  }) {
    const response = await fetch(`${API_BASE_URL}/register_client`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(clientData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to register client');
    }

    return response.json();
  },

  // FIXED: Assign client to group - explicit method definition
  async assignClientToGroup(clientId: string, groupId: string) {
    console.log('🔧 Calling assignClientToGroup with:', { clientId, groupId });
    
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

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to assign client to group');
    }

    const result = await response.json();
    console.log('✅ assignClientToGroup result:', result);
    return result;
  },

  // Remove client (unchanged)
  async removeClient(clientId: string) {
    const response = await fetch(`${API_BASE_URL}/remove_client`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ client_id: clientId }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to remove client');
    }

    return response.json();
  },

  // Get client status (unchanged)
  async getClientStatus(clientId: string) {
    const response = await fetch(`${API_BASE_URL}/client_status`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ client_id: clientId }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to get client status');
    }

    return response.json();
  },

  // DEPRECATED: assignStream method (keeping for compatibility but marked deprecated)
  async assignStream(clientId: string, streamId: string) {
    console.warn('⚠️  assignStream is deprecated in hybrid architecture');
    
    // This is now a placeholder - stream assignment handled differently
    return Promise.resolve({ 
      success: true, 
      message: 'Stream assignment handled by group assignment' 
    });
  }
};

export const videoApi = {
  async getVideos() {
    const response = await fetch(`${API_BASE_URL}/get_videos`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  async uploadVideo(file: File) {
    const formData = new FormData();
    formData.append('file', file);  // Fixed: use 'file' instead of 'video'

    const response = await fetch(`${API_BASE_URL}/upload_video`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to upload video');
    }

    return response.json();
  },

  // ✅ Fixed: Use POST method with JSON body (original frontend approach)
  async deleteVideo(videoName: string) {
    const response = await fetch(`${API_BASE_URL}/delete_video`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ video_name: videoName }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || error.message || 'Failed to delete video');
    }

    return response.json();
  },

  async getVideoInfo(videoName: string) {
    const response = await fetch(`${API_BASE_URL}/video_info`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ video_name: videoName }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to get video info');
    }

    return response.json();
  }
};  

// System API for monitoring
export const systemApi = {
  async getSystemStatus() {
    const response = await fetch(`${API_BASE_URL}/system_status`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  async getHealth() {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  // For debugging API connections
  async ping() {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  }
};

// Export a combined API object for easier debugging
export const api = {
  group: groupApi,
  client: clientApi,
  video: videoApi,
  system: systemApi
};

// Debug function to check if all methods exist
export const debugApiMethods = () => {
  console.log('🔍 API Methods Debug:');
  console.log('clientApi methods:', Object.keys(clientApi));
  console.log('assignClientToGroup exists:', typeof clientApi.assignClientToGroup === 'function');
  
  // Test the method exists
  if (typeof clientApi.assignClientToGroup === 'function') {
    console.log('✅ assignClientToGroup method is properly defined');
  } else {
    console.error('❌ assignClientToGroup method is missing!');
  }
};
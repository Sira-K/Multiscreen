// Fix the API base URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

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

    return {
      groups: data.groups.map((group: any) => ({
        id: group.id,
        name: group.name,
        description: group.description || '',
        screen_count: group.screen_count,
        orientation: group.orientation,
        streaming_mode: group.streaming_mode,
        status: group.docker_running ? 'active' : 'inactive',
        docker_running: group.docker_running,
        docker_status: group.docker_status,
        active_clients: group.active_clients || 0,
        total_clients: group.total_clients || 0,
        container_id: group.container_id,
        container_name: group.container_name,
        created_at_formatted: group.created_at_formatted,
        ports: group.ports || {},
        srt_port: group.srt_port || 10080,
        available_streams: group.available_streams || [],
        current_video: group.current_video,
        ffmpeg_process_id: group.ffmpeg_process_id,
        docker_container_id: group.docker_container_id
      })),
      total_groups: data.total
    };
  },

  async createGroup(groupData: {
    name: string;
    description?: string;
    screen_count: number;
    orientation: string;
    streaming_mode: string;
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

  async startSingleVideoSplit(groupId: string, config: {
    video_file: string;
    screen_count?: number;
    orientation?: string;
    enable_looping?: boolean;
    srt_ip?: string;
    srt_port?: number;
  }) {
    try {
      console.log(`Starting single video split for group ${groupId} with video: ${config.video_file}`);

      const requestData = {
        group_id: groupId,
        video_file: config.video_file,
        screen_count: config.screen_count || 2,
        orientation: config.orientation || 'horizontal',
        enable_looping: config.enable_looping !== undefined ? config.enable_looping : true,
        loop_count: -1, // Infinite loop by default
        srt_ip: config.srt_ip || '127.0.0.1',
        srt_port: config.srt_port || 10080,
        sei: '681d5c8f-80cd-4847-930a-99b9484b4a32+000000'
      };

      console.log('Single video split request data:', requestData);

      const response = await fetch(`${API_BASE_URL}/start_split_screen_srt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      });

      const result = await handleApiResponse(response, 'POST /start_split_screen_srt');
      console.log('Single video split started successfully:', result);

      return result;
    } catch (error) {
      console.error('Error starting single video split:', error);
      throw error;
    }
  },

  async startMultiVideoGroup(groupId: string, videoFiles: Array<{ screen: number, file: string }>, config?: any) {
    try {
      console.log(`Starting single-stream multi-video for group ${groupId} with ${videoFiles.length} videos`);

      // Extract file paths from the objects
      const filePathsOnly = videoFiles.map(video => video.file);

      const requestData = {
        group_id: groupId,
        video_files: filePathsOnly,  // Now sending simple array of strings
        screen_count: config?.screen_count || videoFiles.length,
        orientation: config?.orientation || 'horizontal',
        output_width: config?.output_width || 1920,
        output_height: config?.output_height || 1080,
        grid_rows: config?.grid_rows || 2,
        grid_cols: config?.grid_cols || 2,
        srt_ip: config?.srt_ip || '127.0.0.1',
        srt_port: config?.srt_port || 10080,
        // Optional: Send screen mapping separately if needed
        screen_mapping: videoFiles  // Keep original structure for reference
      };

      console.log('Single-stream multi-video request data:', requestData);
      console.log('File paths being sent:', filePathsOnly);

      const response = await fetch(`${API_BASE_URL}/start_multi_video_srt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      });

      const result = await handleApiResponse(response, 'POST /start_multi_video_srt');
      console.log('Single-stream multi-video started successfully:', result);

      // Process the response to extract useful information
      if (result.stream_info && result.stream_info.crop_information) {
        console.log('Crop information for clients:', result.stream_info.crop_information);
        console.log('Stream URL:', result.stream_info.stream_url);

        // Log example client commands for debugging
        Object.keys(result.stream_info.crop_information).forEach(screenId => {
          const crop = result.stream_info.crop_information[screenId];
          console.log(`Screen ${screenId} crop: ${crop.width}x${crop.height}+${crop.x}+${crop.y}`);
        });
      }

      return result;
    } catch (error) {
      console.error('Error starting single-stream multi-video:', error);
      throw error;
    }
  },


  async stopGroup(groupId: string) {
    try {
      console.log(`Stopping streaming for group ${groupId}`);

      const response = await fetch(`${API_BASE_URL}/stop_group_stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ group_id: groupId }),
      });

      const result = await handleApiResponse(response, 'POST /stop_group_stream');
      console.log('Group streaming stopped successfully:', result);

      return result;
    } catch (error) {
      console.error('Error stopping group:', error);
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
      console.error(`Error getting streaming status for group ${groupId}:`, error);
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
      console.error('Error getting all streaming statuses:', error);
      return { streaming_statuses: {} };
    }
  }
};

export const clientApi = {
  // ===================================
  // CLIENT REGISTRATION & CONNECTION
  // ===================================

  async registerClient(clientData: {
    hostname: string;
    ip_address?: string;
    display_name?: string;
    platform?: string;
  }) {
    console.log('Registering client:', clientData);

    const response = await fetch(`${API_BASE_URL}/api/clients/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        hostname: clientData.hostname,
        ip_address: clientData.ip_address, // Optional - server will use request IP if not provided
        display_name: clientData.display_name,
        platform: clientData.platform || 'web'
      }),
    });

    const result = await handleApiResponse(response, 'POST /api/clients/register');
    console.log('Client registered successfully:', result);
    return result;
  },

  // Keep legacy method for backward compatibility
  async registerClientLegacy(clientData: {
    hostname: string;
    ip_address: string;
    display_name?: string;
    platform?: string;
  }) {
    console.log('Registering client (legacy):', clientData);

    const response = await fetch(`${API_BASE_URL}/register_client`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        hostname: clientData.hostname,
        ip_address: clientData.ip_address,
        display_name: clientData.display_name,
        platform: clientData.platform || 'web'
      }),
    });

    const result = await handleApiResponse(response, 'POST /register_client');
    console.log('Client registered successfully (legacy):', result);
    return result;
  },

  async waitForAssignment(clientId: string) {
    console.log(` Waiting for assignment for client: ${clientId}`);

    const response = await fetch(`${API_BASE_URL}/api/clients/wait_for_assignment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        client_id: clientId,
        hostname: clientId // Backend accepts either
      }),
    });

    return await handleApiResponse(response, 'POST /api/clients/wait_for_assignment');
  },

  // Keep legacy method for backward compatibility
  async waitForStream(clientId: string) {
    // Try new endpoint first, fallback to legacy
    try {
      return await this.waitForAssignment(clientId);
    } catch (error) {
      console.warn('New endpoint failed, trying legacy:', error);
      const response = await fetch(`${API_BASE_URL}/wait_for_stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: clientId,
          hostname: clientId
        }),
      });
      return await handleApiResponse(response, 'POST /wait_for_stream');
    }
  },

  async unregisterClient(clientId: string) {
    console.log(`Unregistering client: ${clientId}`);

    const response = await fetch(`${API_BASE_URL}/api/clients/unregister`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        client_id: clientId
      }),
    });

    return await handleApiResponse(response, 'POST /api/clients/unregister');
  },

  async sendHeartbeat(clientId: string) {
    console.log(`Sending heartbeat for client: ${clientId}`);

    const response = await fetch(`${API_BASE_URL}/api/clients/heartbeat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        client_id: clientId
      }),
    });

    const result = await handleApiResponse(response, 'POST /api/clients/heartbeat');
    console.log('Heartbeat sent successfully:', result);
    return result;
  },

  // ===================================
  // CLIENT INFORMATION & STATUS
  // ===================================

  async getClients() {
    console.log('Fetching all clients...');

    // Try new endpoint first, fallback to legacy
    let response, data;
    try {
      response = await fetch(`${API_BASE_URL}/api/clients/list`);
      data = await handleApiResponse(response, 'GET /api/clients/list');
    } catch (error) {
      console.warn('New endpoint failed, trying legacy:', error);
      response = await fetch(`${API_BASE_URL}/get_clients`);
      data = await handleApiResponse(response, 'GET /get_clients');
    }

    console.log('Raw backend response:', data);
    console.log(`Retrieved ${data.clients?.length || 0} clients`);

    return {
      clients: (data.clients || []).map((client: any) => {
        console.log('Processing client:', client);

        return {
          // Primary identifiers
          id: client.client_id,
          client_id: client.client_id,
          hostname: client.hostname,
          ip_address: client.ip_address || client.ip, // Handle both new and old format

          // Display info
          display_name: client.display_name || client.hostname,
          platform: client.platform || 'unknown',

          // Connection status
          is_active: client.is_active || false,
          status: client.status || (client.is_active ? 'active' : 'inactive'),
          assignment_status: client.assignment_status || 'unknown', // New field
          last_seen: client.last_seen || 0,
          seconds_ago: client.seconds_ago,
          last_seen_formatted: client.last_seen_formatted ||
            (client.seconds_ago ? `${client.seconds_ago}s ago` : 'Unknown'),

          // Group assignment
          group_id: client.group_id,
          group_name: client.group_name,
          group_docker_running: client.group_docker_running || false,
          group_docker_status: client.group_docker_status,

          // Stream assignment
          stream_assignment: client.stream_assignment,
          stream_id: client.stream_assignment, // Alias for frontend compatibility
          stream_url: client.stream_url,
          screen_number: client.screen_number,

          // Timestamps
          registered_at: client.registered_at || 0,
          assigned_at: client.assigned_at || 0,

          // Legacy fields
          order: client.order || 0
        };
      }),
      // Handle both new and old response formats
      total_clients: data.statistics?.total_clients || data.total_clients || 0,
      active_clients: data.statistics?.active_clients || data.active_clients || 0,
      assigned_clients: data.statistics?.assigned_clients || 0,
      screen_assigned_clients: data.statistics?.screen_assigned_clients || 0,
      statistics: data.statistics || {}
    };
  },

  async getClient(clientId: string) {
    console.log(`Getting client details for: ${clientId}`);

    // Try new endpoint first, fallback to legacy
    try {
      const response = await fetch(`${API_BASE_URL}/api/clients/get_client/${encodeURIComponent(clientId)}`);
      const result = await handleApiResponse(response, `GET /api/clients/get_client/${clientId}`);
      console.log(`Retrieved client details:`, result);
      return result;
    } catch (error) {
      console.warn('New endpoint failed, trying legacy:', error);
      const response = await fetch(`${API_BASE_URL}/get_client/${encodeURIComponent(clientId)}`);
      const result = await handleApiResponse(response, `GET /get_client/${clientId}`);
      console.log(`Retrieved client details (legacy):`, result);
      return result;
    }
  },

  // ===================================
  // GROUP ASSIGNMENT
  // ===================================

  async assignClientToGroup(clientId: string, groupId: string | null) {
    console.log(`Assigning client ${clientId} to group ${groupId}`);

    // Try new endpoint first, fallback to legacy
    try {
      const response = await fetch(`${API_BASE_URL}/api/clients/assign_to_group`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: clientId,
          group_id: groupId // Can be null to unassign
        }),
      });

      const result = await handleApiResponse(response, 'POST /api/clients/assign_to_group');
      console.log(`Client assigned to group successfully:`, result);
      return result;
    } catch (error) {
      console.warn('New endpoint failed, trying legacy:', error);
      const response = await fetch(`${API_BASE_URL}/api/clients/assign_to_group`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: clientId,
          group_id: groupId
        }),
      });

      const result = await handleApiResponse(response, 'POST /api/clients/assign_to_group');
      console.log(`Client assigned to group successfully (legacy):`, result);
      return result;
    }
  },

  async unassignClientFromGroup(clientId: string) {
    console.log(`Unassigning client ${clientId} from group`);

    return await this.unassignClient(clientId, 'all');
  },

  // ===================================
  // STREAM ASSIGNMENT (NEW)
  // ===================================

  async assignClientToStream(clientId: string, groupId?: string, streamName?: string, srtIp?: string) {
    console.log(`Assigning client ${clientId} to stream ${streamName} in group ${groupId}`);

    const response = await fetch(`${API_BASE_URL}/api/clients/assign_to_stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        client_id: clientId,
        group_id: groupId, // Optional if client already in group
        stream_name: streamName, // Optional - will auto-assign if not provided
        srt_ip: srtIp || '127.0.0.1'
      }),
    });

    const result = await handleApiResponse(response, 'POST /api/clients/assign_to_stream');
    console.log(`Client assigned to stream successfully:`, result);
    return result;
  },

  // ===================================
  // SCREEN ASSIGNMENT
  // ===================================

  async assignClientToScreen(clientId: string, groupId: string, screenNumber: number, srtIp?: string) {
    console.log(`Assigning client ${clientId} to screen ${screenNumber} in group ${groupId}`);

    const response = await fetch(`${API_BASE_URL}/api/clients/assign_to_screen`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        client_id: clientId,
        group_id: groupId,
        screen_number: screenNumber,
        srt_ip: srtIp || '127.0.0.1'
      }),
    });

    const result = await handleApiResponse(response, 'POST /api/clients/assign_to_screen');
    console.log(`Client assigned to screen successfully:`, result);
    return result;
  },

  async unassignClientFromScreen(clientId: string) {
    console.log(`Unassigning client ${clientId} from screen`);

    return await this.unassignClient(clientId, 'screen');
  },

  async autoAssignScreens(groupId: string, srtIp?: string) {
    console.log(` Auto-assigning screens for group ${groupId}`);

    // Try new endpoint first, fallback to legacy
    try {
      const response = await fetch(`${API_BASE_URL}/api/clients/auto_assign_group`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          group_id: groupId,
          assignment_type: 'screens',
          srt_ip: srtIp || '127.0.0.1'
        }),
      });

      const result = await handleApiResponse(response, 'POST /api/clients/auto_assign_group');
      console.log(`Auto-assigned screens:`, result);
      return result;
    } catch (error) {
      console.warn('New endpoint failed, trying legacy:', error);
      const response = await fetch(`${API_BASE_URL}/auto_assign_screens`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          group_id: groupId
        }),
      });

      const result = await handleApiResponse(response, 'POST /auto_assign_screens');
      console.log(`Auto-assigned screens (legacy):`, result);
      return result;
    }
  },

  async autoAssignStreams(groupId: string, srtIp?: string) {
    console.log(` Auto-assigning streams for group ${groupId}`);

    const response = await fetch(`${API_BASE_URL}/api/clients/auto_assign_group`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        group_id: groupId,
        assignment_type: 'streams',
        srt_ip: srtIp || '127.0.0.1'
      }),
    });

    const result = await handleApiResponse(response, 'POST /api/clients/auto_assign_group');
    console.log(`Auto-assigned streams:`, result);
    return result;
  },

  async getScreenAssignments(groupId: string) {
    console.log(`Getting screen assignments for group ${groupId}`);

    // Try legacy endpoint first (might still be available)
    try {
      const response = await fetch(`${API_BASE_URL}/get_screen_assignments?group_id=${encodeURIComponent(groupId)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      const result = await handleApiResponse(response, 'GET /get_screen_assignments');
      console.log(`Retrieved screen assignments:`, result);
      return result;
    } catch (error) {
      // Fallback: get clients and filter by group
      console.warn('Legacy endpoint failed, filtering clients by group:', error);
      const clients = await this.getClients();
      const groupClients = clients.clients.filter(client => client.group_id === groupId);

      return {
        group_id: groupId,
        assignments: groupClients.map(client => ({
          client_id: client.client_id,
          screen_number: client.screen_number,
          display_name: client.display_name
        }))
      };
    }
  },

  // ===================================
  // GENERIC UNASSIGNMENT (NEW)
  // ===================================

  async unassignClient(clientId: string, unassignType: 'all' | 'stream' | 'screen' = 'all') {
    console.log(` Unassigning client ${clientId} (type: ${unassignType})`);

    // Try new endpoint first, fallback to legacy
    try {
      const response = await fetch(`${API_BASE_URL}/api/clients/unassign_client`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: clientId,
          unassign_type: unassignType
        }),
      });

      const result = await handleApiResponse(response, 'POST /api/clients/unassign_client');
      console.log(` Client unassigned (${unassignType}):`, result);
      return result;
    } catch (error) {
      console.warn('New endpoint failed, trying legacy:', error);

      // Map to appropriate legacy endpoint
      if (unassignType === 'screen') {
        const response = await fetch(`${API_BASE_URL}/unassign_client_from_screen`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            client_id: clientId
          })
        });
        return await handleApiResponse(response, 'POST /unassign_client_from_screen');
      } else {
        // Default to full unassign
        const response = await fetch(`${API_BASE_URL}/unassign_client`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            client_id: clientId
          }),
        });
        return await handleApiResponse(response, 'POST /unassign_client');
      }
    }
  },

  // ===================================
  // CLIENT MANAGEMENT
  // ===================================

  async removeClient(clientId: string) {
    console.log(` Removing client ${clientId} from system`);

    // Try new endpoint first, fallback to legacy
    try {
      const response = await fetch(`${API_BASE_URL}/api/clients/remove_client`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: clientId
        }),
      });

      const result = await handleApiResponse(response, 'POST /api/clients/remove_client');
      console.log(` Client removed:`, result);
      return result;
    } catch (error) {
      console.warn('New endpoint failed, trying legacy:', error);
      return await this.deleteClient(clientId);
    }
  },

  async bulkRemoveClients(clientIds: string[], force: boolean = false) {
    console.log(` Bulk removing ${clientIds.length} clients from system`);

    try {
      const response = await fetch(`${API_BASE_URL}/api/clients/bulk_remove_clients`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_ids: clientIds,
          force: force
        }),
      });

      const result = await handleApiResponse(response, 'POST /api/clients/bulk_remove_clients');
      console.log(` Bulk remove completed:`, result);
      return result;
    } catch (error) {
      console.error('Bulk remove failed:', error);
      throw error;
    }
  },

  async cleanupDisconnectedClients(force: boolean = false) {
    console.log(` Cleaning up disconnected clients`);

    try {
      const response = await fetch(`${API_BASE_URL}/api/clients/cleanup_disconnected_clients`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          force: force
        }),
      });

      const result = await handleApiResponse(response, 'POST /api/clients/cleanup_disconnected_clients');
      console.log(` Cleanup completed:`, result);
      return result;
    } catch (error) {
      console.error('Cleanup failed:', error);
      throw error;
    }
  },

  async controlAutoCleanup(action: 'start' | 'stop' | 'status', config?: {
    cleanupIntervalSeconds?: number;
    inactiveThresholdSeconds?: number;
  }) {
    console.log(` Controlling auto-cleanup: ${action}`);

    try {
      const body: any = { action };
      if (config) {
        if (config.cleanupIntervalSeconds !== undefined) {
          body.cleanup_interval_seconds = config.cleanupIntervalSeconds;
        }
        if (config.inactiveThresholdSeconds !== undefined) {
          body.inactive_threshold_seconds = config.inactiveThresholdSeconds;
        }
      }

      const response = await fetch(`${API_BASE_URL}/api/clients/control_auto_cleanup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      const result = await handleApiResponse(response, 'POST /api/clients/control_auto_cleanup');
      console.log(` Auto-cleanup control result:`, result);
      return result;
    } catch (error) {
      console.error('Auto-cleanup control failed:', error);
      throw error;
    }
  },

  async deleteClient(clientId: string) {
    console.log(` Deleting client ${clientId}`);

    const response = await fetch(`${API_BASE_URL}/delete_client`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        client_id: clientId
      }),
    });

    const result = await handleApiResponse(response, 'DELETE /delete_client');
    console.log(` Client deleted:`, result);
    return result;
  },

  // These methods don't exist in new backend - kept for compatibility
  async renameClient(clientId: string, displayName: string) {
    console.log(` Renaming client ${clientId} to "${displayName}"`);

    // Try legacy endpoint
    try {
      const response = await fetch(`${API_BASE_URL}/rename_client`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: clientId,
          display_name: displayName
        }),
      });

      const result = await handleApiResponse(response, 'POST /rename_client');
      console.log(` Client renamed successfully:`, result);
      return result;
    } catch (error) {
      console.warn(' renameClient not implemented in new backend');
      return {
        success: false,
        message: 'Rename functionality not available in new backend structure'
      };
    }
  },

  async moveClient(clientId: string, direction: 'up' | 'down') {
    console.log(` Moving client ${clientId} ${direction}`);

    // Try legacy endpoint
    try {
      const response = await fetch(`${API_BASE_URL}/move_client`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: clientId,
          direction: direction
        }),
      });

      const result = await handleApiResponse(response, 'POST /move_client');
      console.log(` Client moved ${direction}:`, result);
      return result;
    } catch (error) {
      console.warn(' moveClient not implemented in new backend');
      return {
        success: false,
        message: 'Move functionality not available in new backend structure'
      };
    }
  },

  // ===================================
  // CLIENT POLLING & STREAMING
  // ===================================

  async startClientPolling(
    clientId: string,
    onStreamReady: (streamData: any) => void,
    onStatusUpdate?: (status: any) => void
  ) {
    console.log(` Starting polling for client ${clientId}`);

    const pollInterval = 3000; // Poll every 3 seconds
    let pollCount = 0;
    const maxPolls = 200; // Stop after 10 minutes (200 * 3 seconds)

    const poll = async () => {
      try {
        pollCount++;

        if (pollCount > maxPolls) {
          console.warn(` Polling timeout for client ${clientId} after ${maxPolls} attempts`);
          return;
        }

        // Use new waitForAssignment method
        const result = await this.waitForAssignment(clientId);

        // Notify status update callback
        if (onStatusUpdate) {
          onStatusUpdate({
            status: result.status,
            message: result.message,
            pollCount,
            maxPolls
          });
        }

        console.log(` Poll ${pollCount}/${maxPolls} - Client ${clientId} status: ${result.status}`);

        if (result.status === 'ready_to_play') {
          console.log(` Stream ready for client ${clientId}!`);
          onStreamReady(result);
          return; // Stop polling
        } else if (result.status === 'not_registered') {
          console.error(` Client ${clientId} not registered - stopping polling`);
          return; // Stop polling
        } else {
          console.log(` Client ${clientId}: ${result.message || result.status}`);
          setTimeout(poll, pollInterval); // Continue polling
        }
      } catch (error) {
        console.error(` Polling error for client ${clientId}:`, error);

        // Retry with exponential backoff
        const retryDelay = Math.min(pollInterval * Math.pow(1.5, pollCount % 5), 30000);
        setTimeout(poll, retryDelay);
      }
    };

    poll(); // Start polling
  },

  // ===================================
  // HEALTH & STATUS
  // ===================================

  async getHealthStatus() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/clients/health`);
      const result = await handleApiResponse(response, 'GET /api/clients/health');
      return result;
    } catch (error) {
      console.error(' Health check failed:', error);
      return { success: false, error: error.message };
    }
  },

  // ===================================
  // UTILITY FUNCTIONS
  // ===================================

  async ping() {
    // Try new health endpoint first, fallback to legacy
    try {
      const healthResult = await this.getHealthStatus();
      return { success: healthResult.success, ...healthResult };
    } catch (error) {
      try {
        const response = await fetch(`${API_BASE_URL}/ping`);
        const result = await handleApiResponse(response, 'GET /ping');
        return { success: true, ...result };
      } catch (legacyError) {
        console.error(' Server ping failed:', error);
        return { success: false, error: error.message };
      }
    }
  },

  async getServerStatus() {
    // Try new health endpoint first, fallback to legacy
    try {
      return await this.getHealthStatus();
    } catch (error) {
      try {
        const response = await fetch(`${API_BASE_URL}/status`);
        const result = await handleApiResponse(response, 'GET /status');
        return result;
      } catch (legacyError) {
        console.error(' Failed to get server status:', error);
        throw error;
      }
    }
  }
};

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

  async uploadVideo(
    files: File | File[],
    onProgress?: (progress: {
      currentFile: string;
      currentFileProgress: number;
      overallProgress: number;
      completedFiles: number;
      totalFiles: number;
      currentFileIndex: number;
    }) => void
  ) {
    // Convert single file to array for consistent handling
    const fileArray = Array.isArray(files) ? files : [files];

    const results = {
      successful: [] as Array<{
        original_filename: string;
        saved_filename: string;
        size_mb: number;
        status: string;
        path: string;
        processing_time_seconds: number;
      }>,
      failed: [] as Array<{
        filename: string;
        error: string;
      }>,
      summary: {
        total: fileArray.length,
        successful: 0,
        failed: 0
      },
      timing: {
        total_time_seconds: 0,
        started_at: '',
        completed_at: '',
        individual_uploads: [] as Array<{
          filename: string;
          upload_time_seconds: number;
          file_size_mb: number;
        }>
      }
    };

    const startTime = Date.now();
    results.timing.started_at = new Date().toISOString();

    // Upload files one by one
    for (let i = 0; i < fileArray.length; i++) {
      const file = fileArray[i];
      const fileStartTime = Date.now();

      try {
        // Update progress for current file start
        if (onProgress) {
          onProgress({
            currentFile: file.name,
            currentFileProgress: 0,
            overallProgress: (i / fileArray.length) * 100,
            completedFiles: i,
            totalFiles: fileArray.length,
            currentFileIndex: i
          });
        }

        // Upload single file
        const uploadResult = await this.uploadSingleFile(file, (fileProgress) => {
          if (onProgress) {
            const overallProgress = ((i + (fileProgress / 100)) / fileArray.length) * 100;
            onProgress({
              currentFile: file.name,
              currentFileProgress: fileProgress,
              overallProgress,
              completedFiles: i,
              totalFiles: fileArray.length,
              currentFileIndex: i
            });
          }
        });

        const fileEndTime = Date.now();
        const uploadTimeSeconds = (fileEndTime - fileStartTime) / 1000;

        // Handle successful upload
        if (uploadResult.success && uploadResult.uploads && uploadResult.uploads.length > 0) {
          const uploadData = uploadResult.uploads[0]; // Single file upload
          results.successful.push(uploadData);
          results.summary.successful++;

          // Add individual upload timing
          results.timing.individual_uploads.push({
            filename: file.name,
            upload_time_seconds: uploadTimeSeconds,
            file_size_mb: uploadData.size_mb
          });

          console.log(` Successfully uploaded: ${file.name} (${uploadTimeSeconds.toFixed(2)}s)`);
        } else {
          throw new Error(uploadResult.message || 'Upload failed without error message');
        }

      } catch (error) {
        const fileEndTime = Date.now();
        const uploadTimeSeconds = (fileEndTime - fileStartTime) / 1000;

        console.error(` Failed to upload ${file.name}:`, error);

        results.failed.push({
          filename: file.name,
          error: error instanceof Error ? error.message : 'Unknown error'
        });
        results.summary.failed++;

        // Add failed upload timing
        results.timing.individual_uploads.push({
          filename: file.name,
          upload_time_seconds: uploadTimeSeconds,
          file_size_mb: file.size / (1024 * 1024) // Convert bytes to MB
        });
      }
    }

    // Final progress update
    if (onProgress) {
      onProgress({
        currentFile: '',
        currentFileProgress: 100,
        overallProgress: 100,
        completedFiles: fileArray.length,
        totalFiles: fileArray.length,
        currentFileIndex: fileArray.length
      });
    }

    // Calculate total timing
    const endTime = Date.now();
    results.timing.completed_at = new Date().toISOString();
    results.timing.total_time_seconds = (endTime - startTime) / 1000;

    console.log(` Upload Summary: ${results.summary.successful}/${results.summary.total} successful in ${results.timing.total_time_seconds.toFixed(2)}s`);

    return results;
  },

  // Helper function for uploading a single file
  async uploadSingleFile(file: File, onProgress?: (progress: number) => void): Promise<any> {
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
            reject(new Error(error.message || error.error || 'Failed to upload video'));
          } catch (e) {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Network error occurred'));
      });

      xhr.addEventListener('timeout', () => {
        reject(new Error('Upload timeout'));
      });

      // Set timeout (optional - adjust as needed)
      xhr.timeout = 300000; // 5 minutes

      xhr.open('POST', `${API_BASE_URL}/upload_video`);
      xhr.send(formData);
    });
  },

  async deleteVideo(videoName: string) {
    try {
      console.log(`Attempting to delete video: ${videoName}`);

      const response = await fetch(`${API_BASE_URL}/delete_video`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_name: videoName
        })
      });
      console.log(`Delete response status: ${response.status}`);

      // Use your existing handleApiResponse function for consistency
      const data = await handleApiResponse(response, `DELETE /delete_video (${videoName})`);

      console.log('Video deleted successfully:', data);
      return data;

    } catch (error) {
      console.error('Delete video error:', error);

      // Re-throw with more context
      if (error instanceof Error) {
        throw new Error(`Failed to delete "${videoName}": ${error.message}`);
      } else {
        throw new Error(`Failed to delete "${videoName}": Unknown error`);
      }
    }
  },

  async deleteMultipleVideos(
    videoNames: string[],
    onProgress?: (progress: { completed: number; total: number; currentFile: string }) => void
  ) {
    const successful: string[] = [];
    const failed: Array<{ filename: string; error: string }> = [];

    for (let i = 0; i < videoNames.length; i++) {
      const videoName = videoNames[i];

      // Update progress
      if (onProgress) {
        onProgress({
          completed: i,
          total: videoNames.length,
          currentFile: videoName
        });
      }

      try {
        await this.deleteVideo(videoName);
        successful.push(videoName);
      } catch (error) {
        failed.push({
          filename: videoName,
          error: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    }

    // Final progress update
    if (onProgress) {
      onProgress({
        completed: videoNames.length,
        total: videoNames.length,
        currentFile: ''
      });
    }

    return {
      successful,
      failed,
      summary: {
        total: videoNames.length,
        successful: successful.length,
        failed: failed.length
      }
    };
  }
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

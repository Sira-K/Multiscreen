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
      console.log(`🎬 Starting single video split for group ${groupId} with video: ${config.video_file}`);
      
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

      console.log('📡 Single video split request data:', requestData);

      const response = await fetch(`${API_BASE_URL}/start_single_video_split`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      });

      const result = await handleApiResponse(response, 'POST /start_single_video_split');
      console.log('✅ Single video split started successfully:', result);
      
      return result;
    } catch (error) {
      console.error('❌ Error starting single video split:', error);
      throw error;
    }
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

      console.log('📡 Multi-video request data:', requestData);

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
      console.error('❌ Error starting multi-video:', error);
      throw error;
    }
  },


  async stopGroup(groupId: string) {
    try {
      console.log(`🛑 Stopping streaming for group ${groupId}`);
      
      const response = await fetch(`${API_BASE_URL}/stop_group`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ group_id: groupId }),
      });

      const result = await handleApiResponse(response, 'POST /stop_group');
      console.log('✅ Group streaming stopped successfully:', result);
      
      return result;
    } catch (error) {
      console.error('❌ Error stopping group:', error);
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

  async assignClientToScreen(clientId: string, groupId: string, screenNumber: number) {
    try {
      const response = await fetch(`${API_BASE_URL}/assign_client_to_screen`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: clientId,
          group_id: groupId,
          screen_number: screenNumber
        }),
      });

      return await handleApiResponse(response, 'POST /assign_client_to_screen');
    } catch (error) {
      console.warn('⚠️ assignClientToScreen: Backend endpoint not implemented yet');
      throw new Error('Screen assignment not implemented in backend yet');
    }
  },

  async autoAssignScreens(groupId: string) {
    try {
      const response = await fetch(`${API_BASE_URL}/auto_assign_screens`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ group_id: groupId }),
      });

      return await handleApiResponse(response, 'POST /auto_assign_screens');
    } catch (error) {
      console.warn('⚠️ autoAssignScreens: Backend endpoint not implemented yet');
      throw new Error('Auto screen assignment not implemented in backend yet');
    }
  },

  async getScreenAssignments(groupId: string) {
    console.log(`📋 Getting screen assignments for group ${groupId}`);
    
    const response = await fetch(`${API_BASE_URL}/get_screen_assignments?group_id=${encodeURIComponent(groupId)}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    const result = await handleApiResponse(response, 'GET /get_screen_assignments');
    console.log(`✅ Retrieved screen assignments:`, result);
    return result;
  },

  async unassignClientFromScreen(clientId: string) {
    console.log(`🎯 Unassigning client ${clientId} from screen`);
    
    const response = await fetch(`${API_BASE_URL}/unassign_client_from_screen`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        client_id: clientId
      })
    });

    const result = await handleApiResponse(response, 'POST /unassign_client_from_screen');
    console.log(`✅ Successfully unassigned client from screen:`, result);
    return result;
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

          console.log(`✅ Successfully uploaded: ${file.name} (${uploadTimeSeconds.toFixed(2)}s)`);
        } else {
          throw new Error(uploadResult.message || 'Upload failed without error message');
        }

      } catch (error) {
        const fileEndTime = Date.now();
        const uploadTimeSeconds = (fileEndTime - fileStartTime) / 1000;

        console.error(`❌ Failed to upload ${file.name}:`, error);
        
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

    console.log(`📊 Upload Summary: ${results.summary.successful}/${results.summary.total} successful in ${results.timing.total_time_seconds.toFixed(2)}s`);

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

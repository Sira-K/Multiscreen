// src/components/GroupCard.tsx - Modified with proper operations
import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Play, Square, Monitor, Users, CheckCircle, AlertCircle } from "lucide-react";
import { groupApi } from '@/lib/api'; // Add this import

interface Group {
  id: string;
  name: string;
  description: string;
  screen_count: number;
  orientation: string;
  status: 'active' | 'inactive' | 'starting' | 'stopping';
  docker_container_id?: string;
  ffmpeg_process_id?: number;
  available_streams: string[];
  current_video?: string;
  active_clients: number;
  total_clients: number;
  srt_port: number;
  created_at_formatted: string;
}

interface Client {
  client_id: string;
  display_name?: string;
  hostname?: string;
  ip: string;
  status: 'active' | 'inactive';
  stream_id?: string | null;
  group_id?: string | null;
  group_name?: string | null;
}

interface Video {
  name: string;
  path: string;
  size_mb: number;
}

interface GroupCardProps {
  group: Group;
  videos: Video[];
  clients: Client[];
  selectedVideo: string | undefined;
  operationInProgress: string | null;
  onVideoSelect: (groupId: string, videoName: string) => void;
  onStart: (groupId: string, groupName: string) => void;
  onStop: (groupId: string, groupName: string) => void;
  onDelete: (groupId: string, groupName: string) => void;
  onAssignClient: (clientId: string, streamId: string, groupId: string) => void;
  // Add these new props for proper operations
  onRefreshGroups?: () => Promise<void>;
  setOperationInProgress?: (groupId: string | null) => void;
}

const GroupCard: React.FC<GroupCardProps> = ({
  group,
  videos,
  clients,
  selectedVideo,
  operationInProgress,
  onVideoSelect,
  onStart,
  onStop,
  onDelete,
  onAssignClient,
  onRefreshGroups,
  setOperationInProgress,
}) => {
  console.log(`🔍 Group "${group.name}" status:`, {
    status: group.status,
    docker_container_id: group.docker_container_id,
    ffmpeg_process_id: group.ffmpeg_process_id,
    showingStopButton: group.status === 'active'
  });

  console.log('🔍 GroupCard - clients data:', clients);
  console.log('🔍 GroupCard - group:', group);

  // Enhanced start function with proper API call and refresh
  const handleStartGroup = async (groupId: string, groupName: string) => {
    console.log(`🚀 Starting group "${groupName}" (${groupId}) with video: ${selectedVideo}`);
    
    if (!selectedVideo) {
      console.error('❌ No video selected');
      return;
    }

    try {
      if (setOperationInProgress) {
        setOperationInProgress(groupId);
      }
      
      // Call the API directly with proper parameters
      console.log('🔄 Calling start API...');
      const result = await groupApi.startGroup(groupId, selectedVideo);
      console.log('✅ Start API result:', result);
      
      // Refresh groups to get updated status
      if (onRefreshGroups) {
        console.log('🔄 Refreshing groups after start...');
        await onRefreshGroups();
        
        // Log the updated status
        console.log(`📊 Group "${groupName}" should now be active`);
      }
      
      // Call the original onStart for any additional handling
      onStart(groupId, groupName);
      
    } catch (error) {
      console.error(`❌ Failed to start group "${groupName}":`, error);
      
      // Still refresh to get current status
      if (onRefreshGroups) {
        try {
          await onRefreshGroups();
        } catch (refreshError) {
          console.error('❌ Failed to refresh after start error:', refreshError);
        }
      }
    } finally {
      if (setOperationInProgress) {
        setOperationInProgress(null);
      }
    }
  };

  // Enhanced stop function with proper API call and refresh
  const handleStopGroup = async (groupId: string, groupName: string) => {
    console.log(`🛑 Stopping group "${groupName}" (${groupId})`);
    
    try {
      if (setOperationInProgress) {
        setOperationInProgress(groupId);
      }
      
      // Call the API directly
      console.log('🔄 Calling stop API...');
      const result = await groupApi.stopGroup(groupId);
      console.log('✅ Stop API result:', result);
      
      // Refresh groups to get updated status
      if (onRefreshGroups) {
        console.log('🔄 Refreshing groups after stop...');
        await onRefreshGroups();
        
        // Log the updated status
        console.log(`📊 Group "${groupName}" should now be inactive`);
      }
      
      // Call the original onStop for any additional handling
      onStop(groupId, groupName);
      
    } catch (error) {
      console.error(`❌ Failed to stop group "${groupName}":`, error);
      
      // Still refresh to get current status
      if (onRefreshGroups) {
        try {
          await onRefreshGroups();
        } catch (refreshError) {
          console.error('❌ Failed to refresh after stop error:', refreshError);
        }
      }
    } finally {
      if (setOperationInProgress) {
        setOperationInProgress(null);
      }
    }
  };

  // Enhanced delete function
  const handleDeleteGroup = async (groupId: string, groupName: string) => {
    console.log(`🗑️ Deleting group "${groupName}" (${groupId})`);
    
    try {
      if (setOperationInProgress) {
        setOperationInProgress(groupId);
      }
      
      // Call the API directly
      const result = await groupApi.deleteGroup(groupId);
      console.log('✅ Delete API result:', result);
      
      // Refresh groups to remove deleted group
      if (onRefreshGroups) {
        await onRefreshGroups();
      }
      
      // Call the original onDelete for any additional handling
      onDelete(groupId, groupName);
      
    } catch (error) {
      console.error(`❌ Failed to delete group "${groupName}":`, error);
      
      // Still refresh to get current status
      if (onRefreshGroups) {
        try {
          await onRefreshGroups();
        } catch (refreshError) {
          console.error('❌ Failed to refresh after delete error:', refreshError);
        }
      }
    } finally {
      if (setOperationInProgress) {
        setOperationInProgress(null);
      }
    }
  };

  const getStatusBadge = () => {
    const isOperating = operationInProgress === group.id;
    
    if (isOperating) {
      return (
        <Badge className="bg-yellow-100 text-yellow-800 border-yellow-200">
          <div className="w-3 h-3 border-2 border-yellow-600 border-t-transparent rounded-full animate-spin mr-1" />
          Processing...
        </Badge>
      );
    }

    switch (group.status) {
      case 'active':
        return (
          <Badge className="bg-green-100 text-green-800 border-green-200">
            <CheckCircle className="w-3 h-3 mr-1" />
            Active
          </Badge>
        );
      case 'starting':
        return (
          <Badge className="bg-blue-100 text-blue-800 border-blue-200">
            <div className="w-3 h-3 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mr-1" />
            Starting
          </Badge>
        );
      case 'stopping':
        return (
          <Badge className="bg-orange-100 text-orange-800 border-orange-200">
            <div className="w-3 h-3 border-2 border-orange-600 border-t-transparent rounded-full animate-spin mr-1" />
            Stopping
          </Badge>
        );
      default:
        return (
          <Badge className="bg-gray-100 text-gray-800 border-gray-200">
            <AlertCircle className="w-3 h-3 mr-1" />
            Inactive
          </Badge>
        );
    }
  };

  const getLayoutDescription = () => {
    if (group.orientation === 'grid') {
      const rows = Math.sqrt(group.screen_count);
      const cols = Math.sqrt(group.screen_count);
      return `${rows}×${cols} Grid (${group.screen_count} screens)`;
    }
    return `${group.orientation} (${group.screen_count} screens)`;
  };

  // Filter clients for this group
  const assignedClients = clients.filter(client => client.group_id === group.id);
  const unassignedClients = clients.filter(client => 
    (!client.group_id || client.group_id !== group.id) && client.status === 'active'
  ).slice(0, 3);

  // Determine button states
  const isActive = group.status === 'active';
  const isTransitioning = group.status === 'starting' || group.status === 'stopping';
  const isOperating = operationInProgress === group.id;
  const canStart = !isActive && !isTransitioning && !isOperating && videos.length > 0 && selectedVideo;
  const canStop = isActive && !isTransitioning && !isOperating;

  return (
    <Card className="hover:shadow-md transition-shadow">
      <div className="text-xs bg-gray-100 p-2 mb-2">
        Debug: Status = "{group.status}" | Docker: {group.docker_container_id ? '✅' : '❌'} | SRT: {group.ffmpeg_process_id ? '✅' : '❌'} | Operation: {isOperating ? '🔄' : '⏹️'}
      </div>
      <CardHeader>
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-lg">{group.name}</CardTitle>
            <CardDescription>{group.description || 'No description'}</CardDescription>
          </div>
          {getStatusBadge()}
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Group Info */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="flex items-center">
            <Monitor className="w-4 h-4 mr-2 text-gray-500" />
            {getLayoutDescription()}
          </div>
          <div className="flex items-center">
            <Users className="w-4 h-4 mr-2 text-gray-500" />
            {group.active_clients || 0}/{group.total_clients || 0} clients
          </div>
        </div>

        {/* Current Video */}
        {group.current_video && (
          <div className="text-sm">
            <span className="font-medium">Playing:</span> {group.current_video}
          </div>
        )}

        {/* Available Streams Info */}
        {group.available_streams && group.available_streams.length > 0 && (
          <div className="text-sm text-green-600">
            <span className="font-medium">Active Streams:</span> {group.available_streams.length}
          </div>
        )}

        {/* Video Selection */}
        {group.status === 'inactive' && (
          <div className="space-y-2">
            <div className="text-sm font-medium text-gray-700">
              Select Video: ({videos.length} available)
            </div>
            
            {videos.length === 0 ? (
              <div className="text-sm text-red-600 p-2 border border-red-200 rounded">
                ⚠️ No videos found. Upload videos first in the Video Files tab.
              </div>
            ) : (
              <>
                <Select
                  value={selectedVideo || ''}
                  onValueChange={(value) => {
                    console.log('🎥 Video selected:', value);
                    onVideoSelect(group.id, value);
                  }}
                  disabled={isOperating}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder={`Choose from ${videos.length} video${videos.length !== 1 ? 's' : ''}...`} />
                  </SelectTrigger>
                  <SelectContent>
                    {videos.map((video, index) => (
                      <SelectItem key={`${video.name}-${index}`} value={video.name}>
                        <div className="flex flex-col">
                          <span className="font-medium">{video.name}</span>
                          <span className="text-xs text-gray-500">{video.size_mb} MB</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {selectedVideo && (
                  <div className="text-xs text-green-600">
                    ✓ {selectedVideo} selected
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Client Management Section */}
        <div className="space-y-2">
          <div className="text-sm font-medium text-gray-700">
            Client Assignments: ({assignedClients.length})
          </div>
          <div className="space-y-2">
            {/* Show clients already assigned to this group */}
            {assignedClients.map(client => (
              <div key={`assigned-${client.client_id}`} className="flex items-center justify-between p-2 bg-gray-50 rounded border">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${client.status === 'active' ? 'bg-green-500' : 'bg-red-500'}`}></div>
                  <span className="text-sm font-medium">
                    {client.display_name || client.hostname || client.client_id}
                  </span>
                  {client.stream_id && (
                    <Badge variant="outline" className="text-xs">
                      {client.stream_id.replace(`live/${group.id}/`, '')}
                    </Badge>
                  )}
                </div>
                
                <select
                  value={client.stream_id || ''}
                  onChange={(e) => {
                    console.log('🔧 Debug assigned client dropdown change:', {
                      clientObject: client,
                      clientId: client?.client_id,
                      streamValue: e.target.value
                    });
                    
                    if (client?.client_id) {
                      onAssignClient(client.client_id, e.target.value, group.id);
                    } else {
                      console.error('❌ Missing client_id:', client);
                    }
                  }}
                  className="text-xs p-1 border border-gray-300 rounded"
                  disabled={operationInProgress === `assign-${client.client_id}`}
                >
                  <option value="">Unassign</option>
                  <option value={`live/${group.id}/test`}>Full Screen</option>
                  {/* Add more stream options if available */}
                  {group.available_streams && group.available_streams.map(streamId => (
                    <option key={streamId} value={streamId}>
                      {streamId.replace(`live/${group.id}/`, '')}
                    </option>
                  ))}
                </select>
              </div>
            ))}
              
            {/* Show unassigned clients */}
            {unassignedClients.map(client => (
              <div key={`unassigned-${client.client_id}`} className="flex items-center justify-between p-2 bg-blue-50 rounded border border-blue-200">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${client.status === 'active' ? 'bg-green-500' : 'bg-red-500'}`}></div>
                  <span className="text-sm text-blue-700">
                    {client.display_name || client.hostname || client.client_id}
                  </span>
                  <Badge variant="secondary" className="text-xs">Unassigned</Badge>
                </div>
                
                <select
                  onChange={(e) => {
                    console.log('🔧 Debug unassigned dropdown change:', {
                      clientObject: client,
                      clientId: client?.client_id,
                      streamValue: e.target.value
                    });
                    
                    if (e.target.value && client?.client_id) {
                      onAssignClient(client.client_id, e.target.value, group.id);
                    } else {
                      console.error('❌ Missing client_id:', client);
                    }
                  }}
                  className="text-xs p-1 border border-blue-300 rounded bg-white"
                  defaultValue=""
                >
                  <option value="">Assign to stream...</option>
                  {/* Use the same stream options as above */}
                  {group.available_streams && group.available_streams.length > 0 ? (
                    group.available_streams.map(streamId => (
                      <option key={streamId} value={streamId}>
                        {streamId.replace(`live/${group.id}/`, '')}
                      </option>
                    ))
                  ) : (
                    // Fallback streams for inactive groups
                    Array.from({length: group.screen_count}, (_, i) => (
                      <option key={i} value={`live/${group.id}/test${i}`}>
                        Section {i + 1}
                      </option>
                    )).concat([
                      <option key="full" value={`live/${group.id}/test`}>
                        Full Video
                      </option>
                    ])
                  )}
                </select>
              </div>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          {isActive || isTransitioning ? (
            <Button
              onClick={() => handleStopGroup(group.id, group.name)}
              disabled={!canStop}
              variant="destructive"
              size="sm"
              className="flex-1"
            >
              {isOperating ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
              ) : (
                <Square className="w-4 h-4 mr-2" />
              )}
              {isTransitioning ? (group.status === 'stopping' ? 'Stopping...' : 'Starting...') : 'Stop'}
            </Button>
          ) : (
            <Button
              onClick={() => handleStartGroup(group.id, group.name)}
              disabled={!canStart}
              className="bg-green-600 hover:bg-green-700 flex-1"
              size="sm"
            >
              {isOperating ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
              ) : (
                <Play className="w-4 h-4 mr-2" />
              )}
              Start
              {!selectedVideo && videos.length > 0 && (
                <span className="ml-1 text-xs">(Select video)</span>
              )}
            </Button>
          )}
          
          <Button
            onClick={() => handleDeleteGroup(group.id, group.name)}
            disabled={operationInProgress === group.id || group.status === 'active'}
            variant="outline"
            size="sm"
          >
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default GroupCard;
// frontend/src/components/ui/GroupCard.tsx - Fixed with proper streaming status

import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Square, Users, Monitor, Power, AlertCircle, Video as VideoIcon, Grid3X3, Rows, Columns, Play } from "lucide-react";
import type { Video } from '@/types';
import { api } from '@/API/api';

interface Client {
  client_id: string;
  display_name?: string;
  hostname?: string;
  ip_address?: string;
  is_active?: boolean;
  group_id?: string | null;
  screen_number?: number;
}

interface Group {
  id: string;
  name: string;
  description?: string;
  screen_count: number;
  orientation: 'horizontal' | 'vertical' | 'grid';
  docker_running: boolean;
  active_clients?: number;
}

interface VideoAssignment {
  screen: number;
  file: string;
}

interface GroupCardProps {
  group: Group;
  videos: Video[];
  clients: Client[];
  unassignedClients: Client[];
  isStreaming: boolean;
  operationInProgress: string | null;
  onStop: (groupId: string, groupName: string) => void;
  onDelete: (groupId: string, groupName: string) => void;
  onAssignClient: (clientId: string, groupId: string) => void;
  onStreamingStatusChange?: (groupId: string, isStreaming: boolean) => void;
  onRefresh?: () => void;
}

const GroupCard = ({
  group,
  videos,
  clients,
  unassignedClients,
  isStreaming: initialIsStreaming,
  operationInProgress,
  onStop,
  onDelete,
  onAssignClient,
  onStreamingStatusChange,
  onRefresh
}: GroupCardProps) => {
  const [showMultiVideoDialog, setShowMultiVideoDialog] = useState(false);
  const [videoAssignments, setVideoAssignments] = useState<VideoAssignment[]>([]);
  const [isStartingMultiVideo, setIsStartingMultiVideo] = useState(false);
  const [isStoppingStream, setIsStoppingStream] = useState(false);
  
  // Local streaming state that can be updated independently
  const [localIsStreaming, setLocalIsStreaming] = useState(initialIsStreaming);

  // Sync with parent prop changes
  useEffect(() => {
    setLocalIsStreaming(initialIsStreaming);
  }, [initialIsStreaming]);

  // Check streaming status periodically
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const status = await api.group.getStreamingStatus(group.id);
        const newIsStreaming = status.is_streaming;
        
        if (newIsStreaming !== localIsStreaming) {
          console.log(`🔄 Streaming status changed for ${group.name}: ${localIsStreaming} -> ${newIsStreaming}`);
          setLocalIsStreaming(newIsStreaming);
          
          if (onStreamingStatusChange) {
            onStreamingStatusChange(group.id, newIsStreaming);
          }
        }
      } catch (error) {
        console.error('Error checking streaming status:', error);
      }
    };

    // Check immediately and then every 5 seconds
    checkStatus();
    const interval = setInterval(checkStatus, 5000);
    
    return () => clearInterval(interval);
  }, [group.id, localIsStreaming, onStreamingStatusChange]);

  // Initialize video assignments based on screen count
  const initializeVideoAssignments = () => {
    const assignments: VideoAssignment[] = [];
    for (let i = 0; i < group.screen_count; i++) {
      assignments.push({ screen: i, file: "" });
    }
    setVideoAssignments(assignments);
  };

  // Handle video assignment change
  const handleVideoAssignmentChange = (screenIndex: number, fileName: string) => {
    setVideoAssignments(prev => 
      prev.map((assignment, index) => 
        index === screenIndex ? { ...assignment, file: fileName } : assignment
      )
    );
  };

  // Start multi-video streaming
  const handleStartMultiVideo = async () => {
    try {
      setIsStartingMultiVideo(true);
      
      // Validate that all screens have videos assigned
      const validAssignments = videoAssignments.filter(assignment => assignment.file);
      if (validAssignments.length !== group.screen_count) {
        throw new Error(`Please assign videos to all ${group.screen_count} screens`);
      }
      
      console.log(`🎬 Starting multi-video for group ${group.name} with assignments:`, validAssignments);
      
      // Call multi-video API
      const result = await api.group.startMultiVideoGroup(group.id, validAssignments, {
        screen_count: group.screen_count,
        orientation: group.orientation
      });
      
      console.log('✅ Multi-video started successfully:', result);
      
      // Update local streaming state immediately
      setLocalIsStreaming(true);
      
      // Update parent state
      if (onStreamingStatusChange) {
        onStreamingStatusChange(group.id, true);
      }
      
      // Auto-assign clients to screens
      try {
        await api.client.autoAssignScreens(group.id);
        console.log('✅ Auto-assigned clients to screens');
      } catch (assignError) {
        console.warn('⚠️ Auto-assign failed:', assignError);
      }
      
      setShowMultiVideoDialog(false);
      
      // Refresh the parent component data
      if (onRefresh) {
        onRefresh();
      }
      
    } catch (error) {
      console.error('❌ Error starting multi-video:', error);
      alert(`Failed to start multi-video: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsStartingMultiVideo(false);
    }
  };

  // Handle stop streaming
  const handleStopStreaming = async () => {
    try {
      setIsStoppingStream(true);
      
      console.log(`🛑 Stopping stream for group ${group.name}`);
      
      // Call the stop API directly
      await api.group.stopGroup(group.id);
      
      console.log('✅ Stream stopped successfully');
      
      // Update local streaming state immediately
      setLocalIsStreaming(false);
      
      // Update parent state
      if (onStreamingStatusChange) {
        onStreamingStatusChange(group.id, false);
      }
      
      // Refresh the parent component data
      if (onRefresh) {
        onRefresh();
      }
      
    } catch (error) {
      console.error('❌ Error stopping stream:', error);
      alert(`Failed to stop stream: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsStoppingStream(false);
    }
  };

  // Get orientation icon
  const getOrientationIcon = () => {
    switch (group.orientation) {
      case 'horizontal': return <Rows className="w-4 h-4" />;
      case 'vertical': return <Columns className="w-4 h-4" />;
      case 'grid': return <Grid3X3 className="w-4 h-4" />;
      default: return <Monitor className="w-4 h-4" />;
    }
  };

  // Determine if any operation is in progress
  const isAnyOperationInProgress = operationInProgress === group.id || isStartingMultiVideo || isStoppingStream;

  return (
    <div className="border rounded-lg overflow-hidden bg-white">
      <div className="p-4 border-b flex justify-between items-center">
        <div>
          <h3 className="font-medium text-lg flex items-center gap-2">
            {group.name}
            {group.docker_running ? (
              <Badge variant="outline" className="text-green-600 border-green-300">
                <Power className="w-3 h-3 mr-1" />
                Running
              </Badge>
            ) : (
              <Badge variant="outline" className="text-red-600 border-red-300">
                <AlertCircle className="w-3 h-3 mr-1" />
                Stopped
              </Badge>
            )}
          </h3>
          <p className="text-sm text-gray-500">{group.description || 'No description'}</p>
        </div>
        
        <div className="flex gap-2">
          {localIsStreaming ? (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleStopStreaming}
              disabled={isAnyOperationInProgress}
            >
              {isStoppingStream ? 'Stopping...' : (
                <>
                  <Square className="h-4 w-4 mr-2" />
                  Stop Stream
                </>
              )}
            </Button>
          ) : (
            <Dialog open={showMultiVideoDialog} onOpenChange={setShowMultiVideoDialog}>
              <DialogTrigger asChild>
                <Button
                  variant="default"
                  size="sm"
                  onClick={initializeVideoAssignments}
                  disabled={isAnyOperationInProgress || !group.docker_running}
                >
                  <Play className="h-4 w-4 mr-2" />
                  Start Multi-Video
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle>Multi-Video Setup - {group.name}</DialogTitle>
                </DialogHeader>
                
                <div className="space-y-4">
                  <div className="text-sm text-gray-600">
                    Assign one video file to each screen. Each screen will display its assigned video.
                  </div>
                  
                  <div className="grid gap-3">
                    {videoAssignments.map((assignment, index) => (
                      <div key={index} className="flex items-center gap-2">
                        <Label className="w-20 text-sm">Screen {index + 1}:</Label>
                        <Select
                          value={assignment.file}
                          onValueChange={(value) => handleVideoAssignmentChange(index, value)}
                        >
                          <SelectTrigger className="flex-1">
                            <SelectValue placeholder="Select video..." />
                          </SelectTrigger>
                          <SelectContent>
                            {videos.map((video) => (
                              <SelectItem key={video.name} value={video.name}>
                                {video.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    ))}
                  </div>
                  
                  <div className="text-xs text-gray-500">
                    Layout: {group.screen_count} screens in {group.orientation} orientation
                  </div>
                  
                  <div className="flex gap-2 pt-2">
                    <Button
                      onClick={handleStartMultiVideo}
                      disabled={isStartingMultiVideo || videoAssignments.some(a => !a.file)}
                      className="flex-1"
                    >
                      {isStartingMultiVideo ? 'Starting...' : 'Start Multi-Video'}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setShowMultiVideoDialog(false)}
                      disabled={isStartingMultiVideo}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          )}
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => onDelete(group.id, group.name)}
            disabled={isAnyOperationInProgress}
          >
            Delete
          </Button>
        </div>
      </div>
      
      <div className="p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-1">
            <h4 className="text-sm font-medium text-gray-700">Clients</h4>
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-gray-500" />
              <span className="text-sm">
                {clients.length} assigned ({group.active_clients || 0} active)
              </span>
            </div>
            
            {/* Show screen assignments for clients */}
            {clients.length > 0 && (
              <div className="mt-2 space-y-1">
                {clients.map((client) => (
                  <div key={client.client_id} className="text-xs text-gray-600">
                    {client.display_name || client.hostname} 
                    {client.screen_number !== undefined && (
                      <span className="ml-1 text-blue-600">→ Screen {client.screen_number + 1}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
          
          <div className="space-y-1">
            <h4 className="text-sm font-medium text-gray-700">Layout</h4>
            <div className="flex items-center gap-2 text-sm">
              {getOrientationIcon()}
              <span>{group.screen_count} screens • {group.orientation}</span>
            </div>
          </div>
          
          <div className="space-y-1">
            <h4 className="text-sm font-medium text-gray-700">Status</h4>
            <div className="text-sm">
              {localIsStreaming ? (
                <Badge variant="outline" className="text-green-600 border-green-300">
                  🔴 Streaming
                </Badge>
              ) : (
                <Badge variant="outline" className="text-gray-600 border-gray-300">
                  ⭕ Idle
                </Badge>
              )}
            </div>
          </div>
        </div>
        
        {/* Client Assignment */}
        {unassignedClients.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Assign Client to Group</h4>
            <Select
              onValueChange={(clientId) => onAssignClient(clientId, group.id)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a client to assign..." />
              </SelectTrigger>
              <SelectContent>
                {unassignedClients.map((client) => (
                  <SelectItem 
                    key={client.client_id} 
                    value={client.client_id}
                  >
                    {client.display_name || client.hostname || client.client_id}
                    {client.ip_address && ` (${client.ip_address})`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
        
        {/* Manual Screen Assignment (for existing clients) */}
        {clients.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Screen Assignments</h4>
            <div className="space-y-2">
              {clients.map((client) => (
                <div key={client.client_id} className="flex items-center gap-2 text-sm">
                  <span className="w-32 truncate">
                    {client.display_name || client.hostname}
                  </span>
                  <Select
                    value={client.screen_number?.toString() || ''}
                    onValueChange={async (value) => {
                      try {
                        await api.client.assignClientToScreen(
                          client.client_id, 
                          group.id, 
                          parseInt(value)
                        );
                        // Refresh clients or update state
                        if (onRefresh) {
                          onRefresh();
                        }
                      } catch (error) {
                        console.error('Error assigning screen:', error);
                        alert('Failed to assign client to screen');
                      }
                    }}
                  >
                    <SelectTrigger className="w-24">
                      <SelectValue placeholder="Screen" />
                    </SelectTrigger>
                    <SelectContent>
                      {Array.from({ length: group.screen_count }, (_, i) => (
                        <SelectItem key={i} value={i.toString()}>
                          Screen {i + 1}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ))}
            </div>
            
            {/* Auto-assign button for convenience */}
            {clients.some(c => c.screen_number === undefined) && (
              <div className="mt-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    try {
                      await api.client.autoAssignScreens(group.id);
                      if (onRefresh) {
                        onRefresh();
                      }
                    } catch (error) {
                      console.error('Error auto-assigning screens:', error);
                      alert('Failed to auto-assign screens');
                    }
                  }}
                  disabled={isAnyOperationInProgress}
                >
                  Auto-Assign Screens
                </Button>
              </div>
            )}
          </div>
        )}
        
        {/* Instructions */}
        {!localIsStreaming && clients.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <h4 className="text-sm font-medium text-blue-800 mb-1">How to use Multi-Video:</h4>
            <ol className="text-xs text-blue-700 space-y-1">
              <li>1. Click "Start Multi-Video" and assign videos to each screen</li>
              <li>2. Each client will automatically connect to their assigned screen</li>
              <li>3. Each screen displays different video content</li>
            </ol>
          </div>
        )}
        
        {/* Debug Info (remove in production) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="text-xs text-gray-400 border-t pt-2">
            Debug: localIsStreaming={localIsStreaming.toString()}, 
            initialIsStreaming={initialIsStreaming.toString()}, 
            operationInProgress={operationInProgress || 'none'}
          </div>
        )}
      </div>
    </div>
  );
};

export default GroupCard;
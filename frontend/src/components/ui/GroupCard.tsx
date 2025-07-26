// frontend/src/components/ui/GroupCard.tsx - Video assignments directly in group card

import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Square, Users, Monitor, Power, AlertCircle, Video as VideoIcon, Grid3X3, Rows, Columns, Play, RotateCcw, ChevronDown, ChevronUp } from "lucide-react";
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

// Helper function to get storage key for a group's video assignments
const getStorageKey = (groupId: string) => `video_assignments_${groupId}`;

// Helper function to save video assignments to localStorage
const saveVideoAssignments = (groupId: string, assignments: VideoAssignment[]) => {
  try {
    const key = getStorageKey(groupId);
    const data = {
      assignments,
      timestamp: Date.now(),
      version: '1.0'
    };
    localStorage.setItem(key, JSON.stringify(data));
    console.log(`💾 Saved video assignments for group ${groupId}:`, assignments);
  } catch (error) {
    console.warn('⚠️ Failed to save video assignments to localStorage:', error);
  }
};

// Helper function to load video assignments from localStorage
const loadVideoAssignments = (groupId: string, screenCount: number): VideoAssignment[] => {
  try {
    const key = getStorageKey(groupId);
    const stored = localStorage.getItem(key);
    
    if (stored) {
      const data = JSON.parse(stored);
      const assignments = data.assignments || [];
      
      // Validate that we have the right number of screens and structure
      if (Array.isArray(assignments) && assignments.length === screenCount) {
        // Validate each assignment has the correct structure
        const validAssignments = assignments.every((assignment, index) => 
          assignment && 
          typeof assignment === 'object' && 
          assignment.screen === index &&
          typeof assignment.file === 'string'
        );
        
        if (validAssignments) {
          console.log(`📂 Loaded video assignments for group ${groupId}:`, assignments);
          return assignments;
        }
      }
    }
  } catch (error) {
    console.warn('⚠️ Failed to load video assignments from localStorage:', error);
  }
  
  // Return empty assignments if loading failed or data is invalid
  return Array.from({ length: screenCount }, (_, index) => ({
    screen: index,
    file: ""
  }));
};

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
  const [videoAssignments, setVideoAssignments] = useState<VideoAssignment[]>([]);
  const [isStartingMultiVideo, setIsStartingMultiVideo] = useState(false);
  const [isStoppingStream, setIsStoppingStream] = useState(false);
  const [showVideoConfig, setShowVideoConfig] = useState(false);
  
  // Local streaming state that can be updated independently
  const [localIsStreaming, setLocalIsStreaming] = useState(initialIsStreaming);

  // Sync with parent prop changes
  useEffect(() => {
    setLocalIsStreaming(initialIsStreaming);
  }, [initialIsStreaming]);

  // Check streaming status periodically with better error handling
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
        // More graceful error handling - only log detailed error in development
        if (process.env.NODE_ENV === 'development') {
          console.error(`Error checking streaming status for group ${group.name}:`, error);
        } else {
          console.warn(`Unable to check streaming status for group ${group.name}`);
        }
        
        // Don't update streaming state on network errors to avoid false status changes
        // The status will be updated when the API call succeeds or when manually triggered
      }
    };

    // Check immediately and then every 10 seconds (reduced frequency to minimize network errors)
    checkStatus();
    const interval = setInterval(checkStatus, 10000);
    
    return () => clearInterval(interval);
  }, [group.id, localIsStreaming, onStreamingStatusChange, group.name]);

  // Load saved video assignments when group changes or component mounts
  useEffect(() => {
    const savedAssignments = loadVideoAssignments(group.id, group.screen_count);
    setVideoAssignments(savedAssignments);
    
    // Auto-expand video config if assignments exist
    const hasAssignments = savedAssignments.some(assignment => assignment.file);
    setShowVideoConfig(hasAssignments);
  }, [group.id, group.screen_count]);

  // Reset video assignments to empty
  const resetVideoAssignments = () => {
    const emptyAssignments: VideoAssignment[] = Array.from({ length: group.screen_count }, (_, index) => ({
      screen: index,
      file: ""
    }));
    setVideoAssignments(emptyAssignments);
    saveVideoAssignments(group.id, emptyAssignments);
  };

  // Handle video assignment change and save to localStorage
  const handleVideoAssignmentChange = (screenIndex: number, fileName: string) => {
    // Convert special clear value to empty string
    const actualFileName = fileName === "__CLEAR__" ? "" : fileName;
    
    const newAssignments = videoAssignments.map((assignment, index) => 
      index === screenIndex ? { ...assignment, file: actualFileName } : assignment
    );
    
    setVideoAssignments(newAssignments);
    
    // Save to localStorage immediately when user makes changes
    saveVideoAssignments(group.id, newAssignments);
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

  // Check if all screens have video assignments
  const hasCompleteAssignments = videoAssignments.every(assignment => assignment.file);
  
  // Check if any assignments exist
  const hasAnyAssignments = videoAssignments.some(assignment => assignment.file);

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
            <Button
              variant="default"
              size="sm"
              onClick={handleStartMultiVideo}
              disabled={isAnyOperationInProgress || !group.docker_running || !hasCompleteAssignments}
            >
              {isStartingMultiVideo ? 'Starting...' : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  {hasCompleteAssignments ? 'Start Multi-Video' : 'Setup Videos First'}
                </>
              )}
            </Button>
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

        {/* Video Assignment Configuration Section */}
        <div className="border rounded-lg overflow-hidden">
          <div 
            className="bg-gray-50 px-3 py-2 flex items-center justify-between cursor-pointer hover:bg-gray-100 transition-colors"
            onClick={() => setShowVideoConfig(!showVideoConfig)}
          >
            <div className="flex items-center gap-2">
              <VideoIcon className="w-4 h-4 text-gray-600" />
              <h4 className="text-sm font-medium text-gray-700">Video Assignments</h4>
              {hasAnyAssignments && (
                <Badge variant="outline" className="text-green-600 border-green-300 text-xs">
                  {videoAssignments.filter(a => a.file).length}/{group.screen_count}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2">
              {hasAnyAssignments && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    resetVideoAssignments();
                  }}
                  className="h-6 w-6 p-0"
                  title="Reset all assignments"
                >
                  <RotateCcw className="h-3 w-3" />
                </Button>
              )}
              {showVideoConfig ? (
                <ChevronUp className="w-4 h-4 text-gray-500" />
              ) : (
                <ChevronDown className="w-4 h-4 text-gray-500" />
              )}
            </div>
          </div>
          
          {showVideoConfig && (
            <div className="p-3 border-t bg-white space-y-3">
              <div className="text-xs text-gray-600">
                Assign one video file to each screen. Each screen will display its assigned video.
              </div>
              
              <div className="grid gap-2">
                {videoAssignments.map((assignment, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <Label className="w-16 text-xs">Screen {index + 1}:</Label>
                    <Select
                      value={assignment.file}
                      onValueChange={(value) => handleVideoAssignmentChange(index, value)}
                    >
                      <SelectTrigger className="flex-1 h-8 text-xs">
                        <SelectValue placeholder="Select video..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__CLEAR__">
                          <span className="text-gray-400">Clear assignment</span>
                        </SelectItem>
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
              
              {hasAnyAssignments && (
                <div className="bg-green-50 border border-green-200 rounded p-2">
                  <div className="text-xs text-green-800 font-medium">
                    ✅ {videoAssignments.filter(a => a.file).length} of {group.screen_count} screens configured
                  </div>
                  {!hasCompleteAssignments && (
                    <div className="text-xs text-green-600 mt-1">
                      ⚠️ {group.screen_count - videoAssignments.filter(a => a.file).length} screens still need video assignments
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
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
                  
                  {/* Status indicator */}
                  <div className="flex items-center gap-2 flex-1">
                    <Select
                      value={client.screen_number !== undefined && client.screen_number !== null ? client.screen_number.toString() : 'unassigned'}
                      onValueChange={async (value) => {
                        try {
                          if (value === 'unassigned') {
                            // Unassign client from screen
                            await api.client.unassignClientFromScreen(client.client_id);
                          } else {
                            // Assign client to screen
                            await api.client.assignClientToScreen(
                              client.client_id,
                              group.id,
                              parseInt(value)
                            );
                          }
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
                      <SelectTrigger className="w-32">
                        <SelectValue placeholder="No screen" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="unassigned">
                          <span className="text-gray-400">No screen</span>
                        </SelectItem>
                        {Array.from({ length: group.screen_count }, (_, i) => (
                          <SelectItem key={i} value={i.toString()}>
                            Screen {i + 1}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    
                    {/* Visual status indicator */}
                    {client.screen_number !== undefined ? (
                      <Badge variant="outline" className="text-green-600 border-green-300 text-xs">
                        ✅ Screen {client.screen_number + 1}
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-yellow-600 border-yellow-300 text-xs">
                        ⏳ Unassigned
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
            
            {/* Summary */}
            <div className="mt-3 p-2 bg-gray-50 rounded text-xs text-gray-600">
              Assigned: {clients.filter(c => c.screen_number !== undefined).length} / {clients.length} clients
              {clients.filter(c => c.screen_number !== undefined).length < clients.length && 
                " • Some clients need screen assignments"}
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
                  className="text-xs"
                >
                  Auto-Assign Remaining Screens
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
              <li>1. Configure video assignments above (saved automatically)</li>
              <li>2. Click "Start Multi-Video" to begin streaming</li>
              <li>3. Each client will display their assigned screen's video</li>
            </ol>
          </div>
        )}
        
        {/* Debug Info (remove in production) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="text-xs text-gray-400 border-t pt-2">
            Debug: localIsStreaming={localIsStreaming.toString()}, 
            initialIsStreaming={initialIsStreaming.toString()}, 
            operationInProgress={operationInProgress || 'none'},
            hasAssignments={hasAnyAssignments.toString()},
            completeAssignments={hasCompleteAssignments.toString()},
            apiBaseUrl={import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001'}
          </div>
        )}
      </div>
    </div>
  );
};

export default GroupCard;
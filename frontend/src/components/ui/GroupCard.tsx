// frontend/src/components/ui/GroupCard.tsx - Integrated Compact Design with Streaming Mode Features

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from './button';
import { Badge } from './badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './dialog';
import { Label } from './label';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { 
  Users, Monitor, Grid3X3, Play, Square, Video, Copy, ChevronDown, ChevronUp, 
  RotateCcw, Power, AlertCircle, Rows, Columns, VideoIcon, Layers, MoreVertical, 
  Settings, Info, Container, Wifi, CheckCircle
} from 'lucide-react';
import { Group, Client, Video as VideoType } from '../../types';

// Use the existing API structure from the project
import { api } from '../../API/api';

interface GroupCardProps {
  group: Group;
  clients: Client[];
  videos: VideoType[];
  unassignedClients?: Client[];
  onDelete: (groupId: string, groupName: string) => void;
  onStreamingStatusChange?: (groupId: string, isStreaming: boolean) => void;
  onRefresh?: () => void;
  onAssignClient?: (clientId: string, groupId: string) => void;
}

interface VideoAssignment {
  screen: number;
  file: string;
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

const GroupCard: React.FC<GroupCardProps> = ({
  group,
  clients,
  videos,
  unassignedClients = [],
  onDelete,
  onStreamingStatusChange,
  onRefresh,
  onAssignClient
}) => {
  // Debug log to see what data is received
  console.log(`🔍 GroupCard - Group "${group.name || 'Unknown'}":`, {
    id: group.id,
    name: group.name,
    streaming_mode: group.streaming_mode,
    docker_running: group.docker_running,
    docker_status: group.docker_status,
    total_clients: clients.length,
    active_clients: clients.filter(c => c.status === 'active').length,
    ports: group.ports,
    container_id: group.container_id,
    rawGroup: group
  });

  // Safety check - if essential fields are missing, show error state
  if (!group.id || !group.name) {
    return (
      <Card className="bg-red-50 border border-red-200">
        <CardContent className="p-3">
          <div className="flex items-center gap-2 text-red-800">
            <AlertCircle className="h-4 w-4" />
            <span className="font-medium text-sm">Invalid Group Data</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  const [localIsStreaming, setLocalIsStreaming] = useState(group.status === 'active');
  const [operationInProgress, setOperationInProgress] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Video assignment states with localStorage persistence
  const [videoAssignments, setVideoAssignments] = useState<VideoAssignment[]>([]);
  const [showVideoConfig, setShowVideoConfig] = useState(false);
  
  // Multi-video mode states
  const [showMultiVideoDialog, setShowMultiVideoDialog] = useState(false);
  const [isStartingMultiVideo, setIsStartingMultiVideo] = useState(false);
  
  // Single video split mode states
  const [showSingleVideoDialog, setShowSingleVideoDialog] = useState(false);
  const [selectedVideoFile, setSelectedVideoFile] = useState<string>('');
  const [isStartingSingleVideo, setIsStartingSingleVideo] = useState(false);

  // Streaming mode dropdown state
  const [showStreamingModeDropdown, setShowStreamingModeDropdown] = useState(false);

  const isStoppingStream = operationInProgress === 'stopping';
  const isAnyOperationInProgress = operationInProgress !== null || isStartingMultiVideo || isStartingSingleVideo;

  // Load saved video assignments when group changes or component mounts
  useEffect(() => {
    const savedAssignments = loadVideoAssignments(group.id, group.screen_count);
    setVideoAssignments(savedAssignments);
    
    // Auto-expand video config if assignments exist
    const hasAssignments = savedAssignments.some(assignment => assignment.file);
    setShowVideoConfig(hasAssignments);
  }, [group.id, group.screen_count]);

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
        // More graceful error handling
        if (process.env.NODE_ENV === 'development') {
          console.error(`Error checking streaming status for group ${group.name}:`, error);
        }
      }
    };

    // Check immediately and then every 10 seconds
    checkStatus();
    const interval = setInterval(checkStatus, 10000);
    
    return () => clearInterval(interval);
  }, [group.id, localIsStreaming, onStreamingStatusChange, group.name]);

  // Determine if streaming can be started (Docker must be running)
  const canStartStreaming = group.docker_running && !isAnyOperationInProgress;
  const canStopStreaming = group.docker_running && !isStoppingStream;

  const getOrientationIcon = () => {
    switch (group.orientation) {
      case 'horizontal':
        return <Rows className="w-4 h-4" />;
      case 'vertical':
        return <Columns className="w-4 h-4" />;
      case 'grid':
        return <Grid3X3 className="w-4 h-4" />;
      default:
        return <Monitor className="w-4 h-4" />;
    }
  };

  // Get streaming mode icon based on group's streaming_mode
  const getStreamingModeIcon = () => {
    switch (group.streaming_mode) {
      case 'single_video_split':
        return <Copy className="w-4 h-4 text-blue-600" />;
      case 'multi_video':
        return <VideoIcon className="w-4 h-4 text-purple-600" />;
      default:
        return <Layers className="w-4 h-4 text-gray-600" />;
    }
  };

  // Get streaming mode badge (compact display)
  const getStreamingModeBadge = () => {
    const mode = group.streaming_mode || 'multi_video';
    const isActive = localIsStreaming;
    
    if (mode === 'single_video_split') {
      return (
        <Badge 
          variant={isActive ? "default" : "secondary"} 
          className={`${isActive ? 'bg-blue-600 text-white border-blue-600' : 'bg-blue-100 text-blue-700 border-blue-300'} text-xs`}
        >
          <Copy className="w-3 h-3 mr-1" />
          Split
          {isActive && <div className="w-1.5 h-1.5 bg-white rounded-full ml-1 animate-pulse" />}
        </Badge>
      );
    } else {
      return (
        <Badge 
          variant={isActive ? "default" : "secondary"} 
          className={`${isActive ? 'bg-purple-600 text-white border-purple-600' : 'bg-purple-100 text-purple-700 border-purple-300'} text-xs`}
        >
          <VideoIcon className="w-3 h-3 mr-1" />
          Multi
          {isActive && <div className="w-1.5 h-1.5 bg-white rounded-full ml-1 animate-pulse" />}
        </Badge>
      );
    }
  };

  // Status indicators
  const getDockerStatusBadge = () => {
    if (group.docker_running) {
      return <Badge variant="default" className="bg-green-100 text-green-800 text-xs">Running</Badge>;
    } else {
      return <Badge variant="destructive" className="text-xs">Stopped</Badge>;
    }
  };

  const getStreamingStatusBadge = () => {
    if (localIsStreaming) {
      return <Badge variant="default" className="bg-blue-100 text-blue-800 text-xs">Streaming</Badge>;
    } else if (group.docker_running) {
      return <Badge variant="outline" className="text-xs">Ready</Badge>;
    } else {
      return <Badge variant="secondary" className="text-xs">Offline</Badge>;
    }
  };

  // Get streaming mode description for dropdown
  const getStreamingModeDescription = () => {
    const mode = group.streaming_mode || 'multi_video';
    
    if (mode === 'multi_video') {
      return {
        title: "Multi-Video Mode",
        description: "Each screen displays different content. You must assign a separate video file to each screen before streaming can begin.",
        requirements: [
          `Assign ${group.screen_count} different video files`,
          "One video per screen",
          "Each screen shows unique content"
        ],
        canStart: hasCompleteAssignments
      };
    } else {
      return {
        title: "Single Video Split Mode", 
        description: "One video is automatically divided into equal sections across all screens. You must assign one video file to the group.",
        requirements: [
          "Assign 1 video file to the group",
          `Video split into ${group.screen_count} equal sections`,
          "All screens show synchronized content"
        ],
        canStart: selectedVideoFile !== ''
      };
    }
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

  // Reset video assignments to empty
  const resetVideoAssignments = () => {
    const emptyAssignments: VideoAssignment[] = Array.from({ length: group.screen_count }, (_, index) => ({
      screen: index,
      file: ""
    }));
    setVideoAssignments(emptyAssignments);
    saveVideoAssignments(group.id, emptyAssignments);
  };

  // Handle multi-video mode - using existing startMultiVideoGroup API
  const handleStartMultiVideo = async () => {
    try {
      setIsStartingMultiVideo(true);
      
      const validAssignments = videoAssignments.filter(assignment => assignment.file);
      if (validAssignments.length !== group.screen_count) {
        throw new Error(`Please assign videos to all ${group.screen_count} screens`);
      }
      
      console.log(`🎬 Starting multi-video for group ${group.name} with assignments:`, validAssignments);
      
      const result = await api.group.startMultiVideoGroup(group.id, validAssignments, {
        screen_count: group.screen_count,
        orientation: group.orientation
      });
      
      console.log('✅ Multi-video started successfully:', result);
      
      setLocalIsStreaming(true);
      if (onStreamingStatusChange) {
        onStreamingStatusChange(group.id, true);
      }
      
      // Try auto-assign clients to screens if API exists
      try {
        await api.client.autoAssignScreens(group.id);
        console.log('✅ Auto-assigned clients to screens');
      } catch (assignError) {
        console.warn('⚠️ Auto-assign not available yet:', assignError);
      }
      
      setShowMultiVideoDialog(false);
      if (onRefresh) onRefresh();
      
    } catch (error) {
      console.error('❌ Error starting multi-video:', error);
      alert(`Failed to start multi-video: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsStartingMultiVideo(false);
    }
  };

  // Handle single video split mode
  const handleStartSingleVideoSplit = async () => {
    try {
      setIsStartingSingleVideo(true);
      
      if (!selectedVideoFile) {
        throw new Error('Please select a video file');
      }
      
      console.log(`🎬 Starting single video split for group ${group.name} with video: ${selectedVideoFile}`);
      
      const result = await api.group.startSingleVideoSplit(group.id, {
        video_file: selectedVideoFile,
        screen_count: group.screen_count,
        orientation: group.orientation,
        enable_looping: true
      });
      
      console.log('✅ Single video split started successfully:', result);
      
      setLocalIsStreaming(true);
      if (onStreamingStatusChange) {
        onStreamingStatusChange(group.id, true);
      }
      
      // Try auto-assign clients to screens if API exists
      try {
        await api.client.autoAssignScreens(group.id);
        console.log('✅ Auto-assigned clients to screens');
      } catch (assignError) {
        console.warn('⚠️ Auto-assign not available yet:', assignError);
      }
      
      setShowSingleVideoDialog(false);
      if (onRefresh) onRefresh();
      
    } catch (error) {
      console.error('❌ Error starting single video split:', error);
      alert(`Failed to start single video split: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsStartingSingleVideo(false);
    }
  };

  const handleStopStreaming = async () => {
    try {
      setOperationInProgress('stopping');
      console.log(`🛑 Stopping stream for group ${group.name}`);
      
      await api.group.stopGroup(group.id);
      console.log('✅ Stream stopped successfully');
      
      setLocalIsStreaming(false);
      if (onStreamingStatusChange) {
        onStreamingStatusChange(group.id, false);
      }
      
      if (onRefresh) onRefresh();
      
    } catch (error) {
      console.error('❌ Error stopping stream:', error);
      alert(`Failed to stop stream: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setOperationInProgress(null);
    }
  };

  // Check if all screens have video assignments
  const hasCompleteAssignments = videoAssignments.every(assignment => assignment.file);
  
  // Check if any assignments exist
  const hasAnyAssignments = videoAssignments.some(assignment => assignment.file);

  return (
    <Card className="bg-white border border-gray-200">
      {/* Dropdown overlay */}
      {showStreamingModeDropdown && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setShowStreamingModeDropdown(false)}
        />
      )}

      {/* Compact Header */}
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <Container className="h-4 w-4 text-blue-600 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <CardTitle className="text-lg text-gray-800 truncate">{group.name}</CardTitle>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-gray-500">
                  {group.screen_count} screens • {group.orientation}
                </span>
                <span className="text-xs text-gray-400">•</span>
                <span className="text-xs text-gray-500">
                  Port {group.ports?.srt_port || 'N/A'}
                </span>
              </div>
            </div>
          </div>
          
          {/* Status and Actions */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {getDockerStatusBadge()}
            {getStreamingModeBadge()}
            {getStreamingStatusBadge()}
            
            {/* Main Action Button */}
            {localIsStreaming ? (
              <Button
                onClick={handleStopStreaming}
                disabled={!canStopStreaming}
                variant="destructive"
                size="sm"
              >
                <Square className="h-3 w-3 mr-1" />
                {isStoppingStream ? 'Stopping...' : 'Stop'}
              </Button>
            ) : (
              <>
                {group.streaming_mode === 'multi_video' ? (
                  <Button
                    size="sm"
                    onClick={() => {
                      // Use inline video config if we have complete assignments
                      if (hasCompleteAssignments) {
                        handleStartMultiVideo();
                      } else {
                        setShowMultiVideoDialog(true);
                      }
                    }}
                    disabled={!canStartStreaming}
                  >
                    <Play className="h-3 w-3 mr-1" />
                    {hasCompleteAssignments ? 'Start' : 'Setup'}
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    onClick={() => setShowSingleVideoDialog(true)}
                    disabled={!canStartStreaming}
                  >
                    <Play className="h-3 w-3 mr-1" />
                    Start
                  </Button>
                )}
              </>
            )}
            
            {/* Expand/Collapse Button */}
            <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="sm" className="p-1">
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </Button>
              </CollapsibleTrigger>
            </Collapsible>
          </div>
        </div>

        {/* Quick Stats Bar */}
        <div className="flex items-center gap-4 mt-2 text-xs text-gray-600">
          <div className="flex items-center gap-1">
            <Users className="h-3 w-3" />
            <span>{clients.filter(c => c.status === 'active').length}/{clients.length} clients</span>
          </div>
          {localIsStreaming && (
            <div className="flex items-center gap-1">
              <CheckCircle className="h-3 w-3 text-green-600" />
              <span className="text-green-600">Streaming active</span>
            </div>
          )}
          {!group.docker_running && (
            <div className="flex items-center gap-1">
              <AlertCircle className="h-3 w-3 text-red-600" />
              <span className="text-red-600">Docker offline</span>
            </div>
          )}
        </div>
      </CardHeader>

      {/* Expandable Content */}
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CollapsibleContent>
          <CardContent className="pt-0 space-y-4">
            {/* Enhanced Streaming Mode Section with Dropdown */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-700">Streaming Configuration</label>
                <div className="relative">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowStreamingModeDropdown(!showStreamingModeDropdown)}
                    className="h-6 w-6 p-0"
                  >
                    <MoreVertical className="h-3 w-3" />
                  </Button>
                  
                  {showStreamingModeDropdown && (
                    <div className="absolute right-0 top-full mt-1 z-50 bg-white border border-gray-200 rounded-lg shadow-lg min-w-80 p-4">
                      <div className="space-y-3">
                        {/* Header */}
                        <div className="flex items-center gap-2 pb-2 border-b">
                          <Settings className="w-4 h-4 text-blue-600" />
                          <h5 className="font-medium text-gray-900">Streaming Configuration</h5>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setShowStreamingModeDropdown(false)}
                            className="ml-auto h-5 w-5 p-0"
                          >
                            ×
                          </Button>
                        </div>
                        
                        {/* Current Mode Info */}
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            {getStreamingModeIcon()}
                            <span className="font-medium">{getStreamingModeDescription().title}</span>
                            {localIsStreaming && (
                              <div className="flex items-center gap-1">
                                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                                <span className="text-xs text-green-600 font-medium">Active</span>
                              </div>
                            )}
                          </div>
                          
                          <p className="text-sm text-gray-600">
                            {getStreamingModeDescription().description}
                          </p>
                        </div>
                        
                        {/* Requirements */}
                        <div className="space-y-2">
                          <h6 className="text-sm font-medium text-gray-700 flex items-center gap-1">
                            <Info className="w-3 h-3" />
                            Requirements
                          </h6>
                          <ul className="text-xs text-gray-600 space-y-1">
                            {getStreamingModeDescription().requirements.map((req, index) => (
                              <li key={index} className="flex items-start gap-2">
                                <span className="text-blue-600">•</span>
                                <span>{req}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                        
                        {/* Status */}
                        <div className={`p-2 rounded text-sm ${
                          getStreamingModeDescription().canStart 
                            ? 'bg-green-50 border border-green-200 text-green-800' 
                            : 'bg-yellow-50 border border-yellow-200 text-yellow-800'
                        }`}>
                          {getStreamingModeDescription().canStart ? (
                            <div className="flex items-center gap-2">
                              <span className="text-green-600">✓</span>
                              Ready to start streaming
                            </div>
                          ) : (
                            <div className="flex items-center gap-2">
                              <span className="text-yellow-600">⚠</span>
                              {group.streaming_mode === 'multi_video' 
                                ? `Need ${group.screen_count - videoAssignments.filter(a => a.file).length} more video assignments`
                                : 'Need to select a video file'}
                            </div>
                          )}
                        </div>
                        
                        {/* Quick Actions */}
                        {!localIsStreaming && (
                          <div className="pt-2 border-t space-y-2">
                            <h6 className="text-sm font-medium text-gray-700">Quick Actions</h6>
                            
                            {group.streaming_mode === 'multi_video' ? (
                              <div className="space-y-2">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => {
                                    setShowStreamingModeDropdown(false);
                                    setShowVideoConfig(true);
                                  }}
                                  className="w-full text-xs"
                                >
                                  Configure Video Assignments
                                </Button>
                                
                                {hasCompleteAssignments && (
                                  <Button
                                    size="sm"
                                    onClick={() => {
                                      setShowStreamingModeDropdown(false);
                                      handleStartMultiVideo();
                                    }}
                                    className="w-full text-xs"
                                  >
                                    Start Multi-Video Streaming
                                  </Button>
                                )}
                              </div>
                            ) : (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                  setShowStreamingModeDropdown(false);
                                  setShowSingleVideoDialog(true);
                                }}
                                className="w-full text-xs"
                              >
                                Select Video & Start Streaming
                              </Button>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="flex items-center gap-2 text-sm">
                {getStreamingModeIcon()}
                <span>{group.streaming_mode === 'multi_video' ? 'Multi-Video Mode' : 'Single Video Split Mode'}</span>
              </div>
            </div>

            {/* Docker Details */}
            <div className="p-2 bg-blue-50 rounded text-xs">
              <div className="font-medium text-blue-800 mb-1">Container Info</div>
              <div className="grid grid-cols-2 gap-1 text-blue-700">
                <span>ID: {group.container_id ? group.container_id.substring(0, 8) : 'N/A'}</span>
                <span>Status: {group.docker_status || 'unknown'}</span>
              </div>
            </div>

            {/* Video Assignment Configuration Section - only for multi-video mode */}
            {group.streaming_mode === 'multi_video' && (
              <div className="border rounded-lg overflow-hidden">
                <div 
                  className="bg-gray-50 px-3 py-2 flex items-center justify-between cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => setShowVideoConfig(!showVideoConfig)}
                >
                  <div className="flex items-center gap-2">
                    <Video className="w-4 h-4 text-gray-600" />
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
                            value={assignment.file || ""}
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
            )}

            {/* Assigned Clients (Compact) */}
            {clients.length > 0 && (
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Assigned Clients ({clients.length})
                </label>
                <div className="space-y-1 max-h-24 overflow-y-auto">
                  {clients.map((client) => (
                    <div key={client.client_id} className="flex items-center justify-between p-1.5 bg-gray-50 rounded text-xs">
                      <div className="flex items-center gap-1.5 min-w-0 flex-1">
                        <Wifi className={`h-3 w-3 flex-shrink-0 ${client.status === 'active' ? 'text-green-500' : 'text-gray-400'}`} />
                        <span className="font-medium truncate">
                          {client.display_name || client.hostname}
                        </span>
                        <span className="text-gray-500">({client.ip_address})</span>
                      </div>
                      <Badge variant={client.status === 'active' ? "default" : "secondary"} className="text-xs py-0 px-1">
                        {client.status === 'active' ? "Online" : "Offline"}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Quick Assign Unassigned Clients */}
            {unassignedClients.length > 0 && onAssignClient && (
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Quick Assign ({unassignedClients.length} available)
                </label>
                <div className="grid grid-cols-1 gap-1 max-h-20 overflow-y-auto">
                  {unassignedClients.slice(0, 2).map((client) => (
                    <div key={client.client_id} className="flex items-center justify-between p-1.5 bg-yellow-50 rounded text-xs">
                      <div className="flex items-center gap-1.5 min-w-0 flex-1">
                        <Wifi className={`h-3 w-3 flex-shrink-0 ${client.status === 'active' ? 'text-green-500' : 'text-gray-400'}`} />
                        <span className="truncate">{client.display_name || client.hostname}</span>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-6 px-2 text-xs"
                        onClick={() => onAssignClient(client.client_id, group.id)}
                        disabled={operationInProgress === `assign-${client.client_id}`}
                      >
                        {operationInProgress === `assign-${client.client_id}` ? '...' : 'Assign'}
                      </Button>
                    </div>
                  ))}
                  {unassignedClients.length > 2 && (
                    <div className="text-center text-gray-500 text-xs py-1">
                      +{unassignedClients.length - 2} more available
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Error Messages */}
            {!group.docker_running && (
              <div className="p-2 bg-red-50 rounded text-xs">
                <div className="flex items-center gap-1 text-red-800 font-medium">
                  <AlertCircle className="h-3 w-3" />
                  <span>Docker Required</span>
                </div>
                <p className="text-red-700 mt-1">
                  Container must be running to start streaming.
                </p>
              </div>
            )}

            {/* Single Video Split Mode Info */}
            {group.streaming_mode === 'single_video_split' && !localIsStreaming && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Copy className="w-4 h-4 text-blue-600" />
                  <h4 className="text-sm font-medium text-blue-800">Single Video Split Mode</h4>
                </div>
                <p className="text-xs text-blue-700">
                  One video will be automatically divided into {group.screen_count} equal sections 
                  and distributed {group.orientation === 'horizontal' ? 'side-by-side' : 'top-to-bottom'} 
                  across all screens. Click "Start" to select and begin streaming.
                </p>
              </div>
            )}

            {/* Advanced Actions */}
            <div className="flex gap-2 pt-2 border-t">
              <Button
                onClick={() => onDelete(group.id, group.name)}
                disabled={isAnyOperationInProgress}
                variant="outline"
                size="sm"
                className="text-red-600 hover:text-red-700 hover:bg-red-50 text-xs"
              >
                Delete Group
              </Button>
              
              {localIsStreaming && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs"
                  onClick={() => setIsExpanded(false)}
                >
                  <Settings className="h-3 w-3 mr-1" />
                  Stream URLs
                </Button>
              )}
            </div>

            {/* Stream URLs (when active) */}
            {localIsStreaming && group.available_streams && group.available_streams.length > 0 && (
              <div className="p-2 bg-green-50 rounded text-xs">
                <div className="font-medium text-green-800 mb-1">Active Streams</div>
                <div className="space-y-1 max-h-16 overflow-y-auto">
                  {group.available_streams.slice(0, 1).map((streamPath, index) => (
                    <div key={index} className="font-mono bg-white p-1 rounded border text-xs break-all">
                      srt://127.0.0.1:{group.ports?.srt_port || 10080}?streamid=#!::r={streamPath},m=request
                    </div>
                  ))}
                  {group.available_streams.length > 1 && (
                    <div className="text-green-700">
                      +{group.available_streams.length - 1} more streams available
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>

      {/* Multi-Video Dialog - fallback for incomplete assignments */}
      {showMultiVideoDialog && group.streaming_mode === 'multi_video' && (
        <Dialog open={showMultiVideoDialog} onOpenChange={setShowMultiVideoDialog}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Configure Multi-Video Streaming</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Assign a different video to each screen. Each client will display different content.
              </p>
              
              <div className="space-y-3">
                {videoAssignments.map((assignment, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <div className="w-20 text-sm font-medium">
                      Screen {index + 1}:
                    </div>
                    <Select
                      value={assignment.file || ""}
                      onValueChange={(value) => handleVideoAssignmentChange(index, value)}
                    >
                      <SelectTrigger className="flex-1">
                        <SelectValue placeholder="Select video file" />
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
              
              <div className="flex justify-end gap-2">
                <Button
                  onClick={handleStartMultiVideo}
                  disabled={isStartingMultiVideo || videoAssignments.filter(a => a.file).length !== group.screen_count}
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

      {/* Single Video Split Dialog */}
      {showSingleVideoDialog && group.streaming_mode === 'single_video_split' && (
        <Dialog open={showSingleVideoDialog} onOpenChange={setShowSingleVideoDialog}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Configure Single Video Split</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Select one video that will be automatically split into {group.screen_count} sections 
                and distributed {group.orientation === 'horizontal' ? 'side-by-side' : 'top-to-bottom'} 
                across all screens.
              </p>
              
              <div className="space-y-2">
                <Label className="text-sm font-medium">Video File:</Label>
                <Select
                  value={selectedVideoFile || ""}
                  onValueChange={setSelectedVideoFile}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select video file to split" />
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

              <div className="bg-blue-50 p-3 rounded border-l-4 border-blue-400">
                <p className="text-sm text-blue-800">
                  The video will be automatically cropped into {group.screen_count} equal {group.orientation} sections. 
                  Each client will receive their designated section.
                </p>
              </div>
              
              <div className="flex justify-end gap-2">
                <Button
                  onClick={handleStartSingleVideoSplit}
                  disabled={isStartingSingleVideo || !selectedVideoFile}
                >
                  {isStartingSingleVideo ? 'Starting...' : 'Start Single Video Split'}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setShowSingleVideoDialog(false)}
                  disabled={isStartingSingleVideo}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Debug Info (remove in production) */}
      {process.env.NODE_ENV === 'development' && (
        <div className="text-xs text-gray-400 border-t pt-2 px-4 pb-2">
          Debug: localIsStreaming={localIsStreaming.toString()}, 
          operationInProgress={operationInProgress || 'none'},
          hasAssignments={hasAnyAssignments.toString()},
          completeAssignments={hasCompleteAssignments.toString()},
          dockerRunning={group.docker_running?.toString() || 'unknown'},
          streamingMode={group.streaming_mode || 'undefined'}
        </div>
      )}
    </Card>
  );
};

export default GroupCard;
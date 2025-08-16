// frontend/src/components/ui/GroupCard/GroupCardHeader.tsx

import React from 'react';
import { CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from '../button';
import { Badge } from '../badge';
import { Collapsible, CollapsibleTrigger } from "@/components/ui/collapsible";
import { 
  Users, Play, Square, Container, CheckCircle, AlertCircle, 
  ChevronDown, ChevronUp, Copy, VideoIcon
} from 'lucide-react';
import { Group, Client } from '../../../types';
import { VideoAssignment } from './types';

interface GroupCardHeaderProps {
  group: Group;
  clients: Client[];
  localIsStreaming: boolean;
  operationInProgress: string | null;
  hasCompleteAssignments: boolean;
  selectedVideoFile: string;
  isExpanded: boolean;
  setIsExpanded: (expanded: boolean) => void;
  setShowMultiVideoDialog: (show: boolean) => void;
  setShowSingleVideoDialog: (show: boolean) => void;
  handleStartMultiVideo: () => void;
  handleStartSingleVideoSplit: () => void;
  handleStopStreaming: () => void;
  isStartingMultiVideo: boolean;
  isStartingSingleVideo: boolean;
  videoAssignments: VideoAssignment[]; // Add this prop for video assignment status
}

const GroupCardHeader: React.FC<GroupCardHeaderProps> = ({
  group,
  clients,
  localIsStreaming,
  operationInProgress,
  hasCompleteAssignments,
  selectedVideoFile,
  isExpanded,
  setIsExpanded,
  setShowMultiVideoDialog,
  setShowSingleVideoDialog,
  handleStartMultiVideo,
  handleStartSingleVideoSplit,
  handleStopStreaming,
  isStartingMultiVideo,
  isStartingSingleVideo,
  videoAssignments
}) => {
  const isStoppingStream = operationInProgress === 'stopping';
  const isAnyOperationInProgress = operationInProgress !== null || isStartingMultiVideo || isStartingSingleVideo;
  
  // Determine if streaming can be started based on mode
  const canStartStreaming = group.docker_running && !isAnyOperationInProgress && (
    group.streaming_mode === 'single_video_split' 
      ? !!selectedVideoFile  // Single video split only needs 1 video selected
      : hasCompleteAssignments  // Multi-video needs all screens to have videos
  );
  const canStopStreaming = group.docker_running && !isStoppingStream;

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

  return (
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
                  title={!hasCompleteAssignments ? "All screens must have videos assigned for multi-video streaming" : ""}
                >
                  <Play className="h-3 w-3 mr-1" />
                  {hasCompleteAssignments ? 'Start' : `${group.screen_count - videoAssignments.filter(a => a.file).length} Videos Missing`}
                </Button>
              ) : (
                <Button
                  size="sm"
                  onClick={() => {
                    // If video is selected, start directly; otherwise show dialog
                    if (selectedVideoFile) {
                      handleStartSingleVideoSplit();
                    } else {
                      setShowSingleVideoDialog(true);
                    }
                  }}
                  disabled={!canStartStreaming}
                  title={!selectedVideoFile ? "Select a video file to start streaming" : ""}
                >
                  <Play className="h-3 w-3 mr-1" />
                  {selectedVideoFile ? 'Start' : 'Select Video'}
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

      {/* Video Assignment Status - Only show for multi-video mode */}
      {!localIsStreaming && group.docker_running && group.streaming_mode === 'multi_video' && !hasCompleteAssignments && (
        <div className="flex items-center gap-2 mt-2 text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
          <AlertCircle className="h-3 w-3" />
          <span>
            {group.screen_count - videoAssignments.filter(a => a.file).length} of {group.screen_count} screens need videos assigned
          </span>
        </div>
      )}

      {/* Single Video Status - Only show for single video split mode */}
      {!localIsStreaming && group.docker_running && group.streaming_mode === 'single_video_split' && !selectedVideoFile && (
        <div className="flex items-center gap-2 mt-2 text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
          <AlertCircle className="h-3 w-3" />
          <span>
            Select a video file to start split-screen streaming
          </span>
        </div>
        )}

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
  );
};

export default GroupCardHeader;
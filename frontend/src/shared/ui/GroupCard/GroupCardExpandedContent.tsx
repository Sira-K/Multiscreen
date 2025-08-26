// frontend/src/components/ui/GroupCard/GroupCardExpandedContent.tsx

import React from 'react';
import { CardContent } from "@/shared/ui/card";
import { Button } from "@/shared/ui/button";
import { Badge } from "@/shared/ui/badge";
import { AlertCircle } from 'lucide-react';
import { Group, Client, Video as VideoType } from '@/shared/types';

// Import sub-components
import StreamingModeSection from './sections/StreamingModeSection';
import DockerInfoSection from './sections/DockerInfoSection';
import VideoConfigurationSection from './sections/VideoConfigurationSection';
import AssignedClientsSection from './sections/AssignedClientsSection';
import ClientAssignmentSection from './sections/ClientAssignmentSection';
import ActiveStreamsSection from './sections/ActiveStreamsSection';
import { VideoAssignment } from './types';

interface GroupCardExpandedContentProps {
  group: Group;
  clients: Client[];
  videos: VideoType[];
  unassignedClients: Client[];
  localIsStreaming: boolean;
  operationInProgress: string | null;
  videoAssignments: VideoAssignment[];
  showVideoConfig: boolean;
  setShowVideoConfig: (show: boolean) => void;
  selectedVideoFile: string;
  setSelectedVideoFile: (file: string) => void;
  handleVideoAssignmentChange: (screenIndex: number, fileName: string) => void;
  resetVideoAssignments: () => void;
  hasCompleteAssignments: boolean;
  hasAnyAssignments: boolean;
  onDelete: (groupId: string, groupName: string) => void;
  onAssignClient?: (clientId: string, groupId: string) => void;
  
  // 🆕 Screen assignment props
  onAssignClientToScreen?: (clientId: string, groupId: string, screenNumber: number) => Promise<void>;
  onUnassignClientFromScreen?: (clientId: string) => Promise<void>;
  onAutoAssignScreens?: (groupId: string) => Promise<void>;
  getScreenAssignments?: (groupId: string) => Promise<any>;
  screenAssignmentInfo?: {
    allGroupClients: Client[];
    assignedToScreens: Client[];
    unassignedToScreens: Client[];
  };
}

const GroupCardExpandedContent: React.FC<GroupCardExpandedContentProps> = ({
  group,
  clients,
  videos,
  unassignedClients,
  localIsStreaming,
  operationInProgress,
  videoAssignments,
  showVideoConfig,
  setShowVideoConfig,
  selectedVideoFile,
  setSelectedVideoFile,
  handleVideoAssignmentChange,
  resetVideoAssignments,
  hasCompleteAssignments,
  hasAnyAssignments,
  onDelete,
  onAssignClient,
  // 🆕 Screen assignment props
  onAssignClientToScreen,
  onUnassignClientFromScreen,
  onAutoAssignScreens,
  getScreenAssignments,
  screenAssignmentInfo
}) => {
  const isAnyOperationInProgress = operationInProgress !== null;

  return (
    <CardContent className="pt-0 space-y-4">
      {/* Streaming Mode Configuration */}
      <StreamingModeSection
        group={group}
        localIsStreaming={localIsStreaming}
        videoAssignments={videoAssignments}
        selectedVideoFile={selectedVideoFile}
        hasCompleteAssignments={hasCompleteAssignments}
        setShowVideoConfig={setShowVideoConfig}
      />

      {/* Docker Details */}
      <DockerInfoSection group={group} />

      {/* Video Configuration */}
      <VideoConfigurationSection
        group={group}
        videos={videos}
        videoAssignments={videoAssignments}
        selectedVideoFile={selectedVideoFile}
        showVideoConfig={showVideoConfig}
        setShowVideoConfig={setShowVideoConfig}
        setSelectedVideoFile={setSelectedVideoFile}
        handleVideoAssignmentChange={handleVideoAssignmentChange}
        resetVideoAssignments={resetVideoAssignments}
        hasAnyAssignments={hasAnyAssignments}
        hasCompleteAssignments={hasCompleteAssignments}
      />

      {/* Assigned Clients */}
      {clients.length > 0 && (
        <AssignedClientsSection
          group={group}
          clients={clients}
          onAssignClient={onAssignClient}
          // 🆕 Pass screen assignment props
          onAssignClientToScreen={onAssignClientToScreen}
          onUnassignClientFromScreen={onUnassignClientFromScreen}
          onAutoAssignScreens={onAutoAssignScreens}
          screenAssignmentInfo={screenAssignmentInfo}
        />
      )}

      {/* Client Assignment */}
      <ClientAssignmentSection
        group={group}
        unassignedClients={unassignedClients}
        operationInProgress={operationInProgress}
        onAssignClient={onAssignClient}
      />

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

      {/* Stream URLs (when active) */}
      <ActiveStreamsSection group={group} localIsStreaming={localIsStreaming} />

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
      </div>
    </CardContent>
  );
};

export default GroupCardExpandedContent;
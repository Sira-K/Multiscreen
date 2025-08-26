// frontend/src/components/ui/GroupCard/GroupCard.tsx - FIXED VERSION
// This fixes the missing prop passing in the GroupCardExpandedContent

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Collapsible, CollapsibleContent } from "@/components/ui/collapsible";
import { AlertCircle } from 'lucide-react';
import { Group, Client, Video as VideoType } from '@/types';

// Import sub-components
import GroupCardHeader from './GroupCardHeader';
import GroupCardExpandedContent from './GroupCardExpandedContent';
import StreamingDialogs from './StreamingDialogs';
import { useGroupCardState } from './hooks/useGroupCardState';
import { useVideoAssignments } from './hooks/useVideoAssignments';
import { useStreamingOperations } from './hooks/useStreamingOperations';

interface GroupCardProps {
  group: Group;
  clients: Client[];
  videos: VideoType[];
  unassignedClients?: Client[];
  isStreaming?: boolean;
  onDelete: (groupId: string, groupName: string) => void;
  onStreamingStatusChange?: (groupId: string, isStreaming: boolean) => void;
  onRefresh?: () => void;
  onAssignClient?: (clientId: string, groupId: string) => void;

  //  Screen assignment props
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

const GroupCard: React.FC<GroupCardProps> = ({
  group,
  clients,
  videos,
  unassignedClients = [],
  isStreaming = false,
  onDelete,
  onStreamingStatusChange,
  onRefresh,
  onAssignClient,
  //  Screen assignment props
  onAssignClientToScreen,
  onUnassignClientFromScreen,
  onAutoAssignScreens,
  getScreenAssignments,
  screenAssignmentInfo
}) => {
  // DEFENSIVE: Handle both boolean and object props
  let actualIsStreaming = false;
  if (typeof isStreaming === 'boolean') {
    actualIsStreaming = isStreaming;
  } else if (typeof isStreaming === 'object' && isStreaming !== null) {
    actualIsStreaming = (isStreaming as any).is_streaming || false;
  }

  //  DEBUG: Log what screen assignment props we received
  console.log(` GroupCard DEBUG - Group "${group.name}" screen assignment props:`, {
    groupId: group.id,
    hasOnAssignClientToScreen: !!onAssignClientToScreen,
    hasOnUnassignClientFromScreen: !!onUnassignClientFromScreen,
    hasOnAutoAssignScreens: !!onAutoAssignScreens,
    hasGetScreenAssignments: !!getScreenAssignments,
    hasScreenAssignmentInfo: !!screenAssignmentInfo,
    screenAssignmentInfo
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

  // Custom hooks for state management
  const {
    isExpanded,
    setIsExpanded,
    operationInProgress,
    setOperationInProgress
  } = useGroupCardState();

  const {
    videoAssignments,
    showVideoConfig,
    setShowVideoConfig,
    selectedVideoFile,
    setSelectedVideoFile,
    handleVideoAssignmentChange,
    resetVideoAssignments,
    hasCompleteAssignments,
    hasAnyAssignments
  } = useVideoAssignments(group.id, group.screen_count);

  const {
    showMultiVideoDialog,
    setShowMultiVideoDialog,
    showSingleVideoDialog,
    setShowSingleVideoDialog,
    isStartingMultiVideo,
    isStartingSingleVideo,
    handleStartMultiVideo,
    handleStartSingleVideoSplit,
    handleStopStreaming
  } = useStreamingOperations({
    group,
    videoAssignments,
    selectedVideoFile,
    onStreamingStatusChange,
    onRefresh,
    setOperationInProgress
  });

  const localIsStreaming = actualIsStreaming;

  return (
    <>
      <Card className="bg-white border border-gray-200">
        <GroupCardHeader
          group={group}
          clients={clients}
          localIsStreaming={localIsStreaming}
          operationInProgress={operationInProgress}
          hasCompleteAssignments={hasCompleteAssignments}
          selectedVideoFile={selectedVideoFile}
          isExpanded={isExpanded}
          setIsExpanded={setIsExpanded}
          setShowMultiVideoDialog={setShowMultiVideoDialog}
          setShowSingleVideoDialog={setShowSingleVideoDialog}
          handleStartMultiVideo={handleStartMultiVideo}
          handleStartSingleVideoSplit={handleStartSingleVideoSplit}
          handleStopStreaming={handleStopStreaming}
          isStartingMultiVideo={isStartingMultiVideo}
          isStartingSingleVideo={isStartingSingleVideo}
          videoAssignments={videoAssignments}
        />

        <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
          <CollapsibleContent>
            <GroupCardExpandedContent
              group={group}
              clients={clients}
              videos={videos}
              unassignedClients={unassignedClients}
              localIsStreaming={localIsStreaming}
              operationInProgress={operationInProgress}
              videoAssignments={videoAssignments}
              showVideoConfig={showVideoConfig}
              setShowVideoConfig={setShowVideoConfig}
              selectedVideoFile={selectedVideoFile}
              setSelectedVideoFile={setSelectedVideoFile}
              handleVideoAssignmentChange={handleVideoAssignmentChange}
              resetVideoAssignments={resetVideoAssignments}
              hasCompleteAssignments={hasCompleteAssignments}
              hasAnyAssignments={hasAnyAssignments}
              onDelete={onDelete}
              onAssignClient={onAssignClient}

              // Pass screen assignment props
              onAssignClientToScreen={onAssignClientToScreen}
              onUnassignClientFromScreen={onUnassignClientFromScreen}
              onAutoAssignScreens={onAutoAssignScreens}
              getScreenAssignments={getScreenAssignments}
              screenAssignmentInfo={screenAssignmentInfo}
            />
          </CollapsibleContent>
        </Collapsible>
      </Card>

      {/* Streaming Dialogs */}
      <StreamingDialogs
        group={group}
        videos={videos}
        videoAssignments={videoAssignments}
        selectedVideoFile={selectedVideoFile}
        setSelectedVideoFile={setSelectedVideoFile}
        handleVideoAssignmentChange={handleVideoAssignmentChange}
        showMultiVideoDialog={showMultiVideoDialog}
        setShowMultiVideoDialog={setShowMultiVideoDialog}
        showSingleVideoDialog={showSingleVideoDialog}
        setShowSingleVideoDialog={setShowSingleVideoDialog}
        handleStartMultiVideo={handleStartMultiVideo}
        handleStartSingleVideoSplit={handleStartSingleVideoSplit}
        isStartingMultiVideo={isStartingMultiVideo}
        isStartingSingleVideo={isStartingSingleVideo}
      />
    </>
  );
};

export default GroupCard;
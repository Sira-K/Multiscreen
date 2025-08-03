// frontend/src/components/ui/GroupCard/hooks/useStreamingOperations.ts

import { useState } from 'react';
import { Group } from '../../../../types';
import { VideoAssignment } from '../types';
import { api } from '../../../../API/api';

interface UseStreamingOperationsProps {
  group: Group;
  videoAssignments: VideoAssignment[];
  selectedVideoFile: string;
  onStreamingStatusChange?: (groupId: string, isStreaming: boolean) => void;
  onRefresh?: () => void;
  setOperationInProgress: (operation: string | null) => void;
}

export const useStreamingOperations = ({
  group,
  videoAssignments,
  selectedVideoFile,
  onStreamingStatusChange,
  onRefresh,
  setOperationInProgress
}: UseStreamingOperationsProps) => {
  // Dialog states
  const [showMultiVideoDialog, setShowMultiVideoDialog] = useState(false);
  const [showSingleVideoDialog, setShowSingleVideoDialog] = useState(false);
  
  // Loading states
  const [isStartingMultiVideo, setIsStartingMultiVideo] = useState(false);
  const [isStartingSingleVideo, setIsStartingSingleVideo] = useState(false);

  const handleStartMultiVideo = async () => {
    try {
      setIsStartingMultiVideo(true);
      
      const validAssignments = videoAssignments.filter(assignment => assignment.file);
      if (validAssignments.length !== group.screen_count) {
        throw new Error(`Please assign videos to all ${group.screen_count} screens`);
      }
      
      console.log(`🎬 Starting multi-video for group ${group.name} (${group.id})`);
      
      const result = await api.group.startMultiVideoGroup(group.id, validAssignments, {
        screen_count: group.screen_count,
        orientation: group.orientation
      });
      
      console.log(`✅ Multi-video started successfully for group ${group.id}`);
      
      // Only notify parent - NO local state changes
      if (onStreamingStatusChange) {
        onStreamingStatusChange(group.id, true);
      }
      
      setShowMultiVideoDialog(false);
      if (onRefresh) onRefresh();
      
    } catch (error) {
      console.error(`❌ Error starting multi-video for group ${group.id}:`, error);
      alert(`Failed to start multi-video: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsStartingMultiVideo(false);
    }
  };

  const handleStartSingleVideoSplit = async () => {
    console.log(`🔥 handleStartSingleVideoSplit called for group ${group.id} with video: ${selectedVideoFile}`);
    
    try {
      setIsStartingSingleVideo(true);
      
      if (!selectedVideoFile) {
        throw new Error('Please select a video file');
      }
      
      console.log(`🎬 Starting single video split for group ${group.name} (${group.id})`);
      
      const result = await api.group.startSingleVideoSplit(group.id, {
        video_file: selectedVideoFile,
        screen_count: group.screen_count,
        orientation: group.orientation,
        enable_looping: true
      });
      
      console.log(`✅ Single video split started successfully for group ${group.id}:`, result);
      
      // Only notify parent - NO local state changes
      if (onStreamingStatusChange) {
        onStreamingStatusChange(group.id, true);
      }
      
      setShowSingleVideoDialog(false);
      if (onRefresh) onRefresh();
      
    } catch (error) {
      console.error(`❌ Error starting single video split for group ${group.id}:`, error);
      alert(`Failed to start single video split: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsStartingSingleVideo(false);
    }
  };

  const handleStopStreaming = async () => {
    try {
      setOperationInProgress('stopping');
      console.log(`🛑 Stopping stream for group ${group.name} (${group.id})`);
      
      await api.group.stopGroup(group.id);
      console.log(`✅ Stream stopped successfully for group ${group.id}`);
      
      // Only notify parent - NO local state changes
      if (onStreamingStatusChange) {
        onStreamingStatusChange(group.id, false);
      }
      
      if (onRefresh) onRefresh();
      
    } catch (error) {
      console.error(`❌ Error stopping stream for group ${group.id}:`, error);
      alert(`Failed to stop stream: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setOperationInProgress(null);
    }
  };

  return {
    showMultiVideoDialog,
    setShowMultiVideoDialog,
    showSingleVideoDialog,
    setShowSingleVideoDialog,
    isStartingMultiVideo,
    isStartingSingleVideo,
    handleStartMultiVideo,
    handleStartSingleVideoSplit,
    handleStopStreaming
  };
};
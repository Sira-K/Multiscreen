// frontend/src/components/StreamsTab/hooks/useGroupOperations.ts

import { useState } from 'react';
import { groupApi } from '../../../API/api';
import { useErrorHandler } from '../../ErrorSystem/useErrorHandler';

export const useGroupOperations = (
  loadInitialData: () => Promise<void>
) => {
  const { showError, showFFmpegError, showDockerError } = useErrorHandler();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [operationInProgress, setOperationInProgress] = useState<string | null>(null);

  // Form state for creating new groups
  const [newGroupForm, setNewGroupForm] = useState({
    name: '',
    description: '',
    screen_count: 2,
    orientation: 'horizontal' as 'horizontal' | 'vertical' | 'grid',
    streaming_mode: 'multi_video' as 'multi_video' | 'single_video_split'
  });

  // Create new group
  const createGroup = async () => {
    try {
      setOperationInProgress('create');

      console.log(` CREATING GROUP:`, newGroupForm);

      if (!newGroupForm.name.trim()) {
        // Use error system for validation errors
        showError({
          message: "Group name is required",
          error_code: 'VALIDATION_ERROR',
          error_category: '4xx',
          context: {
            component: 'useGroupOperations',
            operation: 'createGroup',
            field: 'name',
            timestamp: new Date().toISOString()
          }
        });
        return;
      }

      const result = await groupApi.createGroup({
        name: newGroupForm.name.trim(),
        description: newGroupForm.description.trim() || undefined,
        screen_count: newGroupForm.screen_count,
        orientation: newGroupForm.orientation,
        streaming_mode: newGroupForm.streaming_mode
      });

      console.log(` GROUP CREATED:`, result);

      // Show success message using error system (info category)
      showError({
        message: `Successfully created group "${newGroupForm.name}"`,
        error_code: 'GROUP_CREATED',
        error_category: '2xx',
        context: {
          component: 'useGroupOperations',
          operation: 'createGroup',
          group_name: newGroupForm.name,
          timestamp: new Date().toISOString()
        }
      });

      // Reset form and close dialog
      setNewGroupForm({
        name: '',
        description: '',
        screen_count: 2,
        orientation: 'horizontal',
        streaming_mode: 'multi_video'
      });
      setShowCreateForm(false);

      // Reload data
      await loadInitialData();

    } catch (error: any) {
      console.error(' Error creating group:', error);

      // Use error system for better error handling
      showError({
        message: error?.message || "Failed to create group",
        error_code: 'GROUP_CREATION_FAILED',
        error_category: '5xx',
        context: {
          component: 'useGroupOperations',
          operation: 'createGroup',
          group_data: newGroupForm,
          timestamp: new Date().toISOString(),
          original_error: error?.message,
          stack: error?.stack
        }
      });
    } finally {
      setOperationInProgress(null);
    }
  };

  // Delete group
  const deleteGroup = async (groupId: string, groupName: string) => {
    try {
      setOperationInProgress(groupId);

      const response = await groupApi.deleteGroup(groupId);

      // Show success message using error system (info category)
      showError({
        message: `Successfully deleted group "${groupName}"`,
        error_code: 'GROUP_DELETED',
        error_category: '2xx',
        context: {
          component: 'useGroupOperations',
          operation: 'deleteGroup',
          group_name: groupName,
          timestamp: new Date().toISOString()
        }
      });

      // Reload data to refresh the list
      await loadInitialData();

    } catch (error: any) {
      console.error('Error deleting group:', error);

      // Use error system for better error handling
      showError({
        message: error?.message || "Failed to delete group",
        error_code: 'GROUP_DELETION_FAILED',
        error_category: '5xx',
        context: {
          component: 'useGroupOperations',
          operation: 'deleteGroup',
          group_id: groupId,
          group_name: groupName,
          timestamp: new Date().toISOString(),
          original_error: error?.message,
          stack: error?.stack
        }
      });
    } finally {
      setOperationInProgress(null);
    }
  };

  return {
    showCreateForm,
    setShowCreateForm,
    newGroupForm,
    setNewGroupForm,
    operationInProgress,
    setOperationInProgress,
    createGroup,
    deleteGroup
  };
};
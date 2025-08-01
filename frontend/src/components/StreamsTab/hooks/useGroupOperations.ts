// frontend/src/components/StreamsTab/hooks/useGroupOperations.ts

import { useState } from 'react';
import { groupApi } from '../../../API/api';

interface ToastFunction {
  (props: { title: string; description: string; variant?: "destructive" }): void;
}

export const useGroupOperations = (
  loadInitialData: () => Promise<void>, 
  toast: ToastFunction
) => {
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

      console.log(`🔄 CREATING GROUP:`, newGroupForm);

      if (!newGroupForm.name.trim()) {
        toast({
          title: "Validation Error",
          description: "Group name is required",
          variant: "destructive"
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

      console.log(`✅ GROUP CREATED:`, result);

      toast({
        title: "Group Created",
        description: `Successfully created group "${newGroupForm.name}"`
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
      console.error('❌ Error creating group:', error);
      toast({
        title: "Creation Failed",
        description: error?.message || "Failed to create group",
        variant: "destructive"
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
      
      toast({
        title: "Group Deleted",
        description: `Successfully deleted group "${groupName}"`
      });

      // Reload data to refresh the list
      await loadInitialData();
      
    } catch (error: any) {
      console.error('Error deleting group:', error);
      toast({
        title: "Deletion Failed",
        description: error?.message || `Failed to delete group "${groupName}"`,
        variant: "destructive"
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
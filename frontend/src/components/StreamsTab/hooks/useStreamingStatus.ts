// frontend/src/components/StreamsTab/hooks/useStreamingStatus.ts

import { useState, useEffect } from 'react';
import { groupApi } from '../../../API/api';
import type { Group } from '../../../types';

export const useStreamingStatus = (groups: Group[]) => {
  const [streamingStatus, setStreamingStatus] = useState<{ [groupId: string]: boolean }>({});

  // Load streaming statuses for all groups
  const loadStreamingStatuses = async (groupsList: Group[]) => {
    try {
      console.log(`🔄 LOADING STREAMING STATUSES for ${groupsList.length} groups...`);
      
      // Initialize all groups with false status first
      const initialStatuses: { [groupId: string]: boolean } = {};
      groupsList.forEach(group => {
        initialStatuses[group.id] = false;
      });
      
      console.log(`📊 INITIAL STREAMING STATUS:`, initialStatuses);
      setStreamingStatus(initialStatuses);
      
      // Try to get all statuses at once
      try {
        const statusData = await groupApi.getAllStreamingStatuses();
        console.log(`📊 API getAllStreamingStatuses response:`, statusData);
        
        const statuses: { [groupId: string]: boolean } = {};
        const rawStatuses = statusData.streaming_statuses || {};
        
        // Process each group's status
        groupsList.forEach(group => {
          const rawStatus = rawStatuses[group.id];
          
          // IMPORTANT: Extract boolean from object if needed
          let isStreaming = false;
          if (typeof rawStatus === 'boolean') {
            isStreaming = rawStatus;
          } else if (typeof rawStatus === 'object' && rawStatus !== null) {
            isStreaming = (rawStatus as any).is_streaming || false; // Type assertion for API objects
          }
          
          statuses[group.id] = isStreaming;
          
          console.log(`📊 Group ${group.name} status processing:`, {
            groupId: group.id,
            rawStatus: rawStatus,
            extractedBoolean: isStreaming
          });
        });
        
        console.log(`📊 FINAL BOOLEAN STREAMING STATUSES:`, statuses);
        setStreamingStatus(statuses);
        
      } catch (getAllError) {
        console.log(`⚠️ getAllStreamingStatuses failed, checking individually:`, getAllError);
        
        // Fallback: check each group individually
        const statuses: { [groupId: string]: boolean } = {};
        
        for (const group of groupsList) {
          try {
            const status = await groupApi.getStreamingStatus(group.id);
            console.log(`📊 Individual status for ${group.name}:`, status);
            
            // IMPORTANT: Extract boolean from response
            let isStreaming = false;
            if (typeof status === 'boolean') {
              isStreaming = status;
            } else if (typeof status === 'object' && status !== null) {
              isStreaming = (status as any).is_streaming || false; // Type assertion for API objects
            }
            
            statuses[group.id] = isStreaming;
            
          } catch (error) {
            console.log(`⚠️ Failed to get status for ${group.name}, defaulting to false`);
            statuses[group.id] = false;
          }
        }
        
        console.log(`📊 FALLBACK BOOLEAN STREAMING STATUSES:`, statuses);
        setStreamingStatus(statuses);
      }
      
    } catch (error) {
      console.error('❌ Error loading streaming statuses:', error);
      // Set all to false as fallback
      const fallbackStatuses: { [groupId: string]: boolean } = {};
      groupsList.forEach(group => {
        fallbackStatuses[group.id] = false;
      });
      setStreamingStatus(fallbackStatuses);
    }
  };

  // Handle streaming status change (called by GroupCard)
  const handleStreamingStatusChange = (groupId: string, isStreaming: boolean) => {
    console.log(`📡 STREAMING STATUS CHANGE:`, {
      groupId,
      isStreaming,
      type: typeof isStreaming,
      oldStatus: streamingStatus[groupId]
    });
    
    // Ensure we always store a boolean
    const booleanStatus = Boolean(isStreaming);
    
    setStreamingStatus(prev => {
      const newStatus = {
        ...prev,
        [groupId]: booleanStatus  // Force boolean
      };
      
      console.log(`📊 UPDATED STREAMING STATUS:`, newStatus);
      return newStatus;
    });
  };

  // Load streaming statuses when groups change
  useEffect(() => {
    if (groups.length > 0) {
      loadStreamingStatuses(groups);
    }
  }, [groups]);

  return {
    streamingStatus,
    setStreamingStatus,
    loadStreamingStatuses,
    handleStreamingStatusChange
  };
};
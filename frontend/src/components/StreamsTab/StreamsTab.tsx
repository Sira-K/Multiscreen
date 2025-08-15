// frontend/src/components/StreamsTab/StreamsTab.tsx - Fixed Version (No Loops)

import React, { useEffect, useRef } from "react";
import { RefreshCw } from "lucide-react";
import { useErrorHandler } from "@/components/ErrorSystem/useErrorHandler";
import type { Group, Video, Client } from '../../types';

// Import sub-components
import StreamsTabHeader from './StreamsTabHeader';
import StreamsTabStats from './StreamsTabStats';
import StreamsTabGroups from './StreamsTabGroups';
import StreamsTabArchitectureInfo from './StreamsTabArchitectureInfo';

// Import custom hooks
import { useStreamsData } from './hooks/useStreamsData';
import { useStreamingStatus } from './hooks/useStreamingStatus';
import { useGroupOperations } from './hooks/useGroupOperations';
import { useClientAssignment } from './hooks/useClientAssignment';

const StreamsTab = () => {
  const { showError, handleApiError } = useErrorHandler();
  const hasInitialized = useRef(false); // Prevent multiple initializations
  
  // State management using custom hooks
  const {
    groups,
    videos,
    clients,
    loading,
    refreshing,
    loadInitialData,
    refreshData
  } = useStreamsData();

  const {
    streamingStatus,
    handleStreamingStatusChange
  } = useStreamingStatus(groups);

  const {
    showCreateForm,
    setShowCreateForm,
    newGroupForm,
    setNewGroupForm,
    operationInProgress,
    createGroup,
    deleteGroup
  } = useGroupOperations(loadInitialData);

  const {
    getUnassignedClients,
    getClientsForGroup,
    handleAssignClient,
    // 🆕 Screen assignment functions
    getClientsWithScreenAssignments,
    handleAssignClientToScreen,
    handleUnassignClientFromScreen,
    handleAutoAssignScreens,
    getScreenAssignments
  } = useClientAssignment(clients, loadInitialData);

  // Initial load with proper error handling - ONLY ONCE
  useEffect(() => {
    if (hasInitialized.current) return; // Prevent multiple calls
    
    const initializeData = async () => {
      try {
        hasInitialized.current = true;
        await loadInitialData();
      } catch (error: any) {
        console.error('❌ Error loading initial data:', error);
        
        // Use the new error system for comprehensive error handling
        showError({
          message: error?.message || "Failed to load application data",
          error_code: 'DATA_LOAD_FAILED',
          error_category: '5xx',
          context: {
            component: 'StreamsTab',
            operation: 'initial_data_load',
            timestamp: new Date().toISOString(),
            original_error: error?.message,
            stack: error?.stack
          }
        });
      }
    };

    initializeData();
  }, [loadInitialData, showError]);

  // Debug effect to monitor streaming status changes - THROTTLED
  useEffect(() => {
    const timer = setTimeout(() => {
      console.log('🔍 Current streaming status:', streamingStatus);
      console.log('🔍 Groups and their status:', groups.map(g => ({
        id: g.id,
        name: g.name,
        status: streamingStatus[g.id]
      })));
    }, 100); // Throttle debug logs

    return () => clearTimeout(timer);
  }, [streamingStatus, groups]);

  // Debug effect for client data - THROTTLED
  useEffect(() => {
    const timer = setTimeout(() => {
      console.log('🔍 Current clients state:', clients);
      console.log('🔍 Unassigned clients:', getUnassignedClients());
      console.log('🔍 Client group assignments:', clients.map(c => ({
        id: c.client_id,
        name: c.display_name || c.hostname,
        group_id: c.group_id,
        status: c.status
      })));
    }, 100); // Throttle debug logs

    return () => clearTimeout(timer);
  }, [clients, getUnassignedClients]);

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <RefreshCw className="h-8 w-8 animate-spin text-gray-400 mx-auto mb-2" />
            <p className="text-gray-600">Loading streaming groups...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <StreamsTabHeader
        showCreateForm={showCreateForm}
        setShowCreateForm={setShowCreateForm}
        refreshData={refreshData}
        refreshing={refreshing}
        newGroupForm={newGroupForm}
        setNewGroupForm={setNewGroupForm}
        createGroup={createGroup}
        operationInProgress={operationInProgress}
      />

      {/* Stats Cards */}
      <StreamsTabStats
        groups={groups}
        streamingStatus={streamingStatus}
        clients={clients}
      />

      {/* Groups Section */}
      <StreamsTabGroups
        groups={groups}
        videos={videos}
        clients={clients}
        streamingStatus={streamingStatus}
        operationInProgress={operationInProgress}
        getUnassignedClients={getUnassignedClients}
        getClientsForGroup={getClientsForGroup}
        handleAssignClient={handleAssignClient}
        
        // 🆕 Screen assignment functions
        getClientsWithScreenAssignments={getClientsWithScreenAssignments}
        handleAssignClientToScreen={handleAssignClientToScreen}
        handleUnassignClientFromScreen={handleUnassignClientFromScreen}
        handleAutoAssignScreens={handleAutoAssignScreens}
        getScreenAssignments={getScreenAssignments}
        
        deleteGroup={deleteGroup}
        handleStreamingStatusChange={handleStreamingStatusChange}
        refreshData={refreshData}
        setShowCreateForm={setShowCreateForm}
      />

      {/* Architecture Info */}
      <StreamsTabArchitectureInfo />
    </div>
  );
};

export default StreamsTab;
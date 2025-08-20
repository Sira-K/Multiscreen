// frontend/src/components/StreamsTab/hooks/useClientAssignment.ts - Enhanced with Stream Assignment

import { useCallback } from 'react';
import { clientApi } from '../../../API/api';
import { useErrorHandler } from '../../ErrorSystem/useErrorHandler';
import type { Client } from '../../../types';

export const useClientAssignment = (
  clients: Client[],
  loadInitialData: () => Promise<void>
) => {
  const { showError } = useErrorHandler();

  // Get unassigned clients - use useCallback to prevent recreation
  const getUnassignedClients = useCallback(() => {
    const unassigned = clients.filter(client =>
      !client.group_id ||
      client.group_id === null ||
      client.group_id === "" ||
      client.group_id === undefined
    );
    console.log(` Unassigned clients calculation:`, {
      totalClients: clients.length,
      unassignedCount: unassigned.length,
      unassignedList: unassigned.map(c => ({
        id: c.client_id,
        name: c.display_name || c.hostname,
        group_id: c.group_id
      }))
    });
    return unassigned;
  }, [clients]);

  // Get clients for a specific group - use useCallback to prevent recreation
  const getClientsForGroup = useCallback((groupId: string) => {
    const groupClients = clients.filter(client => client.group_id === groupId);
    console.log(` Clients for group ${groupId}:`, {
      count: groupClients.length,
      clients: groupClients.map(c => ({
        id: c.client_id,
        name: c.display_name || c.hostname,
        group_id: c.group_id,
        screen_number: c.screen_number
      }))
    });
    return groupClients;
  }, [clients]);

  // Get clients assigned to specific screens in a group
  const getClientsWithScreenAssignments = useCallback((groupId: string) => {
    const groupClients = clients.filter(client => client.group_id === groupId);
    const assignedToScreens = groupClients.filter(client =>
      client.screen_number !== null &&
      client.screen_number !== undefined
    );
    const unassignedToScreens = groupClients.filter(client =>
      client.screen_number === null ||
      client.screen_number === undefined
    );

    console.log(` Screen assignments for group ${groupId}:`, {
      totalInGroup: groupClients.length,
      assignedToScreens: assignedToScreens.length,
      unassignedToScreens: unassignedToScreens.length,
      assignments: assignedToScreens.map(c => ({
        client: c.client_id,
        screen: c.screen_number
      }))
    });

    return {
      allGroupClients: groupClients,
      assignedToScreens,
      unassignedToScreens
    };
  }, [clients]);

  // Handle client assignment to group - use useCallback to prevent recreation
  const handleAssignClient = useCallback(async (clientId: string, groupId: string) => {
    try {
      console.log(` Assigning client ${clientId} to group ${groupId}`);

      if (groupId === "" || groupId === null || groupId === undefined) {
        // Unassign client
        await clientApi.unassignClientFromGroup(clientId);
        console.log(` Client ${clientId} unassigned`);

        showError({
          message: "Client has been unassigned from the group",
          error_code: 'CLIENT_UNASSIGNED',
          error_category: '2xx',
          context: {
            component: 'useClientAssignment',
            operation: 'unassignClient',
            client_id: clientId,
            timestamp: new Date().toISOString()
          }
        });
      } else {
        // Assign client to group
        await clientApi.assignClientToGroup(clientId, groupId);
        console.log(` Client ${clientId} assigned to group ${groupId}`);

        showError({
          message: "Client has been assigned to the group",
          error_code: 'CLIENT_ASSIGNED',
          error_category: '2xx',
          context: {
            component: 'useClientAssignment',
            operation: 'assignClient',
            client_id: clientId,
            group_id: groupId,
            timestamp: new Date().toISOString()
          }
        });
      }

      // Reload data to reflect changes
      await loadInitialData();

    } catch (error: any) {
      console.error(` Error assigning client ${clientId}:`, error);

      showError({
        message: error?.message || "Failed to assign client",
        error_code: 'CLIENT_ASSIGNMENT_FAILED',
        error_category: '5xx',
        context: {
          component: 'useClientAssignment',
          operation: 'assignClient',
          client_id: clientId,
          group_id: groupId,
          timestamp: new Date().toISOString(),
          original_error: error?.message,
          stack: error?.stack
        }
      });
    }
  }, [clients, loadInitialData, showError]);

  //  Handle client assignment to specific screen within a group
  const handleAssignClientToScreen = useCallback(async (
    clientId: string,
    groupId: string,
    screenNumber: number
  ) => {
    try {
      console.log(` Assigning client ${clientId} to screen ${screenNumber} in group ${groupId}`);

      await clientApi.assignClientToScreen(clientId, groupId, screenNumber);
      console.log(` Client ${clientId} assigned to screen ${screenNumber}`);

      showError({
        message: `Client assigned to screen ${screenNumber + 1}`,
        error_code: 'SCREEN_ASSIGNED',
        error_category: '2xx',
        context: {
          component: 'useClientAssignment',
          operation: 'assignClientToScreen',
          client_id: clientId,
          group_id: groupId,
          screen_number: screenNumber,
          timestamp: new Date().toISOString()
        }
      });

      // Reload data to show changes immediately
      await loadInitialData();

    } catch (error: any) {
      console.error(' Error assigning client to screen:', error);
      showError({
        message: error?.message || 'Failed to assign client to screen',
        error_code: 'SCREEN_ASSIGNMENT_FAILED',
        error_category: '5xx',
        context: {
          component: 'useClientAssignment',
          operation: 'assignClientToScreen',
          client_id: clientId,
          group_id: groupId,
          screen_number: screenNumber,
          timestamp: new Date().toISOString(),
          original_error: error?.message,
          stack: error?.stack
        }
      });
    }
  }, [loadInitialData, showError]);

  //  Handle client unassignment from screen (but keep in group)
  const handleUnassignClientFromScreen = useCallback(async (clientId: string) => {
    try {
      console.log(` Unassigning client ${clientId} from screen`);

      await clientApi.unassignClientFromScreen(clientId);
      console.log(` Client ${clientId} unassigned from screen`);

      showError({
        message: "Client has been unassigned from the screen",
        error_code: 'SCREEN_UNASSIGNED',
        error_category: '2xx',
        context: {
          component: 'useClientAssignment',
          operation: 'unassignClientFromScreen',
          client_id: clientId,
          timestamp: new Date().toISOString()
        }
      });

      // Reload data to show changes immediately
      await loadInitialData();

    } catch (error: any) {
      console.error(' Error unassigning client from screen:', error);
      showError({
        message: error?.message || 'Failed to unassign client from screen',
        error_code: 'SCREEN_UNASSIGNMENT_FAILED',
        error_category: '5xx',
        context: {
          component: 'useClientAssignment',
          operation: 'unassignClientFromScreen',
          client_id: clientId,
          timestamp: new Date().toISOString(),
          original_error: error?.message,
          stack: error?.stack
        }
      });
    }
  }, [loadInitialData, showError]);

  //  Auto-assign screens to clients in a group
  const handleAutoAssignScreens = useCallback(async (groupId: string) => {
    try {
      console.log(` Auto-assigning screens for group ${groupId}`);

      await clientApi.autoAssignScreens(groupId);
      console.log(` Screens auto-assigned for group ${groupId}`);

      showError({
        message: "Clients have been automatically assigned to screens",
        error_code: 'AUTO_ASSIGNMENT_COMPLETE',
        error_category: '2xx',
        context: {
          component: 'useClientAssignment',
          operation: 'autoAssignScreens',
          group_id: groupId,
          timestamp: new Date().toISOString()
        }
      });

      // Reload data to show changes immediately
      await loadInitialData();

    } catch (error: any) {
      console.error(' Error auto-assigning screens:', error);
      showError({
        message: error?.message || 'Failed to auto-assign screens',
        error_code: 'AUTO_ASSIGNMENT_FAILED',
        error_category: '5xx',
        context: {
          component: 'useClientAssignment',
          operation: 'autoAssignScreens',
          group_id: groupId,
          timestamp: new Date().toISOString(),
          original_error: error?.message,
          stack: error?.stack
        }
      });
    }
  }, [loadInitialData, showError]);

  //  Get screen assignments for a group
  const getScreenAssignments = useCallback(async (groupId: string) => {
    try {
      console.log(` Getting screen assignments for group ${groupId}`);

      const assignments = await clientApi.getScreenAssignments(groupId);
      console.log(` Retrieved screen assignments:`, assignments);

      return assignments;

    } catch (error: any) {
      console.error(' Error getting screen assignments:', error);
      showError({
        message: error?.message || 'Failed to load screen assignments',
        error_code: 'FAILED_TO_LOAD_ASSIGNMENTS',
        error_category: '5xx',
        context: {
          component: 'useClientAssignment',
          operation: 'getScreenAssignments',
          group_id: groupId,
          timestamp: new Date().toISOString(),
          original_error: error?.message,
          stack: error?.stack
        }
      });
      return null;
    }
  }, [showError]);

  return {
    // Group assignment functions
    getUnassignedClients,
    getClientsForGroup,
    handleAssignClient,

    //  Screen assignment functions
    getClientsWithScreenAssignments,
    handleAssignClientToScreen,
    handleUnassignClientFromScreen,
    handleAutoAssignScreens,
    getScreenAssignments
  };
};
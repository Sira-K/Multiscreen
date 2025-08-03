// frontend/src/components/StreamsTab/hooks/useClientAssignment.ts - Enhanced with Stream Assignment

import { useCallback } from 'react';
import { clientApi } from '../../../API/api';
import type { Client } from '../../../types';

interface ToastFunction {
  (props: { title: string; description: string; variant?: "destructive" }): void;
}

export const useClientAssignment = (
  clients: Client[], 
  loadInitialData: () => Promise<void>, 
  toast: ToastFunction
) => {
  // Get unassigned clients - use useCallback to prevent recreation
  const getUnassignedClients = useCallback(() => {
    const unassigned = clients.filter(client => 
      !client.group_id || 
      client.group_id === null || 
      client.group_id === "" ||
      client.group_id === undefined
    );
    console.log(`📊 Unassigned clients calculation:`, {
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
    console.log(`📊 Clients for group ${groupId}:`, {
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
    
    console.log(`📺 Screen assignments for group ${groupId}:`, {
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
      console.log(`🎯 Assigning client ${clientId} to group ${groupId}`);
      
      if (groupId === "" || groupId === null || groupId === undefined) {
        // Unassign client
        await clientApi.unassignClientFromGroup(clientId);
        console.log(`✅ Client ${clientId} unassigned`);
        
        toast({
          title: "Client Unassigned",
          description: "Client has been unassigned from the group"
        });
      } else {
        // Assign client to group
        await clientApi.assignClientToGroup(clientId, groupId);
        console.log(`✅ Client ${clientId} assigned to group ${groupId}`);
        
        toast({
          title: "Client Assigned",
          description: "Client has been assigned to the group"
        });
      }
      
      // Reload data to show changes immediately
      await loadInitialData();
      
    } catch (error: any) {
      console.error('❌ Error assigning client:', error);
      toast({
        title: "Assignment Failed",
        description: error?.message || 'Failed to assign client',
        variant: "destructive",
      });
    }
  }, [loadInitialData, toast]);

  // 🆕 Handle client assignment to specific screen within a group
  const handleAssignClientToScreen = useCallback(async (
    clientId: string, 
    groupId: string, 
    screenNumber: number
  ) => {
    try {
      console.log(`🖥️ Assigning client ${clientId} to screen ${screenNumber} in group ${groupId}`);
      
      await clientApi.assignClientToScreen(clientId, groupId, screenNumber);
      console.log(`✅ Client ${clientId} assigned to screen ${screenNumber}`);
      
      toast({
        title: "Screen Assigned",
        description: `Client assigned to screen ${screenNumber + 1}`
      });
      
      // Reload data to show changes immediately
      await loadInitialData();
      
    } catch (error: any) {
      console.error('❌ Error assigning client to screen:', error);
      toast({
        title: "Screen Assignment Failed",
        description: error?.message || 'Failed to assign client to screen',
        variant: "destructive",
      });
    }
  }, [loadInitialData, toast]);

  // 🆕 Handle client unassignment from screen (but keep in group)
  const handleUnassignClientFromScreen = useCallback(async (clientId: string) => {
    try {
      console.log(`🖥️ Unassigning client ${clientId} from screen`);
      
      await clientApi.unassignClientFromScreen(clientId);
      console.log(`✅ Client ${clientId} unassigned from screen`);
      
      toast({
        title: "Screen Unassigned",
        description: "Client has been unassigned from the screen"
      });
      
      // Reload data to show changes immediately
      await loadInitialData();
      
    } catch (error: any) {
      console.error('❌ Error unassigning client from screen:', error);
      toast({
        title: "Screen Unassignment Failed",
        description: error?.message || 'Failed to unassign client from screen',
        variant: "destructive",
      });
    }
  }, [loadInitialData, toast]);

  // 🆕 Auto-assign screens to clients in a group
  const handleAutoAssignScreens = useCallback(async (groupId: string) => {
    try {
      console.log(`🤖 Auto-assigning screens for group ${groupId}`);
      
      await clientApi.autoAssignScreens(groupId);
      console.log(`✅ Screens auto-assigned for group ${groupId}`);
      
      toast({
        title: "Auto-Assignment Complete",
        description: "Clients have been automatically assigned to screens"
      });
      
      // Reload data to show changes immediately
      await loadInitialData();
      
    } catch (error: any) {
      console.error('❌ Error auto-assigning screens:', error);
      toast({
        title: "Auto-Assignment Failed",
        description: error?.message || 'Failed to auto-assign screens',
        variant: "destructive",
      });
    }
  }, [loadInitialData, toast]);

  // 🆕 Get screen assignments for a group
  const getScreenAssignments = useCallback(async (groupId: string) => {
    try {
      console.log(`📋 Getting screen assignments for group ${groupId}`);
      
      const assignments = await clientApi.getScreenAssignments(groupId);
      console.log(`✅ Retrieved screen assignments:`, assignments);
      
      return assignments;
      
    } catch (error: any) {
      console.error('❌ Error getting screen assignments:', error);
      toast({
        title: "Failed to Load Assignments",
        description: error?.message || 'Failed to load screen assignments',
        variant: "destructive",
      });
      return null;
    }
  }, [toast]);

  return {
    // Group assignment functions
    getUnassignedClients,
    getClientsForGroup,
    handleAssignClient,
    
    // 🆕 Screen assignment functions
    getClientsWithScreenAssignments,
    handleAssignClientToScreen,
    handleUnassignClientFromScreen,
    handleAutoAssignScreens,
    getScreenAssignments
  };
};
// frontend/src/components/ui/GroupCard/sections/AssignedClientsSection.tsx
// DEBUG VERSION - Add extensive logging to identify the issue

import React from 'react';
import { Button } from '../../button';
import { Badge } from '../../badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../select';
import { Wifi, MoreVertical, Power, Users } from 'lucide-react';
import { Group, Client } from '../../../../types';

interface AssignedClientsSectionProps {
  group: Group;
  clients: Client[];
  onAssignClient?: (clientId: string, groupId: string) => void;
  onAssignClientToScreen?: (clientId: string, groupId: string, screenNumber: number) => Promise<void>;
  onUnassignClientFromScreen?: (clientId: string) => Promise<void>;
  onAutoAssignScreens?: (groupId: string) => Promise<void>;
  screenAssignmentInfo?: {
    allGroupClients: Client[];
    assignedToScreens: Client[];
    unassignedToScreens: Client[];
  };
}

const AssignedClientsSection: React.FC<AssignedClientsSectionProps> = ({
  group,
  clients,
  onAssignClient,
  onAssignClientToScreen,
  onUnassignClientFromScreen,
  onAutoAssignScreens,
  screenAssignmentInfo
}) => {
  
  // DEBUG: Log props received
  console.log(`🔍 AssignedClientsSection DEBUG for group ${group.name}:`, {
    groupId: group.id,
    groupScreenCount: group.screen_count,
    clientsCount: clients.length,
    clients: clients.map(c => ({
      id: c.client_id,
      name: c.display_name || c.hostname,
      screen_number: c.screen_number,
      status: c.status
    })),
    hasScreenAssignmentFunction: !!onAssignClientToScreen,
    hasUnassignFunction: !!onUnassignClientFromScreen,
    screenAssignmentInfo
  });

  const handleScreenAssignment = async (clientId: string, value: string) => {
    console.log(`🖥️ DEBUG: Screen assignment triggered`, {
      clientId,
      groupId: group.id,
      selectedValue: value,
      valueType: typeof value
    });

    try {
      if (value === "unassigned") {
        console.log(`🔄 DEBUG: Unassigning client ${clientId} from screen`);
        if (onUnassignClientFromScreen) {
          await onUnassignClientFromScreen(clientId);
          console.log(`✅ DEBUG: Successfully unassigned client ${clientId}`);
        } else {
          console.error(`❌ DEBUG: onUnassignClientFromScreen function not provided`);
        }
      } else {
        const screenNumber = parseInt(value);
        console.log(`🔄 DEBUG: Assigning client ${clientId} to screen ${screenNumber}`, {
          screenNumber,
          groupId: group.id,
          hasAssignFunction: !!onAssignClientToScreen
        });
        
        if (onAssignClientToScreen) {
          await onAssignClientToScreen(clientId, group.id, screenNumber);
          console.log(`✅ DEBUG: Successfully assigned client ${clientId} to screen ${screenNumber}`);
        } else {
          console.error(`❌ DEBUG: onAssignClientToScreen function not provided`);
        }
      }
    } catch (error) {
      console.error(`❌ DEBUG: Screen assignment failed:`, {
        clientId,
        value,
        error: error instanceof Error ? error.message : error,
        stack: error instanceof Error ? error.stack : undefined
      });
      
      // Re-throw to let parent handle the error
      throw error;
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-gray-700">
          Assigned Clients ({clients.length})
        </label>
        
        {/* Auto-assign screens button */}
        {screenAssignmentInfo && onAutoAssignScreens && screenAssignmentInfo.unassignedToScreens.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              console.log(`🤖 DEBUG: Auto-assign screens triggered for group ${group.id}`);
              onAutoAssignScreens(group.id);
            }}
            className="text-xs"
          >
            Auto-assign Screens
          </Button>
        )}
      </div>
      
      <div className="space-y-1 max-h-24 overflow-y-auto">
        {clients.map((client) => {
          // DEBUG: Log each client's current state
          const currentScreenValue = client.screen_number !== null && client.screen_number !== undefined ? 
            client.screen_number.toString() : "unassigned";
            
          console.log(`🔍 DEBUG: Rendering client ${client.client_id}:`, {
            clientId: client.client_id,
            name: client.display_name || client.hostname,
            screen_number: client.screen_number,
            currentScreenValue,
            status: client.status
          });

          return (
            <div key={client.client_id} className="flex items-center justify-between p-1.5 bg-gray-50 rounded text-xs">
              <div className="flex items-center gap-1.5 min-w-0 flex-1">
                <Wifi className={`h-3 w-3 flex-shrink-0 ${client.status === 'active' ? 'text-green-500' : 'text-gray-400'}`} />
                <span className="font-medium truncate">
                  {client.display_name || client.hostname}
                </span>
                <span className="text-gray-500">({client.ip_address})</span>
                
                {/* Show current screen assignment */}
                {client.screen_number !== null && client.screen_number !== undefined && (
                  <Badge variant="outline" className="text-xs">
                    Screen {client.screen_number + 1}
                  </Badge>
                )}
              </div>
              
              <div className="flex items-center gap-1">
                <Badge variant={client.status === 'active' ? "default" : "secondary"} className="text-xs py-0 px-1">
                  {client.status === 'active' ? "Online" : "Offline"}
                </Badge>
                
                {/* Screen assignment dropdown */}
                <Select
                  value={currentScreenValue}
                  onValueChange={(value) => {
                    console.log(`🖥️ DEBUG: Screen select onChange triggered:`, {
                      clientId: client.client_id,
                      oldValue: currentScreenValue,
                      newValue: value,
                      groupId: group.id
                    });
                    handleScreenAssignment(client.client_id, value);
                  }}
                >
                  <SelectTrigger className="h-6 w-20 p-0 text-xs">
                    <SelectValue placeholder="Screen" />
                  </SelectTrigger>
                  <SelectContent className="w-32">
                    <SelectItem value="unassigned" className="text-xs text-gray-600">
                      No Screen
                    </SelectItem>
                    {Array.from({ length: group.screen_count }, (_, index) => {
                      console.log(`🔍 DEBUG: Creating screen option ${index} for group ${group.name}`);
                      return (
                        <SelectItem key={index} value={index.toString()} className="text-xs">
                          Screen {index + 1}
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>
                
                {/* Group management dropdown */}
                <Select
                  onValueChange={(groupId) => {
                    console.log(`🎯 DEBUG: Group assignment triggered:`, {
                      clientId: client.client_id,
                      newGroupId: groupId,
                      currentGroupId: group.id
                    });
                    
                    if (groupId === "unassign") {
                      if (onAssignClient) onAssignClient(client.client_id, "");
                    } else {
                      if (onAssignClient) onAssignClient(client.client_id, groupId);
                    }
                  }}
                >
                  <SelectTrigger className="h-6 w-6 p-0">
                    <MoreVertical className="h-3 w-3" />
                  </SelectTrigger>
                  <SelectContent className="w-48">
                    <SelectItem value="unassign" className="text-xs text-red-600">
                      <div className="flex items-center">
                        <Power className="h-3 w-3 mr-2" />
                        Unassign from Group
                      </div>
                    </SelectItem>
                    <SelectItem value={group.id} className="text-xs">
                      <div className="flex items-center">
                        <Users className="h-3 w-3 mr-2" />
                        Keep in this group
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          );
        })}
      </div>
      
      {/* Screen assignment summary */}
      {screenAssignmentInfo && (
        <div className="text-xs text-gray-500 mt-2">
          Screen assignments: {screenAssignmentInfo.assignedToScreens.length} of {clients.length} clients assigned
          {/* DEBUG: Show detailed assignment info */}
          <div className="mt-1 text-gray-400">
            DEBUG: Assigned: [{screenAssignmentInfo.assignedToScreens.map(c => `${c.client_id}→S${c.screen_number}`).join(', ')}]
          </div>
        </div>
      )}
    </div>
  );
};

export default AssignedClientsSection;
// frontend/src/components/ui/GroupCard/sections/AssignedClientsSection.tsx

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

  const handleScreenAssignment = async (clientId: string, value: string) => {
    try {
      if (value === "unassigned") {
        if (onUnassignClientFromScreen) {
          await onUnassignClientFromScreen(clientId);
        }
      } else {
        const screenNumber = parseInt(value);
        if (onAssignClientToScreen) {
          await onAssignClientToScreen(clientId, group.id, screenNumber);
        }
      }
    } catch (error) {
      console.error('Screen assignment failed:', error);
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
            onClick={() => onAutoAssignScreens(group.id)}
            className="text-xs"
          >
            Auto-assign Screens
          </Button>
        )}
      </div>

      <div className="space-y-2 max-h-32 overflow-y-auto">
        {clients.map((client) => {
          const currentScreenValue = client.screen_number !== null && client.screen_number !== undefined ?
            client.screen_number.toString() : "unassigned";

          return (
            <div key={client.client_id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <Wifi className={`h-4 w-4 flex-shrink-0 ${client.status === 'active' ? 'text-green-500' : 'text-gray-400'}`} />
                <span className="font-medium truncate text-sm">
                  {client.display_name || client.hostname}
                </span>
                <span className="text-gray-500 text-xs">({client.ip_address})</span>

                {/* Show current screen assignment */}
                {client.screen_number !== null && client.screen_number !== undefined && (
                  <Badge variant="outline" className="text-xs">
                    Screen {client.screen_number + 1}
                  </Badge>
                )}
              </div>

              <div className="flex items-center gap-2">
                <Badge variant={client.status === 'active' ? "default" : "secondary"} className="text-xs py-0.5 px-2">
                  {client.status === 'active' ? "Online" : "Offline"}
                </Badge>

                {/* Screen assignment dropdown - WIDER TO FIT TEXT */}
                <Select
                  value={currentScreenValue}
                  onValueChange={(value) => handleScreenAssignment(client.client_id, value)}
                >
                  <SelectTrigger className="h-6 min-w-[120px] max-w-[120px] px-2 text-xs" style={{ width: '120px' }}>
                    <SelectValue placeholder="Screen" />
                  </SelectTrigger>
                  <SelectContent className="w-32">
                    <SelectItem value="unassigned" className="text-xs text-gray-600">
                      No Screen
                    </SelectItem>
                    {Array.from({ length: group.screen_count }, (_, index) => (
                      <SelectItem key={index} value={index.toString()} className="text-xs">
                        Screen {index + 1}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {/* Group management dropdown */}
                <Select
                  onValueChange={(groupId) => {
                    if (groupId === "unassign") {
                      if (onAssignClient) onAssignClient(client.client_id, "");
                    } else {
                      if (onAssignClient) onAssignClient(client.client_id, groupId);
                    }
                  }}
                >
                  <SelectTrigger className="h-8 w-8 p-0">
                    <MoreVertical className="h-4 w-4" />
                  </SelectTrigger>
                  <SelectContent className="w-48">
                    <SelectItem value="unassign" className="text-sm text-red-600">
                      <div className="flex items-center">
                        <Power className="h-4 w-4 mr-2" />
                        Unassign from Group
                      </div>
                    </SelectItem>
                    <SelectItem value={group.id} className="text-sm">
                      <div className="flex items-center">
                        <Users className="h-4 w-4 mr-2" />
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
        </div>
      )}
    </div>
  );
};

export default AssignedClientsSection;
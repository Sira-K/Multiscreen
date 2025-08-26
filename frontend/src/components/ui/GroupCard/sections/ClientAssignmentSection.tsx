// frontend/src/components/ui/GroupCard/sections/ClientAssignmentSection.tsx

import React from 'react';
import { Button } from '../../button';
import { Users, Wifi } from 'lucide-react';
import { Group, Client } from '@/types';

interface ClientAssignmentSectionProps {
  group: Group;
  unassignedClients: Client[];
  operationInProgress: string | null;
  onAssignClient?: (clientId: string, groupId: string) => void;
}

const ClientAssignmentSection: React.FC<ClientAssignmentSectionProps> = ({
  group,
  unassignedClients,
  operationInProgress,
  onAssignClient
}) => {
  return (
    <>
      {/* Assign Client Button */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">
          Assign New Client
        </label>
        <Button 
          variant="outline" 
          size="sm" 
          className="w-full text-xs"
          onClick={() => {
            if (unassignedClients.length > 0 && onAssignClient) {
              // Assign the first available client
              onAssignClient(unassignedClients[0].client_id, group.id);
            }
          }}
          disabled={unassignedClients.length === 0}
        >
          <Users className="h-3 w-3 mr-1" />
          {unassignedClients.length > 0 
            ? `Assign Client (${unassignedClients.length} available)` 
            : 'No clients available'}
        </Button>
      </div>

      {/* Quick Assign Unassigned Clients */}
      {unassignedClients.length > 0 && onAssignClient && (
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">
            Quick Assign ({unassignedClients.length} available)
          </label>
          <div className="grid grid-cols-1 gap-1 max-h-20 overflow-y-auto">
            {unassignedClients.slice(0, 2).map((client) => (
              <div key={client.client_id} className="flex items-center justify-between p-1.5 bg-yellow-50 rounded text-xs">
                <div className="flex items-center gap-1.5 min-w-0 flex-1">
                  <Wifi className={`h-3 w-3 flex-shrink-0 ${client.status === 'active' ? 'text-green-500' : 'text-gray-400'}`} />
                  <span className="truncate">{client.display_name || client.hostname}</span>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-6 px-2 text-xs"
                  onClick={() => onAssignClient(client.client_id, group.id)}
                  disabled={operationInProgress === `assign-${client.client_id}`}
                >
                  {operationInProgress === `assign-${client.client_id}` ? '...' : 'Assign'}
                </Button>
              </div>
            ))}
            {unassignedClients.length > 2 && (
              <div className="text-center text-gray-500 text-xs py-1">
                +{unassignedClients.length - 2} more available
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
};

export default ClientAssignmentSection;
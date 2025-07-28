// frontend/src/components/ClientsTab.tsx - Fixed with global Client interface

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { ArrowUp, ArrowDown, Monitor, Wifi, WifiOff, Search, Users } from "lucide-react";import { useToast } from "@/hooks/use-toast";
import { clientApi } from '@/API/api';
import type { Client } from '@/types'; // Use the global Client interface

// REMOVED: Local Client interface - now using global one from types/index.ts

interface ClientsTabProps {
  clients: Client[];
  setClients: React.Dispatch<React.SetStateAction<Client[]>>;
}

const ClientsTab = ({ clients, setClients }: ClientsTabProps) => {
  const { toast } = useToast();
  const [searchTerm, setSearchTerm] = useState('');

  const moveClient = (clientId: string, direction: 'up' | 'down') => {
    const clientIndex = clients.findIndex(c => c.client_id === clientId);
    if (
      (direction === 'up' && clientIndex === 0) ||
      (direction === 'down' && clientIndex === clients.length - 1)
    ) {
      return;
    }

    const newClients = [...clients];
    const targetIndex = direction === 'up' ? clientIndex - 1 : clientIndex + 1;
    
    [newClients[clientIndex], newClients[targetIndex]] = [newClients[targetIndex], newClients[clientIndex]];
    setClients(newClients);
  };

  const filteredClients = clients.filter(client => {
    if (!searchTerm) return true;
    
    const searchLower = searchTerm.toLowerCase();
    return (
      (client.display_name?.toLowerCase().includes(searchLower)) ||
      (client.hostname?.toLowerCase().includes(searchLower)) ||
      (client.client_id?.toLowerCase().includes(searchLower)) ||
      (client.ip_address?.toLowerCase().includes(searchLower)) // Note: using ip_address from global interface
    );
  });

  return (
    <div className="space-y-6">
      <Card className="bg-white border border-gray-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="w-5 h-5" />
            Client Management
          </CardTitle>
          <CardDescription>
            View and manage connected clients. You can reorder clients and monitor their connection status.
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          {/* Search */}
          <div className="mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search clients by name, hostname, ID, or IP..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {/* Clients List */}
          <div className="space-y-3">
            {filteredClients.length === 0 ? (
              <div className="text-center py-8">
                <Monitor className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <h3 className="text-lg font-medium text-gray-700 mb-2">No Clients Found</h3>
                <p className="text-gray-500">
                  {searchTerm ? 'No clients match your search criteria.' : 'No clients are currently connected.'}
                </p>
              </div>
            ) : (
              filteredClients.map((client, index) => (
                <div
                  key={client.client_id || `client-${index}`}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-3 h-3 rounded-full ${
                      client.status === 'active' ? 'bg-green-500' : 'bg-red-500'
                    }`} />
                    
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-gray-900">
                          {client.display_name || client.hostname || client.client_id}
                        </h3>
                        {client.status === 'active' ? (
                          <Wifi className="w-4 h-4 text-green-500" />
                        ) : (
                          <WifiOff className="w-4 h-4 text-red-500" />
                        )}
                      </div>
                      
                      <div className="flex items-center gap-4 text-sm text-gray-600 mt-1">
                        <span>IP: {client.ip_address}</span> {/* Using ip_address from global interface */}
                        {client.group_name && (
                          <Badge variant="secondary" className="text-xs">
                            {client.group_name}
                          </Badge>
                        )}
                        {client.stream_assignment && (
                          <Badge variant="outline" className="text-xs">
                            {client.stream_assignment}
                          </Badge>
                        )}
                        {client.last_seen_formatted && (
                          <span className="text-xs">
                            Last seen: {client.last_seen_formatted}
                          </span>
                        )}
                        {client.screen_number !== undefined && (
                          <Badge variant="outline" className="text-xs">
                            Screen {client.screen_number + 1}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => moveClient(client.client_id, 'up')}
                      disabled={index === 0}
                      className="p-2"
                    >
                      <ArrowUp className="w-4 h-4" />
                    </Button>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => moveClient(client.client_id, 'down')}
                      disabled={index === filteredClients.length - 1}
                      className="p-2"
                    >
                      <ArrowDown className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Client Statistics */}
      {clients.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="bg-white border border-gray-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Clients</p>
                  <p className="text-2xl font-bold text-gray-900">{clients.length}</p>
                </div>
                <Monitor className="w-8 h-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white border border-gray-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Active Clients</p>
                  <p className="text-2xl font-bold text-green-600">
                    {clients.filter(c => c.status === 'active').length}
                  </p>
                </div>
                <Wifi className="w-8 h-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white border border-gray-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Inactive Clients</p>
                  <p className="text-2xl font-bold text-red-600">
                    {clients.filter(c => c.status === 'inactive').length}
                  </p>
                </div>
                <WifiOff className="w-8 h-8 text-red-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default ClientsTab;
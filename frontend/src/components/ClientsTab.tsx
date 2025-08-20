// Alternative: Self-loading ClientsTab - frontend/src/components/ClientsTab.tsx

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { ArrowUp, ArrowDown, Monitor, Wifi, WifiOff, Search, Users, RefreshCw } from "lucide-react";
import { useErrorHandler } from "@/components/ErrorSystem/useErrorHandler";
import { clientApi } from '@/API/api';
import type { Client } from '@/types';

// Make ClientsTab self-loading (remove props dependency)
const ClientsTab = () => {
  const { showError } = useErrorHandler();
  const [searchTerm, setSearchTerm] = useState('');
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Load clients data
  const loadClients = async (showRefreshing = false) => {
    try {
      if (showRefreshing) setRefreshing(true);
      console.log(' Loading clients data...');

      const clientsData = await clientApi.getClients();
      console.log(' Raw API response:', clientsData);
      console.log(' All clients:', clientsData.clients);

      // Filter to only show active/connected clients
      const activeClients = (clientsData.clients || []).filter(client => client.status === 'active');
      console.log(' Active clients only:', activeClients);

      setClients(activeClients);

      if (showRefreshing) {
        showError({
          message: `Clients refreshed successfully. Found ${activeClients.length} active clients (${clientsData.clients?.length || 0} total)`,
          error_code: 'CLIENTS_REFRESHED',
          error_category: '2xx',
          context: {
            component: 'ClientsTab',
            operation: 'refreshClients',
            active_clients: activeClients.length,
            total_clients: clientsData.clients?.length || 0,
            timestamp: new Date().toISOString()
          }
        });
      }
    } catch (error: any) {
      console.error(' Error loading clients:', error);
      showError({
        message: "Failed to load clients",
        error_code: 'CLIENTS_LOAD_FAILED',
        error_category: '5xx',
        context: {
          component: 'ClientsTab',
          operation: 'loadClients',
          timestamp: new Date().toISOString(),
          original_error: error?.message,
          stack: error?.stack
        }
      });
    } finally {
      setLoading(false);
      if (showRefreshing) setRefreshing(false);
    }
  };

  // Load initial data and set up refresh interval
  useEffect(() => {
    loadClients();

    // Refresh clients every 5 seconds
    const interval = setInterval(() => {
      loadClients();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

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
      (client.ip_address?.toLowerCase().includes(searchLower))
    );
  });

  // Debug logging
  useEffect(() => {
    console.log(' ClientsTab state:', {
      loading,
      clientsCount: clients.length,
      filteredCount: filteredClients.length,
      clients: clients
    });
  }, [loading, clients, filteredClients]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading clients...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="bg-white border border-gray-200">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Users className="w-5 h-5" />
                Active Clients ({clients.length})
              </CardTitle>
              <CardDescription>
                Connected clients only. Disconnected clients are automatically removed. Auto-refreshes every 5 seconds.
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => loadClients(true)}
              disabled={refreshing}
              className="flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
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

          {/* Debug Info */}
          <div className="mb-4 p-3 bg-gray-100 rounded text-sm text-gray-600">
            Debug: {clients.length} active clients connected, {filteredClients.length} shown after filtering
          </div>

          {/* Clients List */}
          <div className="space-y-3">
            {filteredClients.length === 0 ? (
              <div className="text-center py-8">
                <Monitor className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <h3 className="text-lg font-medium text-gray-700 mb-2">
                  {clients.length === 0 ? 'No Active Clients' : 'No Clients Found'}
                </h3>
                <p className="text-gray-500">
                  {searchTerm
                    ? 'No active clients match your search criteria.'
                    : clients.length === 0
                      ? 'No clients are currently connected to the server. When clients connect, they will appear here automatically.'
                      : 'All clients are filtered out.'
                  }
                </p>
                {clients.length === 0 && (
                  <Button
                    variant="outline"
                    onClick={() => loadClients(true)}
                    className="mt-4"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Check for Clients
                  </Button>
                )}
              </div>
            ) : (
              filteredClients.map((client, index) => (
                <div
                  key={client.client_id || `client-${index}`}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    {/* Always green since we only show connected clients */}
                    <div className="w-3 h-3 rounded-full bg-green-500" />

                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-gray-900">
                          {client.display_name || client.hostname || client.client_id}
                        </h3>
                        {/* Always show as connected since we only display active clients */}
                        <Badge variant="default" className="bg-green-100 text-green-800 border-green-200">
                          Connected
                        </Badge>
                      </div>

                      <div className="flex items-center gap-4 text-sm text-gray-600 mt-1">
                        <span>IP: {client.ip_address}</span>
                        <span>ID: {client.client_id}</span>
                        {client.group_name && (
                          <Badge variant="secondary" className="text-xs">
                            Group: {client.group_name}
                          </Badge>
                        )}
                        {client.stream_assignment && (
                          <Badge variant="outline" className="text-xs">
                            Stream: {client.stream_assignment}
                          </Badge>
                        )}
                        {client.last_seen_formatted && (
                          <span className="text-xs">
                            Last seen: {client.last_seen_formatted}
                          </span>
                        )}
                        {client.screen_number !== undefined && client.screen_number !== null && (
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

      {/* Client Statistics - Updated for active clients only */}
      {clients.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="bg-white border border-gray-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Connected Clients</p>
                  <p className="text-2xl font-bold text-green-600">{clients.length}</p>
                </div>
                <Wifi className="w-8 h-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white border border-gray-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Assigned to Groups</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {clients.filter(c => c.group_id).length}
                  </p>
                </div>
                <Monitor className="w-8 h-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default ClientsTab;
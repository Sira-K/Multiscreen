import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { ArrowUp, ArrowDown, Monitor, Wifi, WifiOff, Search } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { clientApi } from '@/lib/api';


interface Client {
  client_id: string;  // Changed from 'id'
  display_name?: string;  // Optional display name
  hostname?: string;  // Changed from 'name' 
  ip: string;
  status: 'active' | 'inactive';
  stream_id?: string | null;  // Changed from 'connectedStream'
  last_seen_formatted?: string;  // Changed from 'lastSeen'
  group_id?: string | null;
  group_name?: string | null;
  order?: number;  // Make optional since API might not provide this
}

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
    
    // Swap the clients
    [newClients[clientIndex], newClients[targetIndex]] = [newClients[targetIndex], newClients[clientIndex]];
    
    // Update order numbers
    newClients.forEach((client, index) => {
      client.order = index + 1;
    });

    setClients(newClients);
    toast({
      title: "Client Reordered",
      description: `${newClients[targetIndex].display_name || newClients[targetIndex].hostname} moved ${direction}`
    });
  };

  const filteredClients = clients.filter(client =>
    (client.display_name || client.hostname || client.client_id).toLowerCase().includes(searchTerm.toLowerCase()) ||
    client.ip.includes(searchTerm)
  );
  
  useEffect(() => {
    const fetchClients = async () => {
      try {
        const response = await clientApi.getClients();
        setClients(response.clients || []);
      } catch (error) {
        console.error('Error fetching clients:', error);
        // Remove this fallback to mock data:
        // setClients(mockClients);
        setClients([]); // Show empty array instead of mock data
      }
    };
    
    fetchClients();

    // Auto-refresh every 5 seconds to show new clients
    const interval = setInterval(fetchClients, 5000);
    
    // Cleanup interval on component unmount
    return () => clearInterval(interval);
    
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold text-black mb-2">Client Management</h2>
        <p className="text-gray-400">Monitor and manage connected display clients</p>
      </div>

      {/* Search and Controls */}
      <Card className="bg-white border border-gray-200">
        <CardHeader>
          <CardTitle className="text-gray-800">Search Clients</CardTitle>
          <CardDescription className="text-gray-600">
            Find clients by name or IP address
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <Input
              placeholder="Search by name or IP address..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 bg-white border-gray-300 text-gray-900"
            />
          </div>
        </CardContent>
      </Card>

      {/* Clients List */}
      <Card className="bg-white border border-gray-200">
        <CardHeader>
          <CardTitle className="text-gray-800">Client List</CardTitle>
          <CardDescription className="text-gray-600">
            Manage client display order and view connection status
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {filteredClients.map((client, index) => (
              <div
                key={client.client_id}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="flex flex-col gap-1">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => moveClient(client.client_id, 'up')}
                      disabled={index === 0}
                      className="h-6 w-8 p-0 border-gray-300 text-gray-500 disabled:opacity-30 hover:bg-gray-200"
                    >
                      <ArrowUp className="w-3 h-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => moveClient(client.client_id, 'down')}
                      disabled={index === filteredClients.length - 1}
                      className="h-6 w-8 p-0 border-gray-300 text-gray-500 disabled:opacity-30 hover:bg-gray-200"
                    >
                      <ArrowDown className="w-3 h-3" />
                    </Button>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-10 h-10 bg-gray-200 rounded-lg">
                      <Monitor className="w-5 h-5 text-gray-600" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-gray-800">
                          {client.display_name || client.hostname || client.client_id}
                        </h3>
                        <Badge 
                          variant={client.status === 'active' ? 'default' : 'secondary'}
                          className={`flex items-center gap-1 ${client.status === 'active' 
                            ? 'bg-green-100 text-green-800 border-green-200' 
                            : 'bg-red-100 text-red-800 border-red-200'
                          }`}
                        >
                          {client.status === 'active' ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
                          {client.status}
                        </Badge>
                      </div>
                      <div className="text-sm text-gray-600">
                        IP: {client.ip} • Last seen: {client.last_seen_formatted || 'Unknown'}
                      </div>
                      {client.stream_id && (
                        <div className="text-sm text-blue-600 mt-1 font-medium">
                          Connected to: {client.stream_id}
                        </div>
                      )}
                      {client.group_name && (
                        <div className="text-sm text-purple-600 mt-1 font-medium">
                          Group: {client.group_name}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className="text-sm text-gray-500 font-medium">Order</div>
                    <div className="text-lg font-semibold text-gray-800">#{client.order || index + 1}</div>
                  </div>
                  <div className={`w-3 h-3 rounded-full ${
                    client.status === 'active' ? 'bg-green-500' : 'bg-red-500'
                  }`}></div>
                </div>
              </div>
            ))}
          </div>

          {filteredClients.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <Monitor className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No clients found matching your search criteria.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
export default ClientsTab;

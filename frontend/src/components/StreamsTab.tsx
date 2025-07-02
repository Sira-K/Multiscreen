
import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plus, X, Users, Play, Square, Monitor} from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";

interface Stream {
  id: string;
  name: string;
  url: string;
  port: number;
  status: 'active' | 'inactive';
  clients: string[];
}

interface Client {
  id: string;
  name: string;
  ip: string;
  status: 'active' | 'inactive';
  connectedStream: string | null;
  lastSeen: string;
  order: number;
}

interface StreamsTabProps {
  streams: Stream[];
  setStreams: React.Dispatch<React.SetStateAction<Stream[]>>;
  clients: Client[];
}

const StreamsTab = ({ streams, setStreams, clients }: StreamsTabProps) => {
  const { toast } = useToast();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newStreamName, setNewStreamName] = useState('');
  const [newStreamPort, setNewStreamPort] = useState('');

  const addStream = () => {
    if (!newStreamName || !newStreamPort) {
      toast({
        title: "Error",
        description: "Please fill in all fields",
        variant: "destructive"
      });
      return;
    }

    const newStream: Stream = {
      id: Date.now().toString(),
      name: newStreamName,
      url: `srt://192.168.1.100:${newStreamPort}`,
      port: parseInt(newStreamPort),
      status: 'inactive',
      clients: []
    };

    setStreams([...streams, newStream]);
    setNewStreamName('');
    setNewStreamPort('');
    setIsDialogOpen(false);
    toast({
      title: "Stream Added",
      description: `${newStreamName} has been created successfully`
    });
  };

  const removeStream = (streamId: string) => {
    setStreams(streams.filter(stream => stream.id !== streamId));
    toast({
      title: "Stream Removed",
      description: "Stream has been deleted successfully"
    });
  };

  const toggleStreamStatus = (streamId: string) => {
    setStreams(streams.map(stream => 
      stream.id === streamId 
        ? { ...stream, status: stream.status === 'active' ? 'inactive' : 'active' }
        : stream
    ));
  };

  const addClientToStream = (streamId: string, clientId: string) => {
    // Remove client from any other stream first (one stream per client rule)
    const updatedStreams = streams.map(stream => ({
      ...stream,
      clients: stream.clients.filter(c => c !== clientId)
    }));
    
    // Add client to the target stream
    setStreams(updatedStreams.map(stream => 
      stream.id === streamId 
        ? { ...stream, clients: [...stream.clients, clientId] }
        : stream
    ));
    
    toast({
      title: "Client Assigned",
      description: "Client has been assigned to the stream"
    });
  };

  const removeClientFromStream = (streamId: string, clientId: string) => {
    setStreams(streams.map(stream => 
      stream.id === streamId 
        ? { ...stream, clients: stream.clients.filter(c => c !== clientId) }
        : stream
    ));
    toast({
      title: "Client Removed",
      description: "Client has been removed from the stream"
    });
  };


  const getClientName = (clientId: string) => {
    return clients.find(c => c.id === clientId)?.name || clientId;
  };

  const getUnassignedClients = (streamId: string) => {
    const allAssignedClients = streams.flatMap(stream => stream.clients);
    return clients.filter(client => !allAssignedClients.includes(client.id));
  };

  return (
    <div className="space-y-6">
      {/* Header with Add Stream Button */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-semibold text-black mb-2">Stream Management</h2>
          <p className="text-gray-400">Manage your SRT streaming endpoints</p>
        </div>
        <Button 
          onClick={() => setIsDialogOpen(!isDialogOpen)} 
          className="bg-blue-600 hover:bg-blue-700 text-white"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add New Stream
        </Button>
      </div>

      {/* Add New Stream Form - Conditionally Rendered */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus className="w-5 h-5" />
              Create New Stream
            </DialogTitle>
            <DialogDescription>
              Configure a new SRT stream for client connections
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="streamName">Stream Name</Label>
              <Input
                id="streamName"
                value={newStreamName}
                onChange={(e) => setNewStreamName(e.target.value)}
                placeholder="e.g., Conference Room Display"
              />
            </div>
            
            <div className="grid gap-2">
              <Label htmlFor="streamPort">Port</Label>
              <Input
                id="streamPort"
                type="number"
                value={newStreamPort}
                onChange={(e) => setNewStreamPort(e.target.value)}
                placeholder="e.g., 10080"
              />
            </div>
          </div>
          
          <div className="flex justify-end gap-3">
            <Button
              variant="outline"
              onClick={() => setIsDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button 
              onClick={addStream} 
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Stream
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Streams List */}
      {streams.length === 0 ? (
        <Card className="bg-white border border-gray-200">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Monitor className="w-16 h-16 text-gray-400 mb-4" />
            <h3 className="text-lg font-semibold text-gray-800 mb-2">No Streams Created</h3>
            <p className="text-gray-600 text-center mb-6 max-w-md">
              Get started by creating your first SRT stream. Streams allow you to broadcast content to multiple display clients simultaneously.
            </p>
            <Button 
              onClick={() => setIsDialogOpen(true)} 
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Your First Stream
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {streams.map((stream) => (
            <Card key={stream.id} className="bg-white border border-gray-200 shadow-sm">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-gray-800 flex items-center gap-2">
                      {stream.name}
                      <Badge 
                        variant={stream.status === 'active' ? 'default' : 'secondary'}
                        className={stream.status === 'active' 
                          ? 'bg-green-100 text-green-800 border-green-200' 
                          : 'bg-gray-100 text-gray-600 border-gray-200'
                        }
                      >
                        {stream.status}
                      </Badge>
                    </CardTitle>
                    <CardDescription className="text-gray-600">
                      {stream.url}
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant={stream.status === 'active' ? 'destructive' : 'default'}
                      onClick={() => toggleStreamStatus(stream.id)}
                      className={stream.status === 'active' 
                        ? 'bg-red-600 hover:bg-red-700 text-white' 
                        : 'bg-green-600 hover:bg-green-700 text-white'
                      }
                    >
                      {stream.status === 'active' ? <Square className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => removeStream(stream.id)}
                      className="border-gray-300 text-gray-600 hover:bg-gray-50"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <Users className="w-4 h-4 text-gray-500" />
                      <span className="text-gray-700 font-medium text-sm">Connected Clients ({stream.clients.length})</span>
                    </div>
                    <div className="space-y-2">
                      {stream.clients.map((clientId) => (
                        <div key={clientId} className="flex items-center justify-between bg-gray-50 p-3 rounded-lg border border-gray-200">
                          <span className="text-gray-800 text-sm font-medium">{getClientName(clientId)}</span>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => removeClientFromStream(stream.id, clientId)}
                            className="h-7 w-7 p-0 border-gray-300 text-gray-500 hover:bg-gray-100"
                          >
                            <X className="w-3 h-3" />
                          </Button>
                        </div>
                      ))}
                      {stream.clients.length === 0 && (
                        <div className="text-center py-4 text-gray-500 text-sm">
                          No clients connected
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div>
                    <Label className="text-gray-700 font-medium text-sm">Available Clients</Label>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {getUnassignedClients(stream.id).map((client) => (
                        <Button
                          key={client.id}
                          size="sm"
                          variant="outline"
                          onClick={() => addClientToStream(stream.id, client.id)}
                          className="border-blue-300 text-blue-700 hover:bg-blue-50"
                        >
                          <Plus className="w-3 h-3 mr-1" />
                          {client.name}
                        </Button>
                      ))}
                      {getUnassignedClients(stream.id).length === 0 && (
                        <span className="text-gray-500 text-sm py-2">All clients are assigned</span>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default StreamsTab;

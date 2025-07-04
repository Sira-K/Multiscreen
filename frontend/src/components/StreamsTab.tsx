import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plus, X, Users, Monitor, Wifi, WifiOff, AlertCircle } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import FlaskStreamControlButton from "@/components/ui/StreamControlButton"; // Updated import
import { useFlaskWebSocketStreamControl } from "@/hooks/useWebSocketStreamControl"; // Updated import
import { useToast } from "@/hooks/use-toast";

interface Stream {
  id: string;
  name: string;
  url: string;
  port: number;
  status: 'active' | 'inactive';
  clients: string[];
  // Add Flask-specific fields
  groupId?: string;
  groupName?: string;
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
  wsUrl?: string; // Flask WebSocket URL
}

const StreamsTab = ({ streams, setStreams, clients, wsUrl }: StreamsTabProps) => {
  const { toast } = useToast();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newStreamName, setNewStreamName] = useState('');
  const [newStreamPort, setNewStreamPort] = useState('');

  // Initialize Flask WebSocket connection
  const {
    isConnected,
    isLoading,
    connectionStatus,
    startStream,
    stopStream,
    streamStatuses,
    getStreamStatus,
    setOnStreamStatusChange,
    setOnClientStatusChange,
    reconnect
  } = useFlaskWebSocketStreamControl({
    wsUrl: wsUrl || 'http://localhost:3001' // Flask SocketIO URL
  });

  // Set up real-time event handlers
  useEffect(() => {
    // Handle stream status changes from Flask WebSocket
    setOnStreamStatusChange((streamId: string, status: 'active' | 'inactive') => {
      setStreams(prev => prev.map(stream => {
        // Match by either id or groupId
        if (stream.id === streamId || stream.groupId === streamId) {
          return { ...stream, status };
        }
        return stream;
      }));
    });

    // Handle client connection changes from Flask WebSocket
    setOnClientStatusChange((streamId: string, connectedClients: string[]) => {
      setStreams(prev => prev.map(stream => {
        // Match by either id or groupId
        if (stream.id === streamId || stream.groupId === streamId) {
          return { ...stream, clients: connectedClients };
        }
        return stream;
      }));
    });
  }, [setOnStreamStatusChange, setOnClientStatusChange, setStreams]);

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
      clients: [],
      // Add group information for Flask backend
      groupId: Date.now().toString(),
      groupName: newStreamName
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
    // Stop stream first if it's active
    const stream = streams.find(s => s.id === streamId);
    if (stream?.status === 'active') {
      // Use groupId if available, otherwise use streamId
      const targetId = stream.groupId || streamId;
      stopStream(targetId);
    }
    
    setStreams(streams.filter(stream => stream.id !== streamId));
    toast({
      title: "Stream Removed",
      description: "Stream has been deleted successfully"
    });
  };

  const toggleStreamStatus = (streamId: string) => {
    // This will be called by FlaskStreamControlButton for optimistic updates
    // The real state update will come from WebSocket
    const stream = streams.find(s => s.id === streamId);
    if (stream) {
      setStreams(prev => prev.map(s => 
        s.id === streamId 
          ? { ...s, status: s.status === 'active' ? 'inactive' : 'active' }
          : s
      ));
    }
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

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'text-green-600';
      case 'connecting': return 'text-yellow-600';
      case 'disconnected': return 'text-gray-600';
      case 'error': return 'text-red-600';
    }
  };

  const getConnectionStatusIcon = () => {
    switch (connectionStatus) {
      case 'connected': return <Wifi className="w-4 h-4" />;
      case 'connecting': return <Wifi className="w-4 h-4 animate-pulse" />;
      case 'disconnected':
      case 'error': return <WifiOff className="w-4 h-4" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Connection Status Alert */}
      {connectionStatus !== 'connected' && (
        <Alert className={connectionStatus === 'error' ? 'border-red-200 bg-red-50' : 'border-yellow-200 bg-yellow-50'}>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>
              {connectionStatus === 'connecting' && 'Connecting to Flask stream server...'}
              {connectionStatus === 'disconnected' && 'Disconnected from Flask stream server. Trying to reconnect...'}
              {connectionStatus === 'error' && 'Failed to connect to Flask stream server. Real-time updates unavailable.'}
            </span>
            {connectionStatus === 'error' && (
              <Button size="sm" variant="outline" onClick={reconnect}>
                Retry Connection
              </Button>
            )}
          </AlertDescription>
        </Alert>
      )}

      {/* Header with Add Stream Button */}
      <div className="flex justify-between items-center">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <h2 className="text-2xl font-semibold text-black">Stream Management</h2>
            <div className={`flex items-center gap-1 ${getConnectionStatusColor()}`}>
              {getConnectionStatusIcon()}
              <span className="text-sm capitalize">{connectionStatus}</span>
            </div>
          </div>
          <p className="text-gray-400">Manage your SRT streaming endpoints with real-time monitoring</p>
        </div>
        <Button 
          onClick={() => setIsDialogOpen(!isDialogOpen)} 
          className="bg-blue-600 hover:bg-blue-700 text-white"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add New Stream
        </Button>
      </div>

      {/* Add New Stream Dialog */}
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
          {streams.map((stream) => {
            // Get WebSocket status using groupId if available, otherwise streamId
            const statusKey = stream.groupId || stream.id;
            const wsStatus = getStreamStatus(statusKey);
            
            return (
              <Card key={stream.id} className="bg-white border border-gray-200 shadow-sm">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-gray-800 flex items-center gap-2">
                        {stream.groupName || stream.name}
                        <Badge 
                          variant={stream.status === 'active' ? 'default' : 'secondary'}
                          className={stream.status === 'active' 
                            ? 'bg-green-100 text-green-800 border-green-200' 
                            : 'bg-gray-100 text-gray-600 border-gray-200'
                          }
                        >
                          {stream.status}
                        </Badge>
                        {wsStatus && (
                          <Badge variant="outline" className="text-xs">
                            {wsStatus.clientCount} clients
                          </Badge>
                        )}
                      </CardTitle>
                      <CardDescription className="text-gray-600">
                        {stream.url}
                        {stream.groupId && (
                          <span className="block text-xs text-gray-500 mt-1">
                            Group ID: {stream.groupId}
                          </span>
                        )}
                      </CardDescription>
                    </div>
                    <div className="flex gap-2">
                      <FlaskStreamControlButton
                        streamId={stream.id}
                        streamName={stream.name}
                        isActive={stream.status === 'active'}
                        onToggle={toggleStreamStatus}
                        startStream={startStream}
                        stopStream={stopStream}
                        isLoading={isLoading}
                        isConnected={isConnected}
                        connectionStatus={connectionStatus}
                        groupId={stream.groupId}
                        groupName={stream.groupName}
                        size="sm"
                      />
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
                        {wsStatus && wsStatus.availableStreams.length > 0 && (
                          <span className="text-xs text-gray-500">
                            ({wsStatus.availableStreams.length} streams available)
                          </span>
                        )}
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
                    
                    {/* Show Flask-specific stream information */}
                    {wsStatus && wsStatus.currentVideo && (
                      <div className="pt-2 border-t border-gray-200">
                        <span className="text-xs text-gray-500">
                          Current Video: {wsStatus.currentVideo}
                        </span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default StreamsTab;
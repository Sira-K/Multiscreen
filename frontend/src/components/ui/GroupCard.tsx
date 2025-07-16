// frontend/src/components/ui/GroupCard.tsx

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Play, Square, Users, Monitor, Power, AlertCircle } from "lucide-react";
import type { Video } from '@/types';

interface Client {
  client_id: string;
  display_name?: string;
  hostname?: string;
  ip_address?: string; // Changed from 'ip' to match your backend
  is_active?: boolean;
  group_id?: string | null;
  // Add other client properties as needed
}

interface Group {
  id: string;
  name: string;
  description?: string;
  screen_count: number;
  orientation: 'horizontal' | 'vertical' | 'grid';
  docker_running: boolean;
  active_clients?: number;
  // Add other group properties as needed
}

interface GroupCardProps {
  group: Group;
  videos: Video[];
  clients: Client[];
  unassignedClients: Client[];
  selectedVideo?: string;
  isStreaming: boolean;
  operationInProgress: string | null;
  onVideoSelect: (groupId: string, videoName: string) => void;
  onStart: (groupId: string, groupName: string) => void;
  onStop: (groupId: string, groupName: string) => void;
  onDelete: (groupId: string, groupName: string) => void;
  onAssignClient: (clientId: string, groupId: string) => void;
}

const GroupCard = ({
  group,
  videos,
  clients,
  unassignedClients,
  selectedVideo,
  isStreaming,
  operationInProgress,
  onVideoSelect,
  onStart,
  onStop,
  onDelete,
  onAssignClient
}: GroupCardProps) => {
  return (
    <div className="border rounded-lg overflow-hidden bg-white">
      <div className="p-4 border-b flex justify-between items-center">
        <div>
          <h3 className="font-medium text-lg flex items-center gap-2">
            {group.name}
            {group.docker_running ? (
              <Badge variant="outline" className="text-green-600 border-green-300">
                <Power className="w-3 h-3 mr-1" />
                Running
              </Badge>
            ) : (
              <Badge variant="outline" className="text-red-600 border-red-300">
                <AlertCircle className="w-3 h-3 mr-1" />
                Stopped
              </Badge>
            )}
          </h3>
          <p className="text-sm text-gray-500">{group.description || 'No description'}</p>
        </div>
        
        <div className="flex gap-2">
          {isStreaming ? (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => onStop(group.id, group.name)}
              disabled={operationInProgress === group.id}
            >
              {operationInProgress === group.id ? 'Stopping...' : (
                <>
                  <Square className="h-4 w-4 mr-2" />
                  Stop Stream
                </>
              )}
            </Button>
          ) : (
            <Button
              variant="default"
              size="sm"
              onClick={() => onStart(group.id, group.name)}
              disabled={operationInProgress === group.id || !selectedVideo || !group.docker_running}
            >
              {operationInProgress === group.id ? 'Starting...' : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Start Stream
                </>
              )}
            </Button>
          )}
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => onDelete(group.id, group.name)}
            disabled={operationInProgress === group.id}
          >
            Delete
          </Button>
        </div>
      </div>
      
      <div className="p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-1">
            <h4 className="text-sm font-medium text-gray-700">Clients</h4>
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-gray-500" />
              <span className="text-sm">
                {clients.length} assigned ({group.active_clients || 0} active)
              </span>
            </div>
          </div>
          
          <div className="space-y-1">
            <h4 className="text-sm font-medium text-gray-700">Layout</h4>
            <div className="text-sm">
              {group.screen_count} screens • {group.orientation}
            </div>
          </div>
          
          <div className="space-y-1">
            <h4 className="text-sm font-medium text-gray-700">Status</h4>
            <div className="text-sm">
              {isStreaming ? (
                <Badge variant="outline" className="text-green-600 border-green-300">
                  Streaming
                </Badge>
              ) : (
                <Badge variant="outline" className="text-gray-600 border-gray-300">
                  Idle
                </Badge>
              )}
            </div>
          </div>
        </div>
        
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Video Source</h4>
          <Select
            value={selectedVideo || ''}
            onValueChange={(value) => onVideoSelect(group.id, value)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select a video..." />
            </SelectTrigger>
            <SelectContent>
              {videos.map((video) => (
                <SelectItem 
                  key={video.name}  // Using name as key since id might not exist
                  value={video.name}
                >
                  {video.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        {unassignedClients.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Assign Client</h4>
            <Select
              onValueChange={(clientId) => onAssignClient(clientId, group.id)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a client to assign..." />
              </SelectTrigger>
              <SelectContent>
                {unassignedClients.map((client) => (
                  <SelectItem 
                    key={client.client_id} 
                    value={client.client_id}
                  >
                    {client.display_name || client.hostname || client.client_id}
                    {client.ip_address && ` (${client.ip_address})`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>
    </div>
  );
};

export default GroupCard;
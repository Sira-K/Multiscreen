// frontend/src/components/ui/GroupCard.tsx - Updated for Hybrid Architecture

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Play, Square, Monitor, Users, CheckCircle, AlertCircle, Container, Wifi } from "lucide-react";
import type { Group, Client, Video } from '@/types';

interface GroupCardProps {
  group: Group;
  videos: Video[];
  clients: Client[];  // Clients assigned to this group
  unassignedClients: Client[];  // Clients not assigned to any group
  selectedVideo: string | undefined;
  operationInProgress: string | null;
  onVideoSelect: (groupId: string, videoName: string) => void;
  onStart: (groupId: string, groupName: string) => void;
  onStop: (groupId: string, groupName: string) => void;
  onDelete: (groupId: string, groupName: string) => void;
  onAssignClient: (clientId: string, groupId: string) => void;
}

const GroupCard: React.FC<GroupCardProps> = ({
  group,
  videos,
  clients,
  unassignedClients,
  selectedVideo,
  operationInProgress,
  onVideoSelect,
  onStart,
  onStop,
  onDelete,
  onAssignClient,
}) => {
  console.log(`🔍 GroupCard (Hybrid) - Group "${group.name}":`, {
    docker_running: group.docker_running,
    docker_status: group.docker_status,
    total_clients: clients.length,
    active_clients: clients.filter(c => c.is_active).length,
    ports: group.ports
  });

  // Determine if streaming can be started (Docker must be running)
  const canStartStreaming = group.docker_running && !operationInProgress;
  const canStopStreaming = group.docker_running && operationInProgress !== group.id;
  
  // Status indicators
  const getDockerStatusBadge = () => {
    if (group.docker_running) {
      return <Badge variant="default" className="bg-green-100 text-green-800">Docker Running</Badge>;
    } else {
      return <Badge variant="destructive">Docker Stopped</Badge>;
    }
  };

  const getStreamingStatusBadge = () => {
    if (group.streaming_active) {
      return <Badge variant="default" className="bg-blue-100 text-blue-800">Streaming Active</Badge>;
    } else if (group.docker_running) {
      return <Badge variant="outline">Ready to Stream</Badge>;
    } else {
      return <Badge variant="secondary">Cannot Stream</Badge>;
    }
  };

  return (
    <Card className="bg-white border border-gray-200">
      <CardHeader>
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-gray-800 flex items-center gap-2">
              <Container className="h-5 w-5 text-blue-600" />
              {group.name}
            </CardTitle>
            <CardDescription className="text-gray-600">
              {group.description || 'No description'}
            </CardDescription>
            <div className="text-sm text-gray-500 mt-1">
              ID: {group.id.substring(0, 8)}... • Created: {group.created_at_formatted}
            </div>
          </div>
          <div className="flex flex-col gap-2">
            {getDockerStatusBadge()}
            {getStreamingStatusBadge()}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Configuration Info */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-3 bg-gray-50 rounded-lg">
          <div>
            <div className="text-sm font-medium text-gray-700">Screens</div>
            <div className="text-lg font-semibold text-gray-900">{group.screen_count}</div>
          </div>
          <div>
            <div className="text-sm font-medium text-gray-700">Layout</div>
            <div className="text-lg font-semibold text-gray-900 capitalize">{group.orientation}</div>
          </div>
          <div>
            <div className="text-sm font-medium text-gray-700">SRT Port</div>
            <div className="text-lg font-semibold text-gray-900">{group.ports.srt_port}</div>
          </div>
          <div>
            <div className="text-sm font-medium text-gray-700">Clients</div>
            <div className="text-lg font-semibold text-gray-900">
              {clients.filter(c => c.is_active).length}/{clients.length}
            </div>
          </div>
        </div>

        {/* Docker Container Info */}
        <div className="p-3 bg-blue-50 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <Container className="h-4 w-4 text-blue-600" />
            <span className="font-medium text-blue-800">Docker Container</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-blue-700">Status:</span> 
              <span className="ml-1 font-medium">{group.docker_status}</span>
            </div>
            <div>
              <span className="text-blue-700">Container:</span> 
              <span className="ml-1 font-mono text-xs">{group.container_id.substring(0, 12)}...</span>
            </div>
          </div>
          <div className="mt-2 text-xs text-blue-600">
            Ports: RTMP:{group.ports.rtmp_port} | HTTP:{group.ports.http_port} | API:{group.ports.api_port} | SRT:{group.ports.srt_port}
          </div>
        </div>

        {/* Video Selection */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">Video File (Optional)</label>
          <Select 
            value={selectedVideo || ''} 
            onValueChange={(value) => onVideoSelect(group.id, value)}
            disabled={operationInProgress === group.id}
          >
            <SelectTrigger className="bg-white border-gray-300">
              <SelectValue placeholder="Select video file or use test pattern" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Test Pattern (Default)</SelectItem>
              {videos.map((video) => (
                <SelectItem key={video.name} value={video.path}>
                  {video.name} ({video.size_mb.toFixed(1)} MB)
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Assigned Clients */}
        {clients.length > 0 && (
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">Assigned Clients</label>
            <div className="space-y-1">
              {clients.map((client) => (
                <div key={client.client_id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <div className="flex items-center gap-2">
                    <Wifi className={`h-4 w-4 ${client.is_active ? 'text-green-500' : 'text-gray-400'}`} />
                    <span className="text-sm font-medium">
                      {client.display_name || client.hostname}
                    </span>
                    <span className="text-xs text-gray-500">({client.ip_address})</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={client.is_active ? "default" : "secondary"} className="text-xs">
                      {client.is_active ? "Active" : "Inactive"}
                    </Badge>
                    {client.stream_assignment && (
                      <Badge variant="outline" className="text-xs">
                        {client.stream_assignment}
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Assign Unassigned Clients */}
        {unassignedClients.length > 0 && (
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">Assign Clients</label>
            <div className="space-y-1">
              {unassignedClients.slice(0, 3).map((client) => (
                <div key={client.client_id} className="flex items-center justify-between p-2 bg-yellow-50 rounded">
                  <div className="flex items-center gap-2">
                    <Wifi className={`h-4 w-4 ${client.is_active ? 'text-green-500' : 'text-gray-400'}`} />
                    <span className="text-sm">
                      {client.display_name || client.hostname}
                    </span>
                    <span className="text-xs text-gray-500">({client.ip_address})</span>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onAssignClient(client.client_id, group.id)}
                    disabled={operationInProgress === `assign-${client.client_id}`}
                  >
                    {operationInProgress === `assign-${client.client_id}` ? 'Assigning...' : 'Assign'}
                  </Button>
                </div>
              ))}
              {unassignedClients.length > 3 && (
                <div className="text-xs text-gray-500 text-center py-1">
                  ... and {unassignedClients.length - 3} more unassigned clients
                </div>
              )}
            </div>
          </div>
        )}

        {/* Error Messages */}
        {!group.docker_running && (
          <div className="p-3 bg-red-50 rounded-lg">
            <div className="flex items-center gap-2 text-red-800">
              <AlertCircle className="h-4 w-4" />
              <span className="font-medium">Docker Container Required</span>
            </div>
            <p className="text-sm text-red-700 mt-1">
              The Docker container must be running before streaming can be started.
              The container may have stopped or failed to start.
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2">
          {group.streaming_active ? (
            <Button
              onClick={() => onStop(group.id, group.name)}
              disabled={!canStopStreaming}
              variant="destructive"
              className="flex-1"
            >
              <Square className="h-4 w-4 mr-2" />
              {operationInProgress === group.id ? 'Stopping...' : 'Stop Streaming'}
            </Button>
          ) : (
            <Button
              onClick={() => onStart(group.id, group.name)}
              disabled={!canStartStreaming}
              className="flex-1"
            >
              <Play className="h-4 w-4 mr-2" />
              {operationInProgress === group.id ? 'Starting...' : 'Start Streaming'}
            </Button>
          )}
          
          <Button
            onClick={() => onDelete(group.id, group.name)}
            disabled={operationInProgress === group.id}
            variant="outline"
            className="text-red-600 hover:text-red-700 hover:bg-red-50"
          >
            Delete
          </Button>
        </div>

        {/* Stream URLs for Active Streaming */}
        {group.streaming_active && group.available_streams && group.available_streams.length > 0 && (
          <div className="mt-4 p-3 bg-green-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <span className="font-medium text-green-800">Active Stream URLs</span>
            </div>
            <div className="space-y-1">
              {group.available_streams.slice(0, 2).map((streamPath, index) => (
                <div key={index} className="text-xs font-mono bg-white p-2 rounded border">
                  srt://127.0.0.1:{group.ports.srt_port}?streamid=#!::r={streamPath},m=request
                </div>
              ))}
              {group.available_streams.length > 2 && (
                <div className="text-xs text-green-700">
                  ... and {group.available_streams.length - 2} more streams
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default GroupCard;
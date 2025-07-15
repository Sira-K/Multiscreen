// frontend/src/components/ui/GroupCard.tsx - Compact Design for Multiple Groups

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Play, Square, Monitor, Users, CheckCircle, AlertCircle, Container, Wifi, ChevronDown, ChevronUp, Settings } from "lucide-react";
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
  const [isExpanded, setIsExpanded] = useState(false);
  
  console.log(`🔍 GroupCard (Compact) - Group "${group.name || 'Unknown'}":`, {
    docker_running: group.docker_running,
    docker_status: group.docker_status,
    total_clients: clients.length,
    active_clients: clients.filter(c => c.is_active).length,
    ports: group.ports,
    container_id: group.container_id,
    id: group.id,
    full_group: group
  });

  // Safety check - if essential fields are missing, show error state
  if (!group.id || !group.name) {
    return (
      <Card className="bg-red-50 border border-red-200">
        <CardContent className="p-3">
          <div className="flex items-center gap-2 text-red-800">
            <AlertCircle className="h-4 w-4" />
            <span className="font-medium text-sm">Invalid Group Data</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Determine if streaming can be started (Docker must be running)
  const canStartStreaming = group.docker_running && !operationInProgress;
  const canStopStreaming = group.docker_running && operationInProgress !== group.id;
  
  // Status indicators
  const getDockerStatusBadge = () => {
    if (group.docker_running) {
      return <Badge variant="default" className="bg-green-100 text-green-800 text-xs">Running</Badge>;
    } else {
      return <Badge variant="destructive" className="text-xs">Stopped</Badge>;
    }
  };

  const getStreamingStatusBadge = () => {
    if (group.streaming_active) {
      return <Badge variant="default" className="bg-blue-100 text-blue-800 text-xs">Streaming</Badge>;
    } else if (group.docker_running) {
      return <Badge variant="outline" className="text-xs">Ready</Badge>;
    } else {
      return <Badge variant="secondary" className="text-xs">Offline</Badge>;
    }
  };

  return (
    <Card className="bg-white border border-gray-200">
      {/* Compact Header */}
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <Container className="h-4 w-4 text-blue-600 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <CardTitle className="text-lg text-gray-800 truncate">{group.name}</CardTitle>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-gray-500">
                  {group.screen_count} screens • {group.orientation}
                </span>
                <span className="text-xs text-gray-400">•</span>
                <span className="text-xs text-gray-500">
                  Port {group.ports?.srt_port || 'N/A'}
                </span>
              </div>
            </div>
          </div>
          
          {/* Status and Actions */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {getDockerStatusBadge()}
            {getStreamingStatusBadge()}
            
            {/* Main Action Button */}
            {group.streaming_active ? (
              <Button
                onClick={() => onStop(group.id, group.name)}
                disabled={!canStopStreaming}
                variant="destructive"
                size="sm"
              >
                <Square className="h-3 w-3 mr-1" />
                {operationInProgress === group.id ? 'Stopping...' : 'Stop'}
              </Button>
            ) : (
              <Button
                onClick={() => onStart(group.id, group.name)}
                disabled={!canStartStreaming}
                size="sm"
              >
                <Play className="h-3 w-3 mr-1" />
                {operationInProgress === group.id ? 'Starting...' : 'Start'}
              </Button>
            )}
            
            {/* Expand/Collapse Button */}
            <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="sm" className="p-1">
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </Button>
              </CollapsibleTrigger>
            </Collapsible>
          </div>
        </div>

        {/* Quick Stats Bar */}
        <div className="flex items-center gap-4 mt-2 text-xs text-gray-600">
          <div className="flex items-center gap-1">
            <Users className="h-3 w-3" />
            <span>{clients.filter(c => c.is_active).length}/{clients.length} clients</span>
          </div>
          {group.streaming_active && (
            <div className="flex items-center gap-1">
              <CheckCircle className="h-3 w-3 text-green-600" />
              <span className="text-green-600">Streaming active</span>
            </div>
          )}
          {!group.docker_running && (
            <div className="flex items-center gap-1">
              <AlertCircle className="h-3 w-3 text-red-600" />
              <span className="text-red-600">Docker offline</span>
            </div>
          )}
        </div>
      </CardHeader>

      {/* Expandable Content */}
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CollapsibleContent>
          <CardContent className="pt-0 space-y-4">
            {/* Video Selection */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">Video Source</label>
              <Select 
                value={selectedVideo || 'test_pattern'} 
                onValueChange={(value) => onVideoSelect(group.id, value === 'test_pattern' ? '' : value)}
                disabled={operationInProgress === group.id}
              >
                <SelectTrigger className="bg-white border-gray-300 h-8 text-sm">
                  <SelectValue placeholder="Select video file or use test pattern" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="test_pattern">Test Pattern (Default)</SelectItem>
                  {videos.map((video) => (
                    <SelectItem key={video.name} value={video.path}>
                      {video.name} ({video.size_mb.toFixed(1)} MB)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Docker Details */}
            <div className="p-2 bg-blue-50 rounded text-xs">
              <div className="font-medium text-blue-800 mb-1">Container Info</div>
              <div className="grid grid-cols-2 gap-1 text-blue-700">
                <span>ID: {group.container_id ? group.container_id.substring(0, 8) : 'N/A'}</span>
                <span>Status: {group.docker_status || 'unknown'}</span>
              </div>
            </div>

            {/* Assigned Clients (Compact) */}
            {clients.length > 0 && (
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Assigned Clients ({clients.length})
                </label>
                <div className="space-y-1 max-h-24 overflow-y-auto">
                  {clients.map((client) => (
                    <div key={client.client_id} className="flex items-center justify-between p-1.5 bg-gray-50 rounded text-xs">
                      <div className="flex items-center gap-1.5 min-w-0 flex-1">
                        <Wifi className={`h-3 w-3 flex-shrink-0 ${client.is_active ? 'text-green-500' : 'text-gray-400'}`} />
                        <span className="font-medium truncate">
                          {client.display_name || client.hostname}
                        </span>
                        <span className="text-gray-500">({client.ip_address})</span>
                      </div>
                      <Badge variant={client.is_active ? "default" : "secondary"} className="text-xs py-0 px-1">
                        {client.is_active ? "Online" : "Offline"}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Quick Assign Unassigned Clients */}
            {unassignedClients.length > 0 && (
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Quick Assign ({unassignedClients.length} available)
                </label>
                <div className="grid grid-cols-1 gap-1 max-h-20 overflow-y-auto">
                  {unassignedClients.slice(0, 2).map((client) => (
                    <div key={client.client_id} className="flex items-center justify-between p-1.5 bg-yellow-50 rounded text-xs">
                      <div className="flex items-center gap-1.5 min-w-0 flex-1">
                        <Wifi className={`h-3 w-3 flex-shrink-0 ${client.is_active ? 'text-green-500' : 'text-gray-400'}`} />
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

            {/* Error Messages */}
            {!group.docker_running && (
              <div className="p-2 bg-red-50 rounded text-xs">
                <div className="flex items-center gap-1 text-red-800 font-medium">
                  <AlertCircle className="h-3 w-3" />
                  <span>Docker Required</span>
                </div>
                <p className="text-red-700 mt-1">
                  Container must be running to start streaming.
                </p>
              </div>
            )}

            {/* Advanced Actions */}
            <div className="flex gap-2 pt-2 border-t">
              <Button
                onClick={() => onDelete(group.id, group.name)}
                disabled={operationInProgress === group.id}
                variant="outline"
                size="sm"
                className="text-red-600 hover:text-red-700 hover:bg-red-50 text-xs"
              >
                Delete Group
              </Button>
              
              {group.streaming_active && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs"
                  onClick={() => setIsExpanded(false)}
                >
                  <Settings className="h-3 w-3 mr-1" />
                  Stream URLs
                </Button>
              )}
            </div>

            {/* Stream URLs (when active) */}
            {group.streaming_active && group.available_streams && group.available_streams.length > 0 && (
              <div className="p-2 bg-green-50 rounded text-xs">
                <div className="font-medium text-green-800 mb-1">Active Streams</div>
                <div className="space-y-1 max-h-16 overflow-y-auto">
                  {group.available_streams.slice(0, 1).map((streamPath, index) => (
                    <div key={index} className="font-mono bg-white p-1 rounded border text-xs break-all">
                      srt://127.0.0.1:{group.ports?.srt_port || 10080}?streamid=#!::r={streamPath},m=request
                    </div>
                  ))}
                  {group.available_streams.length > 1 && (
                    <div className="text-green-700">
                      +{group.available_streams.length - 1} more streams available
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
};

export default GroupCard;
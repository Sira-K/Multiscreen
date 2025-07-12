import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import GroupCard from '@/components/ui/GroupCard';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, X, Play, Square, Users, Monitor, AlertCircle, CheckCircle, RefreshCw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { groupApi, videoApi, clientApi } from '@/lib/api';

interface Group {
  id: string;
  name: string;
  description: string;
  screen_count: number;
  orientation: string;
  status: 'active' | 'inactive' | 'starting' | 'stopping';
  docker_container_id?: string;
  ffmpeg_process_id?: number;
  available_streams: string[];
  current_video?: string;
  active_clients: number;
  total_clients: number;
  srt_port: number;
  created_at_formatted: string;
}

interface Video {
  name: string;
  path: string;
  size_mb: number;
}

interface Client {
  client_id: string;
  display_name?: string;
  hostname?: string;
  ip: string;
  status: 'active' | 'inactive';
  stream_id?: string | null;
  group_id?: string | null;
  group_name?: string | null;
}

const StreamsTab = () => {
  console.log('🚀 StreamsTab component rendered');
  
  const { toast } = useToast();
  
  // State management
  const [groups, setGroups] = useState<Group[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [operationInProgress, setOperationInProgress] = useState<string | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedVideos, setSelectedVideos] = useState<Record<string, string>>({});
  
  // Form state for creating new groups
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupDescription, setNewGroupDescription] = useState('');
  const [newGroupScreenCount, setNewGroupScreenCount] = useState(2);
  const [newGroupOrientation, setNewGroupOrientation] = useState('horizontal');

  // Enhanced fetchGroups function with detailed logging
  const fetchGroups = useCallback(async () => {
    try {
      console.log('🔄 Fetching groups...');
      const response = await groupApi.getGroups();
      console.log('📊 Groups response:', response);
      
      if (response && response.groups) {
        setGroups(response.groups);
        console.log(`✅ Updated ${response.groups.length} groups in state`);
        
        // Log status of each group for debugging
        response.groups.forEach((group: Group) => {
          console.log(`📋 Group "${group.name}": status=${group.status}, ffmpeg_pid=${group.ffmpeg_process_id}, docker=${group.docker_container_id ? 'Yes' : 'No'}`);
        });
      }
    } catch (error) {
      console.error('❌ Error fetching groups:', error);
      toast({
        title: "Loading Error",
        description: "Failed to load groups. Check console for details.",
        variant: "destructive"
      });
    }
  }, [toast]);

  const fetchVideos = useCallback(async () => {
    try {
      const response = await videoApi.getVideos();
      if (response && response.videos) {
        setVideos(response.videos);
        console.log(`📹 Loaded ${response.videos.length} videos`);
      }
    } catch (error) {
      console.error('❌ Error fetching videos:', error);
    }
  }, []);

  const fetchClients = useCallback(async () => {
    try {
      const response = await clientApi.getClients();
      if (response && response.clients) {
        // Map the client data to match your interface
        const mappedClients = (response.clients || []).map(client => ({
          ...client,
          client_id: client.id || client.client_id, // Map id to client_id
        }));
        setClients(mappedClients);
        console.log(`👥 Loaded ${mappedClients.length} clients`);
      }
    } catch (error) {
      console.error('❌ Error fetching clients:', error);
    }
  }, []);

  // State synchronization function
  const syncSystemState = useCallback(async () => {
    try {
      console.log('🔄 Syncing system state...');
      
      // Get current groups and their status from backend
      const groupsResponse = await groupApi.getGroups();
      const serverGroups = groupsResponse.groups || [];
      
      // For each group, check if processes are actually running
      const syncedGroups = await Promise.all(
        serverGroups.map(async (group) => {
          try {
            // Check if FFmpeg process is still running
            const statusResponse = await fetch(`/api/groups/${group.id}/status`);
            const statusData = await statusResponse.json();
            
            // Update group status based on actual system state
            return {
              ...group,
              status: statusData.is_running ? 'active' : 'inactive',
              ffmpeg_process_id: statusData.ffmpeg_process_id || null,
              docker_container_id: statusData.docker_container_id || null
            };
          } catch (error) {
            console.warn(`Failed to check status for group ${group.id}:`, error);
            // If we can't check status, assume inactive for safety
            return { ...group, status: 'inactive' };
          }
        })
      );
      
      setGroups(syncedGroups);
      console.log('✅ System state synchronized');
      
    } catch (error) {
      console.error('❌ Failed to sync system state:', error);
      // Fallback to basic group loading
      try {
        const groupsResponse = await groupApi.getGroups();
        setGroups(groupsResponse.groups || []);
      } catch (fallbackError) {
        console.error('❌ Fallback group loading also failed:', fallbackError);
      }
    }
  }, []);

  // Load initial data with state sync
  const loadInitialData = useCallback(async () => {
    console.log('🔄 Starting loadInitialData...');
    try {
      setLoading(true);
      
      console.log('📡 Making API calls to load groups, videos, and clients...');
      
      // Load all data
      await Promise.all([
        fetchGroups(),
        fetchVideos(),
        fetchClients()
      ]);
      
      console.log('📊 Initial data loaded successfully');
      
    } catch (error) {
      console.error('❌ Error loading initial data:', error);
      toast({
        title: "Loading Error",
        description: "Failed to load data. Check console for details.",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  }, [fetchGroups, fetchVideos, fetchClients, toast]);

  // Manual refresh function for users
  const refreshSystemState = async () => {
    setOperationInProgress('refresh');
    try {
      await syncSystemState();
      toast({
        title: "State Refreshed",
        description: "System state has been synchronized with server"
      });
    } catch (error) {
      toast({
        title: "Refresh Failed", 
        description: "Failed to sync system state",
        variant: "destructive"
      });
    } finally {
      setOperationInProgress(null);
    }
  };

  // Load initial data on mount
  useEffect(() => {
    console.log('🔥 useEffect triggered - calling loadInitialData');
    loadInitialData();
  }, [loadInitialData]);

  // Periodic state checking (every 30 seconds)
  useEffect(() => {
    const interval = setInterval(async () => {
      // Only sync if no operations are in progress
      if (!operationInProgress) {
        console.log('⏰ Periodic groups refresh...');
        await fetchGroups();
      }
    }, 30000); // Check every 30 seconds

    return () => clearInterval(interval);
  }, [operationInProgress, fetchGroups]);

  // Page visibility API - sync when user returns to tab
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden && !operationInProgress) {
        console.log('👁️ Page became visible, refreshing groups...');
        fetchGroups();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [operationInProgress, fetchGroups]);

  const createGroup = async () => {
    if (!newGroupName.trim()) {
      toast({
        title: "Validation Error",
        description: "Group name is required",
        variant: "destructive"
      });
      return;
    }

    try {
      setOperationInProgress('create');
      
      console.log('🏗️ Creating new group:', {
        name: newGroupName,
        description: newGroupDescription,
        screen_count: newGroupScreenCount,
        orientation: newGroupOrientation
      });
      
      const response = await groupApi.createGroup({
        name: newGroupName.trim(),
        description: newGroupDescription.trim(),
        screen_count: newGroupScreenCount,
        orientation: newGroupOrientation
      });
      
      toast({
        title: "Group Created",
        description: `Successfully created "${newGroupName}"`
      });

      // Reset form
      setNewGroupName('');
      setNewGroupDescription('');
      setNewGroupScreenCount(2);
      setNewGroupOrientation('horizontal');
      setShowCreateForm(false);

      // Reload data to show new group
      await fetchGroups();
      
    } catch (error: any) {
      console.error('Error creating group:', error);
      toast({
        title: "Creation Failed",
        description: error?.message || "Failed to create group",
        variant: "destructive"
      });
    } finally {
      setOperationInProgress(null);
    }
  };

  // Legacy handlers for GroupCard compatibility (the real work is done in GroupCard now)
  const handleStart = (groupId: string, groupName: string) => {
    console.log(`🚀 Legacy start callback for group "${groupName}"`);
    // The actual API call and refresh is now handled in GroupCard
  };

  const handleStop = (groupId: string, groupName: string) => {
    console.log(`🛑 Legacy stop callback for group "${groupName}"`);
    // The actual API call and refresh is now handled in GroupCard
  };

  const handleDelete = (groupId: string, groupName: string) => {
    console.log(`🗑️ Legacy delete callback for group "${groupName}"`);
    // The actual API call and refresh is now handled in GroupCard
  };

  const assignClientToStream = async (clientId: string, streamId: string, groupId: string) => {
    try {
      setOperationInProgress(`assign-${clientId}`);
      
      console.log('🔄 Assigning client to group first, then stream:', { clientId, streamId, groupId });
      
      if (streamId) {
        // Step 1: Assign client to group first
        await clientApi.assignToGroup(clientId, groupId);
        console.log('✅ Client assigned to group');
        
        // Step 2: Then assign the stream
        await clientApi.assignStream(clientId, streamId);
        console.log('✅ Client assigned to stream');
      } else {
        // Unassign client
        await clientApi.assignStream(clientId, '');
        await clientApi.assignToGroup(clientId, '');
        console.log('✅ Client unassigned');
      }
      
      // Refresh clients to show updated assignments
      await fetchClients();
      
      toast({
        title: "Client Assignment Updated",
        description: streamId ? `Successfully assigned client to stream` : `Client unassigned from stream`
      });
      
    } catch (error: any) {
      console.error('Error assigning client:', error);
      toast({
        title: "Assignment Failed",
        description: error?.message || "Failed to assign client to stream",
        variant: "destructive"
      });
    } finally {
      setOperationInProgress(null);
    }
  };

  const handleVideoSelect = (groupId: string, videoName: string) => {
    setSelectedVideos(prev => ({
      ...prev,
      [groupId]: videoName
    }));
    console.log(`🎥 Video selected for group ${groupId}: ${videoName}`);
  };

  console.log('🎨 StreamsTab rendering, loading:', loading, 'groups:', groups.length);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading groups and videos...</p>
          <p className="text-sm text-gray-400 mt-2">Syncing system state...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header and Create Button */}
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-2">Stream Management</h2>
          <p className="text-gray-600">Manage streaming groups and control video streams</p>
        </div>
        
        <div className="flex gap-3">
          {/* Refresh State Button */}
          <Button 
            onClick={refreshSystemState}
            disabled={operationInProgress === 'refresh'}
            variant="outline"
            size="sm"
          >
            {operationInProgress === 'refresh' ? (
              <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin mr-2" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            Refresh State
          </Button>

          {/* Create Group Button */}
          <Dialog open={showCreateForm} onOpenChange={setShowCreateForm}>
            <DialogTrigger asChild>
              <Button
                className="bg-blue-600 hover:bg-blue-700 text-white"
                disabled={operationInProgress === 'create'}
              >
                <Plus className="w-4 h-4 mr-2" />
                Create Group
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>Create New Group</DialogTitle>
                <DialogDescription>
                  Create a new streaming group with custom configuration.
                </DialogDescription>
              </DialogHeader>
              
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="name" className="text-right">Name</Label>
                  <Input
                    id="name"
                    value={newGroupName}
                    onChange={(e) => setNewGroupName(e.target.value)}
                    className="col-span-3"
                    placeholder="Enter group name"
                  />
                </div>
                
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="description" className="text-right">Description</Label>
                  <Input
                    id="description"
                    value={newGroupDescription}
                    onChange={(e) => setNewGroupDescription(e.target.value)}
                    className="col-span-3"
                    placeholder="Optional description"
                  />
                </div>
                
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="screens" className="text-right">Screens</Label>
                  <Select value={newGroupScreenCount.toString()} onValueChange={(value) => setNewGroupScreenCount(parseInt(value))}>
                    <SelectTrigger className="col-span-3">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1 Screen</SelectItem>
                      <SelectItem value="2">2 Screens</SelectItem>
                      <SelectItem value="3">3 Screens</SelectItem>
                      <SelectItem value="4">4 Screens</SelectItem>
                      <SelectItem value="6">6 Screens</SelectItem>
                      <SelectItem value="8">8 Screens</SelectItem>
                      <SelectItem value="9">9 Screens</SelectItem>
                      <SelectItem value="12">12 Screens</SelectItem>
                      <SelectItem value="16">16 Screens</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="orientation" className="text-right">Layout</Label>
                  <Select value={newGroupOrientation} onValueChange={setNewGroupOrientation}>
                    <SelectTrigger className="col-span-3">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="horizontal">Horizontal</SelectItem>
                      <SelectItem value="vertical">Vertical</SelectItem>
                      <SelectItem value="grid">Grid</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowCreateForm(false)}>
                  Cancel
                </Button>
                <Button 
                  onClick={createGroup}
                  disabled={operationInProgress === 'create' || !newGroupName.trim()}
                >
                  {operationInProgress === 'create' ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  ) : null}
                  Create Group
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Groups Grid */}
      {groups.length === 0 ? (
        <Card className="text-center p-8">
          <div className="flex flex-col items-center space-y-4">
            <Monitor className="w-12 h-12 text-gray-400" />
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Groups Found</h3>
              <p className="text-gray-600 mb-4">Create your first streaming group to get started</p>
              <Button
                onClick={() => setShowCreateForm(true)}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <Plus className="w-4 h-4 mr-2" />
                Create First Group
              </Button>
            </div>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {groups.map((group) => (
            <GroupCard
              key={group.id}
              group={group}
              videos={videos}
              clients={clients}
              selectedVideo={selectedVideos[group.id]}
              operationInProgress={operationInProgress}
              onVideoSelect={handleVideoSelect}
              onStart={handleStart}
              onStop={handleStop}
              onDelete={handleDelete}
              onAssignClient={assignClientToStream}
              // Enhanced props for proper operations
              onRefreshGroups={fetchGroups}
              setOperationInProgress={setOperationInProgress}
            />
          ))}
        </div>
      )}

      {/* Debug Info - Remove in production */}
      <div className="mt-8 p-4 bg-gray-100 rounded text-xs">
        <h3 className="font-bold mb-2">Debug Info:</h3>
        <p>Groups: {groups.length}</p>
        <p>Videos: {videos.length}</p>
        <p>Clients: {clients.length}</p>
        <p>Operation in progress: {operationInProgress || 'None'}</p>
        <p>Selected videos: {JSON.stringify(selectedVideos)}</p>
        <div className="mt-2">
          <p className="font-semibold">Group Status Summary:</p>
          {groups.map(group => (
            <p key={group.id} className="ml-2">
              {group.name}: {group.status} (Docker: {group.docker_container_id ? '✅' : '❌'}, FFmpeg: {group.ffmpeg_process_id ? '✅' : '❌'})
            </p>
          ))}
        </div>
      </div>
    </div>
  );
};

export default StreamsTab;
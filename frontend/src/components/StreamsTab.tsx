// frontend/src/components/StreamsTab.tsx - Fixed with proper stream status tracking

import { useState, useEffect } from "react";
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
import type { Group, Video, Client } from '@/types';

const StreamsTab = () => {
  const { toast } = useToast();
  
  // State management
  const [groups, setGroups] = useState<Group[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [operationInProgress, setOperationInProgress] = useState<string | null>(null);
  const [selectedVideos, setSelectedVideos] = useState<Record<string, string>>({});
  const [streamingStatus, setStreamingStatus] = useState<Record<string, boolean>>({});
  
  // Form state for creating new groups
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupDescription, setNewGroupDescription] = useState('');
  const [newGroupScreenCount, setNewGroupScreenCount] = useState(2);
  const [newGroupOrientation, setNewGroupOrientation] = useState<'horizontal' | 'vertical' | 'grid'>('horizontal');

  // Load initial data
  useEffect(() => {
    debugApiConnection();
    loadInitialData();
  }, []);

  // Function to fetch streaming status from backend
  const fetchStreamingStatus = async () => {
    try {
      const response = await fetch('/api/get_group_srt_status', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        const status: Record<string, boolean> = {};
        
        // Convert backend streaming status to our format
        if (data.srt_status) {
          Object.entries(data.srt_status).forEach(([groupId, statusInfo]: [string, any]) => {
            status[groupId] = statusInfo.streaming || false;
          });
        }
        
        setStreamingStatus(status);
        console.log('Updated streaming status:', status);
      } else {
        console.warn('Failed to fetch streaming status:', response.statusText);
      }
    } catch (error) {
      console.error('Error fetching streaming status:', error);
    }
  };

  const loadInitialData = async () => {
    try {
      setLoading(true);
      
      // Load data in parallel
      const [groupsResponse, videosResponse, clientsResponse] = await Promise.all([
        groupApi.getGroups(),
        videoApi.getVideos(),
        clientApi.getClients()
      ]);
      
      // Set groups from Docker discovery
      setGroups(groupsResponse.groups || []);
      
      // Set videos
      setVideos(videosResponse.videos || []);
      
      // Set clients from app state
      setClients(clientsResponse.clients || []);
      
      // Fetch actual streaming status from backend
      await fetchStreamingStatus();
      
      console.log('Loaded initial data:', {
        groups: groupsResponse.groups?.length || 0,
        videos: videosResponse.videos?.length || 0,
        clients: clientsResponse.clients?.length || 0
      });
      
    } catch (error: any) {
      console.error('Error loading initial data:', error);
      toast({
        title: "Load Error",
        description: error?.message || "Failed to load data from the server",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const refreshData = async () => {
    setRefreshing(true);
    await loadInitialData();
    setRefreshing(false);
  };

  const debugApiConnection = async () => {
    try {
      const response = await fetch('/api/status');
      console.log('API connection test:', response.ok ? 'Success' : 'Failed');
    } catch (error) {
      console.error('API connection test failed:', error);
    }
  };

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
      setOperationInProgress('creating');
      
      const response = await groupApi.createGroup({
        name: newGroupName,
        description: newGroupDescription,
        screen_count: newGroupScreenCount,
        orientation: newGroupOrientation
      });

      toast({
        title: "Group Created",
        description: `Successfully created group "${newGroupName}"`
      });

      // Reset form
      setNewGroupName('');
      setNewGroupDescription('');
      setNewGroupScreenCount(2);
      setNewGroupOrientation('horizontal');
      setShowCreateForm(false);

      // Reload data
      await loadInitialData();

    } catch (error: any) {
      console.error('Error creating group:', error);
      toast({
        title: "Creation Failed",
        description: error?.message || `Failed to create group "${newGroupName}"`,
        variant: "destructive"
      });
    } finally {
      setOperationInProgress(null);
    }
  };

  const assignClientToGroup = async (clientId: string, groupId: string) => {
    try {
      await clientApi.assignClientToGroup(clientId, groupId);
      
      toast({
        title: "Client Assigned",
        description: "Successfully assigned client to group"
      });

      // Reload data to get updated assignments
      await loadInitialData();
      
    } catch (error: any) {
      console.error('Error assigning client:', error);
      toast({
        title: "Assignment Failed",
        description: error?.message || "Failed to assign client to group",
        variant: "destructive"
      });
    }
  };

  const startGroup = async (groupId: string, groupName: string) => {
    try {
      setOperationInProgress(groupId);
      
      const selectedVideo = selectedVideos[groupId];
      if (!selectedVideo) {
        toast({
          title: "No Video Selected",
          description: "Please select a video before starting the stream",
          variant: "destructive"
        });
        return;
      }

      const response = await groupApi.startGroup(groupId, selectedVideo);
      
      // Update streaming status immediately
      setStreamingStatus(prev => ({
        ...prev,
        [groupId]: true
      }));
      
      toast({
        title: "Streaming Started",
        description: `Successfully started streaming for "${groupName}"`
      });

      // Reload data to get updated status and verify streaming state
      await loadInitialData();
      
    } catch (error: any) {
      console.error('Error starting group:', error);
      toast({
        title: "Start Failed",
        description: error?.message || `Failed to start group "${groupName}"`,
        variant: "destructive"
      });
    } finally {
      setOperationInProgress(null);
    }
  };

  const stopGroup = async (groupId: string, groupName: string) => {
    try {
      setOperationInProgress(groupId);
      
      const response = await groupApi.stopGroup(groupId);
      
      // Update streaming status immediately
      setStreamingStatus(prev => ({
        ...prev,
        [groupId]: false
      }));
      
      toast({
        title: "Streaming Stopped",
        description: `Successfully stopped streaming for "${groupName}"`
      });

      // Reload data to get updated status and verify streaming state
      await loadInitialData();
      
    } catch (error: any) {
      console.error('Error stopping group:', error);
      toast({
        title: "Stop Failed",
        description: error?.message || `Failed to stop group "${groupName}"`,
        variant: "destructive"
      });
    } finally {
      setOperationInProgress(null);
    }
  };

  const deleteGroup = async (groupId: string, groupName: string) => {
    if (!confirm(`Are you sure you want to delete "${groupName}"? This will stop streaming and remove the Docker container.`)) {
      return;
    }

    try {
      setOperationInProgress(groupId);
      
      await groupApi.deleteGroup(groupId);
      
      toast({
        title: "Group Deleted",
        description: `Successfully deleted group "${groupName}"`
      });

      // Remove from local state
      setGroups(prev => prev.filter(g => g.id !== groupId));
      setStreamingStatus(prev => {
        const updated = { ...prev };
        delete updated[groupId];
        return updated;
      });
      
    } catch (error: any) {
      console.error('Error deleting group:', error);
      toast({
        title: "Delete Failed",
        description: error?.message || `Failed to delete group "${groupName}"`,
        variant: "destructive"
      });
    } finally {
      setOperationInProgress(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading multi-screen data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Multi-Screen Groups</h2>
          <p className="text-gray-600 mt-1">
            Manage streaming groups discovered from Docker containers
          </p>
        </div>
        
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={refreshData}
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </Button>
          
          <Dialog open={showCreateForm} onOpenChange={setShowCreateForm}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Group
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Create New Multi-Screen Group</DialogTitle>
                <DialogDescription>
                  Create a Docker container for multi-screen video streaming
                </DialogDescription>
              </DialogHeader>
              
              <div className="space-y-4">
                <div>
                  <Label htmlFor="name">Group Name</Label>
                  <Input
                    id="name"
                    value={newGroupName}
                    onChange={(e) => setNewGroupName(e.target.value)}
                    placeholder="Enter group name..."
                  />
                </div>
                
                <div>
                  <Label htmlFor="description">Description (Optional)</Label>
                  <Input
                    id="description"
                    value={newGroupDescription}
                    onChange={(e) => setNewGroupDescription(e.target.value)}
                    placeholder="Enter description..."
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="screen_count">Screen Count</Label>
                    <Select
                      value={newGroupScreenCount.toString()}
                      onValueChange={(value) => setNewGroupScreenCount(parseInt(value))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">1 Screen</SelectItem>
                        <SelectItem value="2">2 Screens</SelectItem>
                        <SelectItem value="3">3 Screens</SelectItem>
                        <SelectItem value="4">4 Screens</SelectItem>
                        <SelectItem value="6">6 Screens</SelectItem>
                        <SelectItem value="8">8 Screens</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label htmlFor="orientation">Orientation</Label>
                    <Select
                      value={newGroupOrientation}
                      onValueChange={(value: 'horizontal' | 'vertical' | 'grid') => setNewGroupOrientation(value)}
                    >
                      <SelectTrigger>
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
              </div>
              
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setShowCreateForm(false)}
                  disabled={operationInProgress === 'creating'}
                >
                  Cancel
                </Button>
                <Button
                  onClick={createGroup}
                  disabled={operationInProgress === 'creating' || !newGroupName.trim()}
                >
                  {operationInProgress === 'creating' ? 'Creating...' : 'Create Group'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Status Summary */}
      <Card className="bg-white border border-gray-200">
        <CardHeader>
          <CardTitle className="text-gray-800">System Status</CardTitle>
          <CardDescription className="text-gray-600">
            Overview of groups and clients in hybrid architecture
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{groups.length}</div>
              <div className="text-sm text-gray-600">Total Groups</div>
              <div className="text-xs text-gray-500">Docker Containers</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {groups.filter(g => g.docker_running).length}
              </div>
              <div className="text-sm text-gray-600">Active Groups</div>
              <div className="text-xs text-gray-500">Docker Running</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">{clients.length}</div>
              <div className="text-sm text-gray-600">Total Clients</div>
              <div className="text-xs text-gray-500">Registered</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {Object.values(streamingStatus).filter(status => status).length}
              </div>
              <div className="text-sm text-gray-600">Active Streams</div>
              <div className="text-xs text-gray-500">FFmpeg Running</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Groups List */}
      {groups.length === 0 ? (
        <Card className="bg-white border border-gray-200">
          <CardContent className="text-center py-8">
            <Monitor className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-800 mb-2">No Groups Found</h3>
            <p className="text-gray-600 mb-4">
              No Docker containers with multi-screen labels were discovered.
            </p>
            <Button onClick={() => setShowCreateForm(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Your First Group
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6">
          {groups.map((group) => (
            <GroupCard
              key={group.id}
              group={group}
              videos={videos}
              clients={clients.filter(c => c.group_id === group.id)}
              unassignedClients={clients.filter(c => !c.group_id)}
              selectedVideo={selectedVideos[group.id]}
              isStreaming={streamingStatus[group.id] || false}
              operationInProgress={operationInProgress}
              onVideoSelect={(groupId, videoName) => 
                setSelectedVideos(prev => ({ ...prev, [groupId]: videoName }))
              }
              onStart={startGroup}
              onStop={stopGroup}
              onDelete={deleteGroup}
              onAssignClient={assignClientToGroup}
            />
          ))}
        </div>
      )}

      {/* Architecture Info */}
      <Card className="bg-blue-50 border border-blue-200">
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 text-blue-800">
            <CheckCircle className="h-4 w-4" />
            <span className="font-medium">Hybrid Architecture Active</span>
          </div>
          <p className="text-sm text-blue-700 mt-1">
            Groups are managed through Docker discovery. Clients are tracked in real-time app state.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default StreamsTab;
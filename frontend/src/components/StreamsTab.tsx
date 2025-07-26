// frontend/src/components/StreamsTab.tsx - Fixed with proper margins and container

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import GroupCard from '@/components/ui/GroupCard';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, X, Play, Square, Users, Monitor, AlertCircle, CheckCircle, RefreshCw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { groupApi, videoApi, clientApi } from '@/API/api';
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
  const [selectedVideos, setSelectedVideos] = useState<{ [groupId: string]: string }>({});
  const [streamingStatus, setStreamingStatus] = useState<{ [groupId: string]: boolean }>({});

  // Form state for creating new groups
  const [newGroupForm, setNewGroupForm] = useState({
    name: '',
    description: '',
    screen_count: 2,
    orientation: 'horizontal' as 'horizontal' | 'vertical' | 'grid'
  });

  // Load initial data
  const loadInitialData = async () => {
    try {
      const [groupsData, videosData, clientsData] = await Promise.all([
        groupApi.getGroups(),
        videoApi.getVideos(),
        clientApi.getClients()
      ]);

      setGroups(groupsData.groups);
      setVideos(videosData.videos);
      setClients(clientsData.clients);

      // Load streaming statuses for all groups
      await loadStreamingStatuses(groupsData.groups);

    } catch (error: any) {
      console.error('Error loading data:', error);
      toast({
        title: "Loading Failed",
        description: error?.message || "Failed to load application data",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  // Load streaming statuses for all groups
  const loadStreamingStatuses = async (groupsList: Group[]) => {
    try {
      // Check if getAllStreamingStatuses API exists, otherwise check individually
      try {
        const statusData = await groupApi.getAllStreamingStatuses();
        setStreamingStatus(statusData.streaming_statuses || {});
      } catch {
        // Fallback: check each group individually
        const statuses: { [groupId: string]: boolean } = {};
        for (const group of groupsList) {
          try {
            const status = await groupApi.getStreamingStatus(group.id);
            statuses[group.id] = status.is_streaming || false;
          } catch {
            statuses[group.id] = false;
          }
        }
        setStreamingStatus(statuses);
      }
    } catch (error) {
      console.error('Error loading streaming statuses:', error);
      // Set all to false as fallback
      const fallbackStatuses: { [groupId: string]: boolean } = {};
      groupsList.forEach(group => {
        fallbackStatuses[group.id] = false;
      });
      setStreamingStatus(fallbackStatuses);
    }
  };

  // Handle streaming status change (called by GroupCard)
  const handleStreamingStatusChange = (groupId: string, isStreaming: boolean) => {
    setStreamingStatus(prev => ({
      ...prev,
      [groupId]: isStreaming
    }));
  };

  // Initial load
  useEffect(() => {
    loadInitialData();
  }, []);

  // Refresh data
  const refreshData = async () => {
    setRefreshing(true);
    await loadInitialData();
    setRefreshing(false);
  };

  // Create new group
  const createGroup = async () => {
    try {
      setOperationInProgress('create');
      
      if (!newGroupForm.name.trim()) {
        toast({
          title: "Validation Error",
          description: "Group name is required",
          variant: "destructive"
        });
        return;
      }

      const response = await groupApi.createGroup({
        name: newGroupForm.name.trim(),
        description: newGroupForm.description.trim(),
        screen_count: newGroupForm.screen_count,
        orientation: newGroupForm.orientation
      });

      toast({
        title: "Group Created",
        description: `Successfully created group "${newGroupForm.name}"`
      });

      // Reset form and close dialog
      setNewGroupForm({
        name: '',
        description: '',
        screen_count: 2,
        orientation: 'horizontal'
      });
      setShowCreateForm(false);

      // Reload data to show new group
      await loadInitialData();
      
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

  // Delete group
  const deleteGroup = async (groupId: string, groupName: string) => {
    try {
      setOperationInProgress(groupId);
      
      const response = await groupApi.deleteGroup(groupId);
      
      toast({
        title: "Group Deleted",
        description: `Successfully deleted group "${groupName}"`
      });

      // Remove from local state immediately
      setGroups(prev => prev.filter(g => g.id !== groupId));
      setStreamingStatus(prev => {
        const newStatus = { ...prev };
        delete newStatus[groupId];
        return newStatus;
      });
      
    } catch (error: any) {
      console.error('Error deleting group:', error);
      toast({
        title: "Deletion Failed",
        description: error?.message || `Failed to delete group "${groupName}"`,
        variant: "destructive"
      });
    } finally {
      setOperationInProgress(null);
    }
  };

  // Assign client to group
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

  // Stop group streaming (works for both single and multi-video)
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

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <RefreshCw className="h-8 w-8 animate-spin text-gray-400 mx-auto mb-2" />
            <p className="text-gray-600">Loading streaming groups...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Streaming Groups</h2>
          <p className="text-gray-600">Manage multi-screen video streaming groups and client assignments</p>
        </div>
        
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={refreshData}
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          
          <Dialog open={showCreateForm} onOpenChange={setShowCreateForm}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Group
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Streaming Group</DialogTitle>
                <DialogDescription>
                  Set up a new multi-screen streaming group with Docker container management.
                </DialogDescription>
              </DialogHeader>
              
              <div className="space-y-4">
                <div>
                  <Label htmlFor="group-name">Group Name</Label>
                  <Input
                    id="group-name"
                    placeholder="Enter group name"
                    value={newGroupForm.name}
                    onChange={(e) => setNewGroupForm(prev => ({ ...prev, name: e.target.value }))}
                  />
                </div>
                
                <div>
                  <Label htmlFor="group-description">Description (Optional)</Label>
                  <Input
                    id="group-description"
                    placeholder="Enter group description"
                    value={newGroupForm.description}
                    onChange={(e) => setNewGroupForm(prev => ({ ...prev, description: e.target.value }))}
                  />
                </div>
                
                <div>
                  <Label htmlFor="screen-count">Screen Count</Label>
                  <Select
                    value={newGroupForm.screen_count.toString()}
                    onValueChange={(value) => setNewGroupForm(prev => ({ ...prev, screen_count: parseInt(value) }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {[2, 3, 4, 6, 8, 9].map(count => (
                        <SelectItem key={count} value={count.toString()}>
                          {count} screens
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <Label htmlFor="orientation">Layout Orientation</Label>
                  <Select
                    value={newGroupForm.orientation}
                    onValueChange={(value: 'horizontal' | 'vertical' | 'grid') => 
                      setNewGroupForm(prev => ({ ...prev, orientation: value }))
                    }
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
              
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowCreateForm(false)}>
                  Cancel
                </Button>
                <Button 
                  onClick={createGroup}
                  disabled={operationInProgress === 'create' || !newGroupForm.name.trim()}
                >
                  {operationInProgress === 'create' ? 'Creating...' : 'Create Group'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="overflow-hidden">
          <CardContent className="p-0">
            <div className="flex items-center">
              <div className="flex-1 p-6">
                <div className="flex items-center">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-muted-foreground">Total Groups</p>
                    <p className="text-2xl font-bold">{groups.length}</p>
                  </div>
                  <div className="ml-4 rounded-full bg-blue-100 p-3">
                    <Monitor className="h-6 w-6 text-blue-600" />
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="overflow-hidden">
          <CardContent className="p-0">
            <div className="flex items-center">
              <div className="flex-1 p-6">
                <div className="flex items-center">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-muted-foreground">Active Streams</p>
                    <p className="text-2xl font-bold">
                      {Object.values(streamingStatus).filter(Boolean).length}
                    </p>
                  </div>
                  <div className="ml-4 rounded-full bg-green-100 p-3">
                    <Play className="h-6 w-6 text-green-600" />
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="overflow-hidden">
          <CardContent className="p-0">
            <div className="flex items-center">
              <div className="flex-1 p-6">
                <div className="flex items-center">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-muted-foreground">Connected Clients</p>
                    <p className="text-2xl font-bold">{clients.filter(c => c.status === 'active').length}</p>
                  </div>
                  <div className="ml-4 rounded-full bg-purple-100 p-3">
                    <Users className="h-6 w-6 text-purple-600" />
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Groups Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-800">Active Groups</h3>
        
        {groups.length === 0 ? (
          <Card className="bg-white border border-gray-200">
            <CardContent className="text-center py-12">
              <Monitor className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-800 mb-2">No Groups Found</h3>
              <p className="text-gray-600 mb-6">
                No Docker containers with multi-screen labels were discovered.
                Create your first group to get started with multi-screen streaming.
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
                isStreaming={streamingStatus[group.id] || false}
                operationInProgress={operationInProgress}
                onStop={stopGroup}
                onDelete={deleteGroup}
                onAssignClient={assignClientToGroup}
                onStreamingStatusChange={handleStreamingStatusChange}
                onRefresh={refreshData}
              />
            ))}
          </div>
        )}
      </div>

      {/* Architecture Info */}
      <Card className="bg-blue-50 border border-blue-200">
        <CardContent className="p-6">
          <div className="flex items-center gap-2 text-blue-800 mb-2">
            <CheckCircle className="h-4 w-4" />
            <span className="font-medium">Hybrid Architecture Active</span>
          </div>
          <p className="text-sm text-blue-700">
            Groups are managed through Docker discovery. Clients are tracked in real-time app state.
            Multi-video streaming supports different videos per screen with persistent assignments.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default StreamsTab;
// frontend/src/components/StreamsTab.tsx - Updated for Hybrid Architecture

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
  console.log('🚀 StreamsTab component rendered (Hybrid Architecture)');
  
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
  
  // Form state for creating new groups
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupDescription, setNewGroupDescription] = useState('');
  const [newGroupScreenCount, setNewGroupScreenCount] = useState(2);
  const [newGroupOrientation, setNewGroupOrientation] = useState<'horizontal' | 'vertical' | 'grid'>('horizontal');

  // Load initial data
  useEffect(() => {
    console.log('🔥 useEffect triggered - calling loadInitialData (Hybrid Architecture)');
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    console.log('🔄 Starting loadInitialData (Hybrid Architecture)...');
    try {
      setLoading(true);
      
      console.log('📡 Making API calls to load groups, videos, and clients...');
      
      // Load data in parallel
      const [groupsResponse, videosResponse, clientsResponse] = await Promise.all([
        groupApi.getGroups(),
        videoApi.getVideos(),
        clientApi.getClients()
      ]);
      
      console.log('✅ Groups response (Docker discovery):', groupsResponse);
      console.log('✅ Raw groups data:', groupsResponse.groups);
      console.log('✅ Videos response:', videosResponse);
      console.log('✅ Clients response (hybrid state):', clientsResponse);
      
      // Set groups from Docker discovery
      const discoveredGroups = groupsResponse.groups || [];
      setGroups(discoveredGroups);
      
      // Set videos
      setVideos(videosResponse.videos || []);
      
      // Set clients from app state
      const clientsList = clientsResponse.clients || [];
      setClients(clientsList);
      
      // Calculate client counts per group
      const groupsWithCounts = discoveredGroups.map(group => {
        const groupClients = clientsList.filter(client => client.group_id === group.id);
        const activeGroupClients = groupClients.filter(client => client.is_active);
        
        return {
          ...group,  // Keep ALL original group fields
          total_clients: groupClients.length,
          active_clients: activeGroupClients.length
        };
      });
      
      setGroups(groupsWithCounts);
      
      console.log('📊 Final state (Hybrid Architecture):', {
        groupsCount: groupsWithCounts.length,
        videosCount: videosResponse.videos?.length || 0,
        clientsCount: clientsList.length,
        architecture: 'hybrid_docker_discovery',
        finalGroups: groupsWithCounts
      });
      
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
  };

  const refreshData = async () => {
    console.log('🔄 Refreshing data (Hybrid Architecture)...');
    setRefreshing(true);
    try {
      await loadInitialData();
      toast({
        title: "Data Refreshed",
        description: "All data has been updated from Docker and app state",
      });
    } catch (error) {
      console.error('❌ Error refreshing data:', error);
      toast({
        title: "Refresh Failed",
        description: "Failed to refresh data",
        variant: "destructive"
      });
    } finally {
      setRefreshing(false);
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
      setOperationInProgress('create');
      
      console.log('🔨 Creating group with Docker container...');
      
      const groupData = {
        name: newGroupName.trim(),
        description: newGroupDescription.trim(),
        screen_count: newGroupScreenCount,
        orientation: newGroupOrientation
      };
      
      console.log('📦 Group data:', groupData);
      
      const response = await groupApi.createGroup(groupData);
      
      console.log('✅ Group created successfully:', response);
      
      toast({
        title: "Group Created",
        description: `Successfully created "${newGroupName}" with Docker container`
      });

      // Reset form
      setNewGroupName('');
      setNewGroupDescription('');
      setNewGroupScreenCount(2);
      setNewGroupOrientation('horizontal');
      setShowCreateForm(false);

      // Reload data to show the new group
      await loadInitialData();
      
    } catch (error: any) {
      console.error('❌ Error creating group:', error);
      toast({
        title: "Create Failed",
        description: error?.message || "Failed to create group",
        variant: "destructive"
      });
    } finally {
      setOperationInProgress(null);
    }
  };

  const startGroup = async (groupId: string, groupName: string) => {
    try {
      setOperationInProgress(groupId);
      
      console.log(`🚀 Starting group ${groupId} (requires Docker container running)`);
      
      const videoFile = selectedVideos[groupId];
      console.log(`📹 Video file for group ${groupId}:`, videoFile);
      
      const response = await groupApi.startGroup(groupId, videoFile);
      
      console.log('✅ Group started successfully:', response);
      
      toast({
        title: "Streaming Started",
        description: `Successfully started streaming for "${groupName}"`
      });

      // Reload data to get updated status
      await loadInitialData();
      
    } catch (error: any) {
      console.error('❌ Error starting group:', error);
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
      
      console.log(`🛑 Stopping group ${groupId}`);
      
      const response = await groupApi.stopGroup(groupId);
      
      console.log('✅ Group stopped successfully:', response);
      
      toast({
        title: "Streaming Stopped",
        description: `Successfully stopped streaming for "${groupName}"`
      });

      // Reload data to get updated status
      await loadInitialData();
      
    } catch (error: any) {
      console.error('❌ Error stopping group:', error);
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
    if (!confirm(`Are you sure you want to delete "${groupName}"? This will stop streaming and remove the Docker container. This action cannot be undone.`)) {
      return;
    }

    try {
      setOperationInProgress(groupId);
      
      console.log(`🗑️ Deleting group ${groupId} (will stop streams and remove Docker container)`);
      
      await groupApi.deleteGroup(groupId);
      
      toast({
        title: "Group Deleted",
        description: `Successfully deleted "${groupName}" and removed Docker container`
      });

      // Reload groups from Docker discovery
      await loadInitialData();
      
    } catch (error: any) {
      console.error('❌ Error deleting group:', error);
      toast({
        title: "Delete Failed",
        description: error?.message || `Failed to delete group "${groupName}"`,
        variant: "destructive"
      });
    } finally {
      setOperationInProgress(null);
    }
  };

  const assignClientToGroup = async (clientId: string, groupId: string) => {
    try {
      setOperationInProgress(`assign-${clientId}`);
      
      console.log('🔄 Assigning client to group (hybrid architecture):', { clientId, groupId });
      
      await clientApi.assignToGroup(clientId, groupId);
      
      console.log('✅ Client assigned to group');
      
      // Refresh data to show updated assignments
      await loadInitialData();
      
      const group = groups.find(g => g.id === groupId);
      const client = clients.find(c => c.client_id === clientId);
      
      toast({
        title: "Client Assigned",
        description: `Assigned ${client?.display_name || client?.hostname} to ${group?.name}`
      });
      
    } catch (error: any) {
      console.error('❌ Error assigning client:', error);
      toast({
        title: "Assignment Failed",
        description: error?.message || "Failed to assign client to group",
        variant: "destructive"
      });
    } finally {
      setOperationInProgress(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-500" />
          <p className="text-gray-600">Loading groups from Docker discovery...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with refresh button */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-semibold text-black mb-2">
            Stream Management 
            <Badge variant="outline" className="ml-2">Hybrid Architecture</Badge>
          </h2>
          <p className="text-gray-600">
            Manage groups (Docker containers) and streaming (FFmpeg processes)
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            onClick={refreshData} 
            variant="outline" 
            size="sm"
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Dialog open={showCreateForm} onOpenChange={setShowCreateForm}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="h-4 w-4 mr-2" />
                Create Group
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Group</DialogTitle>
                <DialogDescription>
                  This will create a new Docker container for SRT streaming
                </DialogDescription>
              </DialogHeader>
              
              <div className="space-y-4">
                <div>
                  <Label htmlFor="name">Group Name *</Label>
                  <Input
                    id="name"
                    value={newGroupName}
                    onChange={(e) => setNewGroupName(e.target.value)}
                    placeholder="Enter group name"
                  />
                </div>
                
                <div>
                  <Label htmlFor="description">Description</Label>
                  <Input
                    id="description"
                    value={newGroupDescription}
                    onChange={(e) => setNewGroupDescription(e.target.value)}
                    placeholder="Optional description"
                  />
                </div>
                
                <div>
                  <Label htmlFor="screen_count">Screen Count</Label>
                  <Input
                    id="screen_count"
                    type="number"
                    min="1"
                    max="16"
                    value={newGroupScreenCount}
                    onChange={(e) => setNewGroupScreenCount(parseInt(e.target.value) || 1)}
                  />
                </div>
                
                <div>
                  <Label htmlFor="orientation">Layout Orientation</Label>
                  <Select value={newGroupOrientation} onValueChange={(value: 'horizontal' | 'vertical' | 'grid') => setNewGroupOrientation(value)}>
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
                <Button 
                  variant="outline" 
                  onClick={() => setShowCreateForm(false)}
                  disabled={operationInProgress === 'create'}
                >
                  Cancel
                </Button>
                <Button 
                  onClick={createGroup}
                  disabled={operationInProgress === 'create' || !newGroupName.trim()}
                >
                  {operationInProgress === 'create' ? 'Creating...' : 'Create Group'}
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
                {clients.filter(c => c.is_active).length}
              </div>
              <div className="text-sm text-gray-600">Active Clients</div>
              <div className="text-xs text-gray-500">Connected</div>
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
          {groups.map((group) => {
            console.log(`🔍 About to render GroupCard for group:`, group);
            return (
              <GroupCard
                key={group.id}
                group={group}
                videos={videos}
                clients={clients.filter(c => c.group_id === group.id)}
                unassignedClients={clients.filter(c => !c.group_id)}
                selectedVideo={selectedVideos[group.id]}
                operationInProgress={operationInProgress}
                onVideoSelect={(groupId, videoName) => 
                  setSelectedVideos(prev => ({ ...prev, [groupId]: videoName }))
                }
                onStart={startGroup}
                onStop={stopGroup}
                onDelete={deleteGroup}
                onAssignClient={assignClientToGroup}
              />
            );
          })}
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
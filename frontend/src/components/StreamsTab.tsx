// frontend/src/components/StreamsTab.tsx - Fixed Complete Version

import { useState, useEffect } from "react";
import { Card, CardContent} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import GroupCard from '@/components/ui/GroupCard';
import CreateGroupDialog from '@/components/ui/CreateGroupDialog';
import { Plus, X, Play, Square, Users, Monitor, CheckCircle, RefreshCw} from "lucide-react";
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
    orientation: 'horizontal' as 'horizontal' | 'vertical' | 'grid',
    streaming_mode: 'multi_video' as 'multi_video' | 'single_video_split'
  });

  // Load initial data
  const loadInitialData = async () => {
    try {
      console.log(`🔄 LOADING INITIAL DATA...`);
      
      const [groupsData, videosData, clientsData] = await Promise.all([
        groupApi.getGroups(),
        videoApi.getVideos(),
        clientApi.getClients()
      ]);

      console.log(`📊 LOADED GROUPS:`, groupsData.groups.map(g => ({
        id: g.id,
        name: g.name,
        docker_running: g.docker_running,
        docker_status: g.docker_status,
        status: g.status
      })));

      setGroups(groupsData.groups);
      setVideos(videosData.videos);
      setClients(clientsData.clients);

      // Initialize all groups with false status first
      const initialStatuses: { [groupId: string]: boolean } = {};
      groupsData.groups.forEach(group => {
        initialStatuses[group.id] = false;
      });
      
      console.log(`📊 INITIAL STREAMING STATUS:`, initialStatuses);
      setStreamingStatus(initialStatuses);

      // Load actual streaming statuses
      await loadStreamingStatuses(groupsData.groups);

    } catch (error: any) {
      console.error('❌ Error loading data:', error);
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
      console.log(`🔄 LOADING STREAMING STATUSES for ${groupsList.length} groups...`);
      
      // Try to get all statuses at once
      try {
        const statusData = await groupApi.getAllStreamingStatuses();
        console.log(`📊 API getAllStreamingStatuses response:`, statusData);
        
        const statuses: { [groupId: string]: boolean } = {};
        const rawStatuses = statusData.streaming_statuses || {};
        
        // Process each group's status
        groupsList.forEach(group => {
          const rawStatus = rawStatuses[group.id];
          
          // IMPORTANT: Extract boolean from object if needed
          let isStreaming = false;
          if (typeof rawStatus === 'boolean') {
            isStreaming = rawStatus;
          } else if (typeof rawStatus === 'object' && rawStatus !== null) {
            isStreaming = (rawStatus as any).is_streaming || false; // Type assertion for API objects
          }
          
          statuses[group.id] = isStreaming;
          
          console.log(`📊 Group ${group.name} status processing:`, {
            groupId: group.id,
            rawStatus: rawStatus,
            extractedBoolean: isStreaming
          });
        });
        
        console.log(`📊 FINAL BOOLEAN STREAMING STATUSES:`, statuses);
        setStreamingStatus(statuses);
        
      } catch (getAllError) {
        console.log(`⚠️ getAllStreamingStatuses failed, checking individually:`, getAllError);
        
        // Fallback: check each group individually
        const statuses: { [groupId: string]: boolean } = {};
        
        for (const group of groupsList) {
          try {
            const status = await groupApi.getStreamingStatus(group.id);
            console.log(`📊 Individual status for ${group.name}:`, status);
            
            // IMPORTANT: Extract boolean from response
            let isStreaming = false;
            if (typeof status === 'boolean') {
              isStreaming = status;
            } else if (typeof status === 'object' && status !== null) {
              isStreaming = (status as any).is_streaming || false; // Type assertion for API objects
            }
            
            statuses[group.id] = isStreaming;
            
          } catch (error) {
            console.log(`⚠️ Failed to get status for ${group.name}, defaulting to false`);
            statuses[group.id] = false;
          }
        }
        
        console.log(`📊 FALLBACK BOOLEAN STREAMING STATUSES:`, statuses);
        setStreamingStatus(statuses);
      }
      
    } catch (error) {
      console.error('❌ Error loading streaming statuses:', error);
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
    console.log(`📡 STREAMING STATUS CHANGE:`, {
      groupId,
      isStreaming,
      type: typeof isStreaming,
      oldStatus: streamingStatus[groupId]
    });
    
    // Ensure we always store a boolean
    const booleanStatus = Boolean(isStreaming);
    
    setStreamingStatus(prev => {
      const newStatus = {
        ...prev,
        [groupId]: booleanStatus  // Force boolean
      };
      
      console.log(`📊 UPDATED STREAMING STATUS:`, newStatus);
      return newStatus;
    });
  };

  // Initial load
  useEffect(() => {
    loadInitialData();
  }, []);

  // Debug effect to monitor streaming status changes
  useEffect(() => {
    console.log('🔍 Current streaming status:', streamingStatus);
    console.log('🔍 Groups and their status:', groups.map(g => ({
      id: g.id,
      name: g.name,
      status: streamingStatus[g.id]
    })));
  }, [streamingStatus, groups]);

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

      console.log(`🔄 CREATING GROUP:`, newGroupForm);

      if (!newGroupForm.name.trim()) {
        toast({
          title: "Validation Error",
          description: "Group name is required",
          variant: "destructive"
        });
        return;
      }

      const result = await groupApi.createGroup({
        name: newGroupForm.name.trim(),
        description: newGroupForm.description.trim() || undefined,
        screen_count: newGroupForm.screen_count,
        orientation: newGroupForm.orientation,
        streaming_mode: newGroupForm.streaming_mode
      });

      console.log(`✅ GROUP CREATED:`, result);

      // Set new group streaming status to false
      if (result.group && result.group.id) {
        console.log(`📊 Setting streaming status to FALSE for new group: ${result.group.id}`);
        setStreamingStatus(prev => {
          const newStatus = {
            ...prev,
            [result.group.id]: false
          };
          console.log(`📊 NEW STREAMING STATUS AFTER CREATE:`, newStatus);
          return newStatus;
        });
      }

      toast({
        title: "Group Created",
        description: `Successfully created group "${newGroupForm.name}"`
      });

      // Reset form and close dialog
      setNewGroupForm({
        name: '',
        description: '',
        screen_count: 2,
        orientation: 'horizontal',
        streaming_mode: 'multi_video'
      });
      setShowCreateForm(false);

      // Reload data
      await loadInitialData();

    } catch (error: any) {
      console.error('❌ Error creating group:', error);
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
    <div className="space-y-6">
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
          
          <CreateGroupDialog
            showCreateForm={showCreateForm}
            setShowCreateForm={setShowCreateForm}
            newGroupForm={newGroupForm}
            setNewGroupForm={setNewGroupForm}
            createGroup={createGroup}
            operationInProgress={operationInProgress}
          />
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
          <Card className="p-0">
            <CardContent className="text-center py-12 px-6" style={{paddingTop: '48px'}}>
              <Monitor className="h-12 w-12 text-gray-400 mx-auto mb-4"/>
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
            {groups.map((group) => {
              const rawGroupStreamingStatus = streamingStatus[group.id];
              
              // IMPORTANT: Ensure we always pass a boolean
              let isStreamingBoolean = false;
              if (typeof rawGroupStreamingStatus === 'boolean') {
                isStreamingBoolean = rawGroupStreamingStatus;
              } else if (typeof rawGroupStreamingStatus === 'object' && rawGroupStreamingStatus !== null) {
                // Type assertion to handle API response objects
                isStreamingBoolean = (rawGroupStreamingStatus as any).is_streaming || false;
              }
              
              console.log(`🔍 RENDERING GROUP ${group.name}:`, {
                groupId: group.id,
                rawFromState: rawGroupStreamingStatus,
                rawType: typeof rawGroupStreamingStatus,
                convertedToBoolean: isStreamingBoolean,
                willPassToProp: isStreamingBoolean
              });
              
              return (
                <GroupCard
                  key={group.id}
                  group={group}
                  videos={videos}
                  clients={clients.filter(c => c.group_id === group.id)}
                  isStreaming={isStreamingBoolean}  // Always pass boolean
                  onDelete={deleteGroup}
                  onStreamingStatusChange={handleStreamingStatusChange}
                  onRefresh={refreshData}
                />
              );
            })}
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
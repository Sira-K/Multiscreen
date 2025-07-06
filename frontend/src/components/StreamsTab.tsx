import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import GroupCard from '@/components/ui/GroupCard';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, X, Play, Square, Users, Monitor, AlertCircle, CheckCircle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { groupApi, videoApi } from '@/lib/api';
import { clientApi } from '@/lib/api';



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


const StreamsTab = () => {
  console.log('🚀 StreamsTab component rendered');
  
  const { toast } = useToast();
  
  // State management
  const [groups, setGroups] = useState<Group[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [operationInProgress, setOperationInProgress] = useState<string | null>(null);
  const [clients, setClients] = useState<any[]>([]);
  const [selectedVideos, setSelectedVideos] = useState<Record<string, string>>({});
  
  // Form state for creating new groups
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupDescription, setNewGroupDescription] = useState('');
  const [newGroupScreenCount, setNewGroupScreenCount] = useState(2);
  const [newGroupOrientation, setNewGroupOrientation] = useState('horizontal');

  // Load initial data
  useEffect(() => {
    console.log('🔥 useEffect triggered - calling loadInitialData');
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    console.log('🔄 Starting loadInitialData...');
    try {
      setLoading(true);
      
      console.log('📡 Making API calls to load groups, videos, and clients...');
      
      const [groupsResponse, videosResponse, clientsResponse] = await Promise.all([
        groupApi.getGroups(),
        videoApi.getVideos(),
        clientApi.getClients()
      ]);
      
      console.log('✅ Groups response:', groupsResponse);
      console.log('✅ Videos response:', videosResponse); // DEBUG: Check this
      console.log('✅ Clients response:', clientsResponse);
      
      setGroups(groupsResponse.groups || []);
      setVideos(videosResponse.videos || []); // DEBUG: Check if videos is empty
      setClients(clientsResponse.clients || []);
      
      console.log('📊 Final state:', {
        groupsCount: (groupsResponse.groups || []).length,
        videosCount: (videosResponse.videos || []).length, // DEBUG: Check this count
        clientsCount: (clientsResponse.clients || []).length
      });
      
    } catch (error) {
      console.error('❌ Error loading initial data:', error);
      // Add more specific error logging
      if (error.message.includes('videos')) {
        console.error('🎥 Specific video loading error:', error);
      }
      toast({
        title: "Loading Error",
        description: "Failed to load data. Check console for details.",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleVideoSelect = (groupId: string, videoName: string) => {
    setSelectedVideos(prev => ({
      ...prev,
      [groupId]: videoName
    }));
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
      
      const response = await groupApi.createGroup({
        name: newGroupName.trim(),
        description: newGroupDescription.trim(),
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

      // Reload groups to get updated data
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

  const startGroup = async (groupId: string, groupName: string) => {
    try {
      setOperationInProgress(groupId);
      
      console.log(`🎬 Starting group ${groupId} with video:`, selectedVideos[groupId]);
      
      const response = await groupApi.startGroup(groupId, selectedVideos[groupId]);
      
      toast({
        title: "Group Started",
        description: `Successfully started "${groupName}" with ${selectedVideos[groupId] || 'default video'}`
      });

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
      
      console.log(`🛑 Stopping group ${groupId}`);
      
      const response = await groupApi.stopGroup(groupId);
      
      toast({
        title: "Group Stopped",
        description: `Successfully stopped "${groupName}"`
      });

      // Reload data to get updated status
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
    if (!confirm(`Are you sure you want to delete "${groupName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      setOperationInProgress(groupId);
      
      await groupApi.deleteGroup(groupId);
      
      toast({
        title: "Group Deleted",
        description: `Successfully deleted "${groupName}"`
      });

      // Reload groups
      await loadInitialData();
      
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

  const loadClients = async () => {
    try {
      const response = await clientApi.getClients();
      setClients(response.clients || []);
    } catch (error) {
      console.error('Error loading clients:', error);
    }
  };


  const assignClientToStream = async (clientId: string, streamId: string, groupId: string) => {
    try {
      setOperationInProgress(`assign-${clientId}`);
      
      await clientApi.assignStream(clientId, streamId);
      
      // Refresh clients to show updated assignments
      await loadClients();
      
      toast({
        title: "Client Assigned",
        description: `Client assigned to ${streamId}`,
        variant: "default"
      });
      
    } catch (error) {
      console.error('Error assigning client:', error);
      toast({
        title: "Assignment Error",
        description: "Failed to assign client to stream",
        variant: "destructive"
      });
    } finally {
      setOperationInProgress(null);
    }
  };

  const getStatusBadge = (group: Group) => {
    const isOperating = operationInProgress === group.id;
    
    if (isOperating) {
      return (
        <Badge className="bg-yellow-100 text-yellow-800 border-yellow-200">
          <div className="w-3 h-3 border-2 border-yellow-600 border-t-transparent rounded-full animate-spin mr-1" />
          Processing...
        </Badge>
      );
    }

    switch (group.status) {
      case 'active':
        return (
          <Badge className="bg-green-100 text-green-800 border-green-200">
            <CheckCircle className="w-3 h-3 mr-1" />
            Active
          </Badge>
        );
      case 'starting':
        return (
          <Badge className="bg-blue-100 text-blue-800 border-blue-200">
            <div className="w-3 h-3 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mr-1" />
            Starting
          </Badge>
        );
      case 'stopping':
        return (
          <Badge className="bg-orange-100 text-orange-800 border-orange-200">
            <div className="w-3 h-3 border-2 border-orange-600 border-t-transparent rounded-full animate-spin mr-1" />
            Stopping
          </Badge>
        );
      default:
        return (
          <Badge className="bg-gray-100 text-gray-800 border-gray-200">
            <AlertCircle className="w-3 h-3 mr-1" />
            Inactive
          </Badge>
        );
    }
  };

  const getLayoutDescription = (group: Group) => {
    if (group.orientation === 'grid') {
      // Assume 2x2 for now, could be enhanced to store grid dimensions
      const rows = Math.sqrt(group.screen_count);
      const cols = Math.sqrt(group.screen_count);
      return `${rows}×${cols} Grid (${group.screen_count} screens)`;
    }
    return `${group.orientation} (${group.screen_count} screens)`;
  };

  console.log('🎨 StreamsTab rendering, loading:', loading, 'groups:', groups.length);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading groups and videos...</p>
          <p className="text-sm text-gray-400 mt-2">Check browser console for debug info</p>
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
                <Label htmlFor="groupName" className="text-right">
                  Name*
                </Label>
                <Input
                  id="groupName"
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  placeholder="Enter group name"
                  className="col-span-3"
                  disabled={operationInProgress === 'create'}
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="description" className="text-right">
                  Description
                </Label>
                <Input
                  id="description"
                  value={newGroupDescription}
                  onChange={(e) => setNewGroupDescription(e.target.value)}
                  placeholder="Optional description"
                  className="col-span-3"
                  disabled={operationInProgress === 'create'}
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="screenCount" className="text-right">
                  Screens
                </Label>
                <Input
                  id="screenCount"
                  type="number"
                  min="1"
                  max="16"
                  value={newGroupScreenCount}
                  onChange={(e) => setNewGroupScreenCount(parseInt(e.target.value) || 2)}
                  className="col-span-3"
                  disabled={operationInProgress === 'create'}
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="orientation" className="text-right">
                  Layout
                </Label>
                <Select value={newGroupOrientation} onValueChange={setNewGroupOrientation} disabled={operationInProgress === 'create'}>
                  <SelectTrigger className="col-span-3">
                    <SelectValue placeholder="Select layout" />
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
                type="button"
                variant="outline"
                onClick={() => setShowCreateForm(false)}
                disabled={operationInProgress === 'create'}
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={createGroup}
                disabled={!newGroupName.trim() || operationInProgress === 'create'}
                className="bg-green-600 hover:bg-green-700"
              >
                {operationInProgress === 'create' ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                    Creating...
                  </>
                ) : (
                  'Create Group'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Groups List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {groups.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <Monitor className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Groups Found</h3>
            <p className="text-gray-600 mb-4">Create your first streaming group to get started.</p>
            <Button onClick={() => setShowCreateForm(true)} className="bg-blue-600 hover:bg-blue-700">
              <Plus className="w-4 h-4 mr-2" />
              Create First Group
            </Button>
          </div>
        ) : (
          groups.map((group) => (
            <GroupCard
              key={group.id}
              group={group}
              videos={videos}
              clients={clients}
              selectedVideo={selectedVideos[group.id]}
              operationInProgress={operationInProgress}
              onVideoSelect={handleVideoSelect}
              onStart={startGroup}
              onStop={stopGroup}
              onDelete={deleteGroup}
              onAssignClient={assignClientToStream}
            />
          ))
        )}
      </div>

      {/* Videos Info */}
      {videos.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Available Videos ({videos.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
              {videos.map((video, index) => (
                <div key={index} className="text-sm p-2 bg-gray-50 rounded">
                  <div className="font-medium">{video.name}</div>
                  <div className="text-gray-500">{video.size_mb} MB</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default StreamsTab;
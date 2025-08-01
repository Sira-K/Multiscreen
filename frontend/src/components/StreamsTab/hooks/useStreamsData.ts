// frontend/src/components/StreamsTab/hooks/useStreamsData.ts - Fixed Version

import { useState, useCallback } from 'react';
import { groupApi, videoApi, clientApi } from '../../../API/api';
import type { Group, Video, Client } from '../../../types';

export const useStreamsData = () => {
  const [groups, setGroups] = useState<Group[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Load initial data - use useCallback to prevent recreation on every render
  const loadInitialData = useCallback(async () => {
    try {
      console.log(`🔄 LOADING INITIAL DATA...`);
      
      const [groupsData, videosData, clientsData] = await Promise.all([
        groupApi.getGroups(),
        videoApi.getVideos(),
        clientApi.getClients()
      ]);

      console.log(`📊 LOADED DATA:`, {
        groups: groupsData.groups.length,
        videos: videosData.videos.length,
        clients: clientsData.clients.length
      });

      console.log(`📊 LOADED GROUPS:`, groupsData.groups.map(g => ({
        id: g.id,
        name: g.name,
        docker_running: g.docker_running,
        docker_status: g.docker_status,
        status: g.status
      })));

      console.log(`📊 LOADED CLIENTS:`, clientsData.clients.map(c => ({
        id: c.client_id,
        name: c.display_name || c.hostname,
        group_id: c.group_id,
        status: c.status
      })));

      setGroups(groupsData.groups);
      setVideos(videosData.videos);
      setClients(clientsData.clients);

    } catch (error: any) {
      console.error('❌ Error loading data:', error);
      throw error; // Re-throw to let parent handle toast
    } finally {
      setLoading(false);
    }
  }, []); // Empty dependency array - function won't change

  // Refresh data - use useCallback to prevent recreation
  const refreshData = useCallback(async () => {
    setRefreshing(true);
    try {
      await loadInitialData();
    } finally {
      setRefreshing(false);
    }
  }, [loadInitialData]); // Only depends on loadInitialData

  return {
    groups,
    setGroups,
    videos,
    setVideos,
    clients,
    setClients,
    loading,
    refreshing,
    loadInitialData,
    refreshData
  };
};
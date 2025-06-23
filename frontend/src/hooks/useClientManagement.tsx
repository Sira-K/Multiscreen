// Fixed useClientManagement.tsx with proper cleanup and error handling
import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';
const POLLING_INTERVAL = 1000; // 1 seconds
const MIN_FETCH_INTERVAL = 3000; // 3 seconds

interface ClientInfo {
  id: string;
  ip: string;
  hostname: string;
  status: 'active' | 'inactive';
  stream_id: string | null;
  group_id: string | null;
  group_name: string | null;
  group_status: string | null;
  srt_port: number;
  display_name?: string | null;
  mac_address?: string;
  platform?: string;
  last_seen: number;
  last_seen_formatted: string;
  time_since_seen?: number;
}

interface ClientsResponse {
  clients: ClientInfo[];
  available_streams?: string[];
  streaming_mode?: string;
  split_count?: number;
}

export const useClientManagement = (setOutput: (message: string) => void) => {
  const [clients, setClients] = useState<ClientInfo[]>([]);
  const [availableStreams, setAvailableStreams] = useState<string[]>([]);
  const [streamingMode, setStreamingMode] = useState<string>('');
  const [splitCount, setSplitCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [lastFetchTime, setLastFetchTime] = useState<number>(0);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState<boolean>(true);
  
  // Use refs for cleanup
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isRequestInProgress = useRef<boolean>(false);
  const mountedRef = useRef<boolean>(true);

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, []);

  const apiRequest = useCallback(async <T,>(
    url: string, 
    method: string = 'GET',
    body?: any,
    contentType: string = 'application/json'
  ): Promise<T> => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

      const options: RequestInit = {
        method,
        headers: contentType ? { 'Content-Type': contentType } : undefined,
        signal: controller.signal,
      };

      if (body) {
        options.body = contentType === 'application/json' 
          ? JSON.stringify(body) 
          : body;
      }

      const response = await fetch(`${API_BASE_URL}${url}`, options);
      clearTimeout(timeoutId);
      
      if (!mountedRef.current) {
        throw new Error('Component unmounted');
      }
      
      const responseText = await response.text();
      
      if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}: ${responseText}`);
      }
      
      try {
        return JSON.parse(responseText) as T;
      } catch (e) {
        return { message: responseText } as unknown as T;
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      throw error;
    }
  }, []);

  const fetchClients = useCallback(async (forceRefresh: boolean = false) => {
    if (isRequestInProgress.current && !forceRefresh) {
      return;
    }

    const timeSinceLastFetch = Date.now() - lastFetchTime;
    if (!forceRefresh && timeSinceLastFetch < MIN_FETCH_INTERVAL) {
      return;
    }

    if (!mountedRef.current) return;

    try {
      isRequestInProgress.current = true;
      setLoading(true);
      
      const data = await apiRequest<ClientsResponse>('/get_clients');
      
      if (!mountedRef.current) return;
      
      if (!Array.isArray(data.clients)) {
        throw new Error('Invalid client data format');
      }
      
      setClients(data.clients);
      
      if (Array.isArray(data.available_streams)) {
        const cleanStreams = data.available_streams.map(s => s.replace('live/', ''));
        setAvailableStreams(cleanStreams);
      }
      
      if (data.streaming_mode) setStreamingMode(data.streaming_mode);
      if (typeof data.split_count === 'number') setSplitCount(data.split_count);
      
      setLastFetchTime(Date.now());
      
      if (forceRefresh) {
        setOutput(`Refreshed: ${data.clients.length} clients, ${data.available_streams?.length || 0} streams`);
      }
      
    } catch (error) {
      if (!mountedRef.current) return;
      
      const errorMessage = error instanceof Error ? error.message : String(error);
      setOutput(`Error fetching clients: ${errorMessage}`);
      console.error('Fetch clients error:', error);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
        isRequestInProgress.current = false;
      }
    }
  }, [apiRequest, setOutput, lastFetchTime]);

  const assignStreamToClient = useCallback(async (clientId: string, streamId: string) => {
    try {
      await apiRequest('/assign_stream', 'POST', { 
        client_id: clientId, 
        stream_id: streamId 
      });
      
      // Refresh clients after assignment
      await fetchClients(true);
      setOutput(`Stream assigned to client`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      setOutput(`Error assigning stream: ${errorMessage}`);
      throw error;
    }
  }, [apiRequest, fetchClients, setOutput]);

  const renameClient = useCallback(async (clientId: string, newName: string) => {
    try {
      await apiRequest('/rename_client', 'POST', { 
        client_id: clientId, 
        new_name: newName 
      });
      
      // Refresh clients after rename
      await fetchClients(true);
      setOutput(`Client renamed to "${newName}"`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      setOutput(`Error renaming client: ${errorMessage}`);
      throw error;
    }
  }, [apiRequest, fetchClients, setOutput]);

  const toggleAutoRefresh = useCallback((enabled?: boolean) => {
    const newState = enabled !== undefined ? enabled : !autoRefreshEnabled;
    setAutoRefreshEnabled(newState);
    setOutput(`Auto-refresh ${newState ? 'enabled' : 'disabled'}`);
  }, [autoRefreshEnabled, setOutput]);

  const getTimeSinceLastFetch = useCallback(() => {
    if (lastFetchTime === 0) return 'Never';
    const seconds = Math.floor((Date.now() - lastFetchTime) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m ${seconds % 60}s ago`;
  }, [lastFetchTime]);

  // Polling setup
  useEffect(() => {
    if (!autoRefreshEnabled || !mountedRef.current) {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      return;
    }

    // Initial fetch
    fetchClients();
    
    // Set up polling
    pollingIntervalRef.current = setInterval(() => {
      if (autoRefreshEnabled && !isRequestInProgress.current && mountedRef.current) {
        fetchClients();
      }
    }, POLLING_INTERVAL);
    
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [fetchClients, autoRefreshEnabled]);

  return {
    clients,
    availableStreams,
    streamingMode,
    splitCount,
    loading,
    autoRefreshEnabled,
    lastFetchTime,
    fetchClients: useCallback(() => fetchClients(true), [fetchClients]), // Manual refresh
    assignStreamToClient,
    renameClient,
    toggleAutoRefresh,
    getTimeSinceLastFetch,
  };
};
import { useEffect, useRef, useState, useCallback } from 'react';
import { useToast } from '@/hooks/use-toast';
import { io, Socket } from 'socket.io-client';

interface FlaskWebSocketMessage {
  type: 'stream_status' | 'client_status' | 'error' | 'success' | 'connection_established';
  streamId?: string;
  groupId?: string;
  groupName?: string;
  status?: 'active' | 'inactive';
  message?: string;
  timestamp: string;
  clientCount?: number;
  clients?: string[];
  availableStreams?: string[];
  currentVideo?: string;
  ports?: Record<string, number>;
}

interface StreamStatus {
  streamId: string;
  groupId: string;
  groupName: string;
  status: 'active' | 'inactive';
  clientCount: number;
  clients: string[];
  availableStreams: string[];
  lastUpdate: string;
  currentVideo?: string;
  ports?: Record<string, number>;
}

interface FlaskWebSocketStreamControlProps {
  wsUrl?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export const useFlaskWebSocketStreamControl = ({ 
  wsUrl = 'http://localhost:3001',  // Flask-SocketIO URL
  reconnectInterval = 3000,
  maxReconnectAttempts = 5
}: FlaskWebSocketStreamControlProps = {}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [streamStatuses, setStreamStatuses] = useState<Map<string, StreamStatus>>(new Map());
  
  const socketRef = useRef<Socket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const { toast } = useToast();

  // Callbacks for external components
  const [onStreamStatusChange, setOnStreamStatusChange] = useState<((streamId: string, status: 'active' | 'inactive') => void) | null>(null);
  const [onClientStatusChange, setOnClientStatusChange] = useState<((streamId: string, clients: string[]) => void) | null>(null);

  const handleSocketMessage = useCallback((data: FlaskWebSocketMessage) => {
    console.log('Flask WebSocket message received:', data);

    switch (data.type) {
      case 'stream_status':
        if (data.streamId && data.status) {
          // Update local stream status
          setStreamStatuses(prev => {
            const newMap = new Map(prev);
            newMap.set(data.streamId!, {
              streamId: data.streamId!,
              groupId: data.groupId || data.streamId!,
              groupName: data.groupName || data.streamId!,
              status: data.status!,
              clientCount: data.clientCount || 0,
              clients: data.clients || [],
              availableStreams: data.availableStreams || [],
              lastUpdate: data.timestamp,
              currentVideo: data.currentVideo,
              ports: data.ports
            });
            return newMap;
          });

          // Notify external components
          if (onStreamStatusChange) {
            onStreamStatusChange(data.streamId, data.status);
          }
        }
        break;

      case 'client_status':
        if (data.streamId && data.clients) {
          // Update client connections
          setStreamStatuses(prev => {
            const newMap = new Map(prev);
            const existing = newMap.get(data.streamId!);
            if (existing) {
              newMap.set(data.streamId!, {
                ...existing,
                clientCount: data.clientCount || data.clients!.length,
                clients: data.clients!,
                lastUpdate: data.timestamp
              });
            }
            return newMap;
          });

          // Notify external components
          if (onClientStatusChange) {
            onClientStatusChange(data.streamId, data.clients);
          }
        }
        break;
        
      case 'success':
        toast({
          title: "Stream Control Success",
          description: data.message || "Stream operation completed successfully",
          variant: "default"
        });
        setIsLoading(false);
        break;
        
      case 'error':
        toast({
          title: "Stream Control Error",
          description: data.message || "Stream operation failed",
          variant: "destructive"
        });
        setIsLoading(false);
        break;

      case 'connection_established':
        toast({
          title: "Connected",
          description: "Real-time stream monitoring active",
          variant: "default"
        });
        break;
    }
  }, [toast, onStreamStatusChange, onClientStatusChange]);

  const connectSocket = useCallback(() => {
    if (socketRef.current?.connected) {
      return; // Already connected
    }

    setConnectionStatus('connecting');
    
    try {
      // Create Socket.IO client
      socketRef.current = io(wsUrl, {
        transports: ['websocket', 'polling'],
        upgrade: true,
        rememberUpgrade: true,
        timeout: 20000,
      });
      
      socketRef.current.on('connect', () => {
        setIsConnected(true);
        setConnectionStatus('connected');
        reconnectAttemptsRef.current = 0;
        console.log('Flask SocketIO connected to:', wsUrl);

        // Request current status of all streams
        socketRef.current?.emit('get_all_status');
      });

      // Listen for different event types from Flask-SocketIO
      socketRef.current.on('stream_update', handleSocketMessage);
      socketRef.current.on('client_update', handleSocketMessage);
      socketRef.current.on('connection_established', handleSocketMessage);
      socketRef.current.on('success', handleSocketMessage);
      socketRef.current.on('error', handleSocketMessage);

      socketRef.current.on('disconnect', (reason) => {
        setIsConnected(false);
        setConnectionStatus('disconnected');
        console.log('Flask SocketIO disconnected:', reason);
        
        // Attempt to reconnect if not intentionally disconnected
        if (reason !== 'io client disconnect' && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(`Attempting to reconnect (${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`);
          
          setTimeout(() => {
            connectSocket();
          }, reconnectInterval);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setConnectionStatus('error');
          toast({
            title: "Connection Failed",
            description: "Unable to connect to stream server. Please check your connection.",
            variant: "destructive"
          });
        }
      });

      socketRef.current.on('connect_error', (error) => {
        console.error('Flask SocketIO connection error:', error);
        setConnectionStatus('error');
      });

    } catch (error) {
      console.error('Failed to create Flask SocketIO connection:', error);
      setConnectionStatus('error');
    }
  }, [wsUrl, reconnectInterval, maxReconnectAttempts, toast, handleSocketMessage]);

  useEffect(() => {
    connectSocket();

    // Cleanup on unmount
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, [connectSocket]);

  const sendStreamControl = useCallback((streamId: string, action: 'start' | 'stop') => {
    if (!socketRef.current?.connected) {
      toast({
        title: "Connection Error",
        description: "WebSocket is not connected. Please wait for reconnection.",
        variant: "destructive"
      });
      return false;
    }

    setIsLoading(true);
    
    const message = {
      streamId,
      groupId: streamId, // For Flask backend compatibility
      action,
      timestamp: new Date().toISOString()
    };

    try {
      socketRef.current.emit('stream_control', message);
      console.log('Sent stream control to Flask:', message);
      return true;
    } catch (error) {
      console.error('Failed to send Flask SocketIO message:', error);
      setIsLoading(false);
      toast({
        title: "Send Error",
        description: "Failed to send stream control command",
        variant: "destructive"
      });
      return false;
    }
  }, [toast]);

  const startStream = useCallback((streamId: string) => sendStreamControl(streamId, 'start'), [sendStreamControl]);
  const stopStream = useCallback((streamId: string) => sendStreamControl(streamId, 'stop'), [sendStreamControl]);

  // Get stream status
  const getStreamStatus = useCallback((streamId: string): StreamStatus | null => {
    return streamStatuses.get(streamId) || null;
  }, [streamStatuses]);

  // Manual reconnect
  const reconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect();
    }
    reconnectAttemptsRef.current = 0;
    connectSocket();
  }, [connectSocket]);

  return {
    // Connection state
    isConnected,
    isLoading,
    connectionStatus,
    
    // Stream control
    startStream,
    stopStream,
    sendStreamControl,
    
    // Status information
    streamStatuses: Array.from(streamStatuses.values()),
    getStreamStatus,
    
    // Event handlers (for external components to register)
    setOnStreamStatusChange,
    setOnClientStatusChange,
    
    // Manual control
    reconnect
  };
};
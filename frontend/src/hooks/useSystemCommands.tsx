// Fixed useSystemCommands.tsx with better error handling
import { useState, useEffect, useCallback } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

interface SystemStatus {
  srt: boolean;
  server: boolean;
}

export const useSystemCommands = (setOutput: (output: string) => void) => {
  const [activeButton, setActiveButton] = useState<string | null>(null);
  const [containerId, setContainerId] = useState<string | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    srt: false,
    server: false,
  });
  const [lastCheckTime, setLastCheckTime] = useState(0);

  // System status checking - only every 2 minutes
  const checkSystemStatus = useCallback(async () => {
    // Only check if enough time has passed (2 minutes)
    const now = Date.now();
    if (now - lastCheckTime < 120000) { // 2 minutes
      return;
    }
    
    setLastCheckTime(now);
    
    try {
      const res = await fetch(`${API_BASE_URL}/system_status`);
      if (res.ok) {
        const data = await res.json();
        setSystemStatus({
          srt: data.srt_running || false,
          server: data.server_running || false,
        });
      }
    } catch (err) {
      console.error("Error checking system status:", err);
      // Don't update the output to avoid flooding it with error messages
    }
  }, [lastCheckTime]);

  const handleSystemCommand = useCallback(async (command: 'startSrtServer' | 'startServerStream' | 'stopSystem') => {
    setActiveButton(command);
    setOutput('Processing...');
    try {
      switch (command) {
        case 'startSrtServer': {
          // This command is now handled directly by the SRT start
          setSystemStatus(prev => ({ ...prev, srt: true }));
          setOutput('SRT Server Started');
          break;
        }
        case 'startServerStream': {
          const res = await fetch(`${API_BASE_URL}/start_docker`, { method: 'POST' });
          const data = await res.json();
          if (res.ok && data.container_id) {
            setContainerId(data.container_id);
            setSystemStatus(prev => ({ ...prev, server: true }));
            setOutput('Server Stream Started');
          } else {
            setOutput(`Error: ${data.message || 'Unknown error'}`);
          }
          break;
        }
        case 'stopSystem': {
          if (systemStatus.srt) {
            await fetch(`${API_BASE_URL}/stop_srt`, { method: 'POST' });
          }

          if (containerId) {
            await fetch(`${API_BASE_URL}/stop_docker`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ container_id: containerId }),
            });
          }

          setSystemStatus({ srt: false, server: false });
          setContainerId(null);
          setOutput('System Stopped');
          break;
        }
      }
    } catch (err) {
      console.error('Command failed:', err);
      setOutput(`Error: ${err instanceof Error ? err.message : 'An unexpected error occurred'}`);
    } finally {
      setActiveButton(null);
    }
  }, [systemStatus, containerId, setOutput]);

  // System status polling - every 2 minutes
  useEffect(() => {
    console.log('Setting up system status polling (2 minutes interval)');
    
    // Initial check
    checkSystemStatus();
    
    // Set up polling at a slower frequency
    const interval = setInterval(() => {
      checkSystemStatus();
    }, 120000); // Every 2 minutes
    
    return () => {
      console.log('Cleaning up system status polling');
      clearInterval(interval);
    };
  }, [checkSystemStatus]);

  return {
    activeButton,
    containerId,
    systemStatus,
    handleSystemCommand,
  };
};

export default useSystemCommands;
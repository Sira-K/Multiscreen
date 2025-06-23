// Fixed useStreamSettings.tsx with proper error handling
import { useState, useCallback } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

interface StreamSettings {
  resolution: string;
  framerate: number;
  seiUuid: string;
}

export const useStreamSettings = (setOutput: (output: string) => void) => {
  const [streamSettings, setStreamSettings] = useState<StreamSettings>({
    resolution: '3840x1080',
    framerate: 30,
    seiUuid: 'unique-uuid-here',
  });

  const updateSetting = useCallback((setting: keyof StreamSettings, value: string | number) => {
    setStreamSettings(prev => ({ ...prev, [setting]: value }));
  }, []);

  const handleFileUpload = useCallback(async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
  
    try {
      const response = await fetch(`${API_BASE_URL}/upload_video`, {
        method: 'POST',
        body: formData,
      });
  
      const data = await response.json();
  
      if (response.ok) {
        updateSetting('resolution', data.resolution);
        updateSetting('framerate', data.framerate);
        setOutput(`✅ Video uploaded. Resolution: ${data.resolution}, Framerate: ${data.framerate}`);
      } else {
        setOutput(`❌ Error: ${data.error}`);
      }
    } catch (err) {
      setOutput(`❌ Upload failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  }, [updateSetting, setOutput]);
  

  return {
    streamSettings,
    updateSetting,
    handleFileUpload
  };
};
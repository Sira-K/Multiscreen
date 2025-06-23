// hooks/useScreenManagement.tsx - Enhanced with Grid Layout Support
import { useState, useEffect, useCallback } from 'react';

interface Screen {
  id: number;
  selectedStream: string;
  gridPosition?: {
    row: number;
    col: number;
  };
}

type Orientation = 'horizontal' | 'vertical' | 'grid';

export const useScreenManagement = (
  setOutput: (output: string) => void,
  availableStreams: string[]
) => {
  const [screenCount, setScreenCount] = useState(4);
  const [orientation, setOrientation] = useState<Orientation>('grid');
  const [gridRows, setGridRows] = useState(2);
  const [gridCols, setGridCols] = useState(2);
  const [screenIPs, setScreenIPs] = useState<{ [key: number]: string }>({});
  const [screens, setScreens] = useState<Screen[]>([]);
  const [lastCheckTime, setLastCheckTime] = useState(0);

  // Initialize screens with default values and grid positions
  useEffect(() => {
    initializeScreens();
  }, [screenCount, orientation, gridRows, gridCols, availableStreams]);

  const initializeScreens = () => {
    if (!availableStreams || availableStreams.length === 0) {
      setScreens([]);
      return;
    }

    const newScreens: Screen[] = [];
    const effectiveCount = orientation === 'grid' ? gridRows * gridCols : screenCount;
    
    for (let i = 1; i <= effectiveCount; i++) {
      const streamIndex = (i - 1) % availableStreams.length;
      const screen: Screen = {
        id: i,
        selectedStream: availableStreams[streamIndex] || availableStreams[0]
      };

      // Add grid position for grid layout
      if (orientation === 'grid') {
        const row = Math.floor((i - 1) / gridCols) + 1;
        const col = ((i - 1) % gridCols) + 1;
        screen.gridPosition = { row, col };
      }

      newScreens.push(screen);
    }
    
    setScreens(newScreens);
  };

  const updateScreenCount = (count: number) => {
    setScreenCount(count);
    if (orientation !== 'grid') {
      // For non-grid layouts, update screen count directly
      return;
    }
    // For grid layouts, count is calculated from rows * cols
  };

  const updateOrientation = (newOrientation: Orientation) => {
    setOrientation(newOrientation);
    
    if (newOrientation === 'grid') {
      // When switching to grid, ensure screen count matches grid dimensions
      setScreenCount(gridRows * gridCols);
    }
  };

  const updateGridDimensions = (rows: number, cols: number) => {
    setGridRows(rows);
    setGridCols(cols);
    
    if (orientation === 'grid') {
      setScreenCount(rows * cols);
    }
  };

  const handleIPChange = (screenId: number, value: string) => {
    setScreenIPs(prev => ({ ...prev, [screenId]: value }));
  };

  const saveIPsToBackend = async (
    ips: { [key: number]: string },
    count: number,
    screenOrientation: Orientation,
    rows?: number,
    cols?: number
  ) => {
    try {
      // Prepare the payload with grid support
      const payload = {
        ips: ips,
        screenCount: count,
        orientation: screenOrientation,
        gridRows: rows || gridRows,
        gridCols: cols || gridCols
      };

      console.log('Sending payload to backend:', payload);
      
      // Send request to the backend
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/set_screen_ips`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      console.log('Response status:', response.status);
      
      // Parse the response
      const data = await response.json();
      console.log('Response data:', data);
      
      if (response.ok) {
        let layoutDesc = '';
        if (screenOrientation === 'grid') {
          layoutDesc = `${rows || gridRows}×${cols || gridCols} grid layout`;
        } else {
          layoutDesc = `${screenOrientation} layout`;
        }
        setOutput(`Success: Screen configuration saved (${layoutDesc}, ${count} screens)`);
      } else {
        setOutput(`Failed: ${data.error || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Network or other error:', err);
      setOutput(`Failed to save screen configuration: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const updateScreenStream = (screenId: number, stream: string) => {
    setScreens(prev =>
      prev.map(screen =>
        screen.id === screenId ? { ...screen, selectedStream: stream } : screen
      )
    );
  };

  // Enhanced screen status checking with grid support
  const checkScreenStatus = useCallback(async () => {
    // Only check if enough time has passed (5 minutes)
    const now = Date.now();
    if (now - lastCheckTime < 300000) { // 5 minutes
      return;
    }
    
    setLastCheckTime(now);
    
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/screen_status`);
      if (response.ok) {
        const data = await response.json();
        
        // Update state from server response
        if (data.screen_count !== screenCount) {
          setScreenCount(data.screen_count || 4);
        }
        if (data.orientation !== orientation) {
          setOrientation(data.orientation || 'grid');
        }
        if (data.grid_rows !== gridRows) {
          setGridRows(data.grid_rows || 2);
        }
        if (data.grid_cols !== gridCols) {
          setGridCols(data.grid_cols || 2);
        }
        if (data.screen_ips) {
          setScreenIPs(data.screen_ips);
        }
      }
    } catch (err) {
      // Silent error to avoid flooding console
      console.debug('Error checking screen status:', err);
    }
  }, [lastCheckTime, screenCount, orientation, gridRows, gridCols]);

  const launchPlayer = async (screenId: number) => {
    const screen = screens.find(s => s.id === screenId);
    if (!screen) {
      setOutput(`Screen ${screenId} not found`);
      return;
    }
    
    try {
      const streamUrl = `srt://${import.meta.env.VITE_SRT_IP || '127.0.0.1'}:10080?streamid=#!::r=live/${screen.selectedStream},m=request,latency=5000000`;
      
      // Prepare grid position info for the backend
      const gridPosition = screen.gridPosition || {};
      
      const payload = {
        screenId,
        streamUrl,
        orientation,
        gridRows,
        gridCols,
        gridPosition
      };
      
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/launch_player`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      
      const data = await res.json();
      
      if (res.ok) {
        let positionDesc = '';
        if (orientation === 'grid' && screen.gridPosition) {
          positionDesc = ` at grid position R${screen.gridPosition.row}C${screen.gridPosition.col}`;
        } else if (orientation === 'horizontal') {
          positionDesc = ` (column ${screenId})`;
        } else if (orientation === 'vertical') {
          positionDesc = ` (row ${screenId})`;
        }
        
        setOutput(`Player launched on screen ${screenId}${positionDesc}: ${data.message}`);
      } else {
        setOutput(`Launch failed: ${data.error}`);
      }
    } catch (err) {
      console.error(err);
      setOutput(`Error launching player on screen ${screenId}`);
    }
  };

  // Apply a layout preset
  const applyLayoutPreset = (preset: {
    orientation: Orientation;
    screen_count: number;
    grid_rows?: number;
    grid_cols?: number;
  }) => {
    setOrientation(preset.orientation);
    setScreenCount(preset.screen_count);
    
    if (preset.orientation === 'grid' && preset.grid_rows && preset.grid_cols) {
      setGridRows(preset.grid_rows);
      setGridCols(preset.grid_cols);
    }
    
    const layoutDesc = preset.orientation === 'grid' 
      ? `${preset.grid_rows}×${preset.grid_cols} grid`
      : `${preset.orientation}`;
    
    setOutput(`Applied ${layoutDesc} layout preset`);
  };

  // Get layout description for display
  const getLayoutDescription = () => {
    if (orientation === 'grid') {
      return `${gridRows}×${gridCols} grid (${screenCount} screens)`;
    }
    return `${orientation} (${screenCount} screens)`;
  };

  // Get effective screen count (for grid, this is rows * cols)
  const getEffectiveScreenCount = () => {
    return orientation === 'grid' ? gridRows * gridCols : screenCount;
  };

  // Get screen position description
  const getScreenPositionDescription = (screenId: number) => {
    const screen = screens.find(s => s.id === screenId);
    if (!screen) return '';
    
    if (orientation === 'grid' && screen.gridPosition) {
      return `R${screen.gridPosition.row}C${screen.gridPosition.col}`;
    } else if (orientation === 'horizontal') {
      return `Col ${screenId}`;
    } else {
      return `Row ${screenId}`;
    }
  };

  // Manual refresh function
  const refreshScreenStatus = checkScreenStatus;

  return {
    screens,
    screenCount,
    orientation,
    gridRows,
    gridCols,
    screenIPs,
    updateScreenCount,
    updateOrientation,
    updateGridDimensions,
    updateScreenStream,
    handleIPChange,
    saveIPsToBackend,
    launchPlayer,
    refreshScreenStatus,
    applyLayoutPreset,
    getLayoutDescription,
    getEffectiveScreenCount,
    getScreenPositionDescription,
    // New grid-specific functions
    setGridRows,
    setGridCols,
  };
};
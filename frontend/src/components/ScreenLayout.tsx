import React, { useState, useEffect } from 'react';

interface Screen {
  id: number;
  selectedStream: string;
}

interface ScreenLayoutProps {
  screenCount: number;
  setScreenCount: (count: number) => void;
  screens: Screen[];
  updateScreenStream: (screenId: number, stream: string) => void;
  launchPlayer: (screenId: number) => Promise<void>;
  availableStreams: string[];
  orientation: 'horizontal' | 'vertical' | 'grid';
  setOrientation: (o: 'horizontal' | 'vertical' | 'grid') => void;
  gridRows?: number;
  gridCols?: number;
  setGridRows?: (rows: number) => void;
  setGridCols?: (cols: number) => void;
}

const ScreenLayout: React.FC<ScreenLayoutProps> = ({
  screenCount,
  setScreenCount,
  screens,
  updateScreenStream,
  launchPlayer,
  availableStreams,
  orientation,
  setOrientation,
  gridRows = 2,
  gridCols = 2,
  setGridRows = () => {},
  setGridCols = () => {},
}) => {
  const [activePreset, setActivePreset] = useState<string>('');

  // Layout presets for quick configuration
  const layoutPresets = [
    // Horizontal layouts
    { name: '2H', label: '2 Horizontal', orientation: 'horizontal', screen_count: 2 },
    { name: '3H', label: '3 Horizontal', orientation: 'horizontal', screen_count: 3 },
    { name: '4H', label: '4 Horizontal', orientation: 'horizontal', screen_count: 4 },
    
    // Vertical layouts
    { name: '2V', label: '2 Vertical', orientation: 'vertical', screen_count: 2 },
    { name: '3V', label: '3 Vertical', orientation: 'vertical', screen_count: 3 },
    { name: '4V', label: '4 Vertical', orientation: 'vertical', screen_count: 4 },
    
    // Grid layouts
    { name: '2x2', label: '2×2 Grid', orientation: 'grid', grid_rows: 2, grid_cols: 2, screen_count: 4 },
    { name: '2x3', label: '2×3 Grid', orientation: 'grid', grid_rows: 2, grid_cols: 3, screen_count: 6 },
    { name: '3x2', label: '3×2 Grid', orientation: 'grid', grid_rows: 3, grid_cols: 2, screen_count: 6 },
    { name: '3x3', label: '3×3 Grid', orientation: 'grid', grid_rows: 3, grid_cols: 3, screen_count: 9 },
    { name: '2x4', label: '2×4 Grid', orientation: 'grid', grid_rows: 2, grid_cols: 4, screen_count: 8 },
    { name: '4x2', label: '4×2 Grid', orientation: 'grid', grid_rows: 4, grid_cols: 2, screen_count: 8 },
  ];

  // Update active preset when layout changes
  useEffect(() => {
    const currentPreset = layoutPresets.find(preset => {
      if (preset.orientation !== orientation) return false;
      if (preset.orientation === 'grid') {
        return preset.grid_rows === gridRows && preset.grid_cols === gridCols;
      }
      return preset.screen_count === screenCount;
    });
    setActivePreset(currentPreset?.name || '');
  }, [orientation, screenCount, gridRows, gridCols]);

  // Apply a preset configuration
  const applyPreset = (preset: any) => {
    setOrientation(preset.orientation);
    setScreenCount(preset.screen_count);
    if (preset.orientation === 'grid') {
      setGridRows(preset.grid_rows);
      setGridCols(preset.grid_cols);
    }
    setActivePreset(preset.name);
  };

  // Handle manual grid dimension changes
  const handleGridRowsChange = (rows: number) => {
    setGridRows(rows);
    setScreenCount(rows * gridCols);
  };

  const handleGridColsChange = (cols: number) => {
    setGridCols(cols);
    setScreenCount(gridRows * cols);
  };

  // Get grid CSS styles
  const getGridStyles = () => {
    if (orientation === 'grid') {
      return {
        display: 'grid',
        gridTemplateColumns: `repeat(${gridCols}, 1fr)`,
        gridTemplateRows: `repeat(${gridRows}, 1fr)`,
        gap: '16px',
        aspectRatio: `${gridCols}/${gridRows}`,
      };
    } else if (orientation === 'horizontal') {
      return {
        display: 'grid',
        gridTemplateColumns: `repeat(${screenCount}, 1fr)`,
        gridTemplateRows: '1fr',
        gap: '16px',
      };
    } else { // vertical
      return {
        display: 'grid',
        gridTemplateColumns: '1fr',
        gridTemplateRows: `repeat(${screenCount}, 1fr)`,
        gap: '16px',
      };
    }
  };

  // Get screen position description
  const getScreenPosition = (screenIndex: number) => {
    if (orientation === 'grid') {
      const row = Math.floor(screenIndex / gridCols) + 1;
      const col = (screenIndex % gridCols) + 1;
      return `R${row}C${col}`;
    } else if (orientation === 'horizontal') {
      return `Col ${screenIndex + 1}`;
    } else {
      return `Row ${screenIndex + 1}`;
    }
  };

  // Get layout description
  const getLayoutDescription = () => {
    if (orientation === 'grid') {
      return `${gridRows}×${gridCols} grid layout (${screenCount} screens)`;
    } else {
      return `${orientation} layout (${screenCount} screens)`;
    }
  };

  return (
    <div className="screen-layout-section">
      <h3>Screen Layout Configuration</h3>

      {/* Layout Presets */}
      <div className="grid-controls">
        <div className="grid-presets">
          <label>Quick Layout Presets:</label>
          <div className="preset-buttons">
            {layoutPresets.map(preset => (
              <button
                key={preset.name}
                className={`preset-button ${activePreset === preset.name ? 'active' : ''}`}
                onClick={() => applyPreset(preset)}
                title={preset.label}
              >
                {preset.name}
              </button>
            ))}
          </div>
        </div>

        {/* Manual Controls */}
        <div className="grid-manual-controls">
          <div className="grid-dimension-selector">
            <label>Layout Type:</label>
            <select
              value={orientation}
              onChange={e => setOrientation(e.target.value as 'horizontal' | 'vertical' | 'grid')}
            >
              <option value="horizontal">Horizontal</option>
              <option value="vertical">Vertical</option>
              <option value="grid">Grid</option>
            </select>
          </div>

          {orientation === 'grid' ? (
            <>
              <div className="grid-dimension-selector">
                <label>Grid Rows:</label>
                <select
                  value={gridRows}
                  onChange={e => handleGridRowsChange(parseInt(e.target.value))}
                >
                  {[1, 2, 3, 4, 5, 6].map(num => (
                    <option key={num} value={num}>{num}</option>
                  ))}
                </select>
              </div>

              <div className="grid-dimension-selector">
                <label>Grid Columns:</label>
                <select
                  value={gridCols}
                  onChange={e => handleGridColsChange(parseInt(e.target.value))}
                >
                  {[1, 2, 3, 4, 5, 6].map(num => (
                    <option key={num} value={num}>{num}</option>
                  ))}
                </select>
              </div>
            </>
          ) : (
            <div className="grid-dimension-selector">
              <label>Screen Count:</label>
              <select
                value={screenCount}
                onChange={e => setScreenCount(parseInt(e.target.value))}
              >
                {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(num => (
                  <option key={num} value={num}>{num}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Layout Information */}
      <div className="layout-info">
        <p><strong>Current Layout:</strong> {getLayoutDescription()}</p>
        {orientation === 'grid' && (
          <p><strong>Grid Details:</strong> {gridRows} rows × {gridCols} columns = {screenCount} screens</p>
        )}
      </div>

      {/* Screen Grid Display */}
      <div className="screens-grid" style={getGridStyles()}>
        {screens.slice(0, screenCount).map((screen, index) => (
          <div 
            key={screen.id} 
            className="screen-config"
            data-position={getScreenPosition(index)}
          >
            <h4>
              Screen {screen.id}
              <span className="screen-position">({getScreenPosition(index)})</span>
            </h4>
            
            <div className="stream-selector">
              <label>Assigned Stream:</label>
              <select
                value={screen.selectedStream}
                onChange={e => updateScreenStream(screen.id, e.target.value)}
              >
                {availableStreams.map(stream => (
                  <option key={stream} value={stream}>
                    {stream}
                  </option>
                ))}
              </select>
            </div>
            
            <button onClick={() => launchPlayer(screen.id)}>
              Launch Player
            </button>
          </div>
        ))}
      </div>

      {/* Grid Visualization Helper */}
      {orientation === 'grid' && (
        <div className="grid-visualization">
          <h4>Grid Layout Preview:</h4>
          <div 
            className="grid-preview" 
            style={{
              display: 'grid',
              gridTemplateColumns: `repeat(${gridCols}, 1fr)`,
              gridTemplateRows: `repeat(${gridRows}, 1fr)`,
              gap: '2px',
              maxWidth: '200px',
              aspectRatio: `${gridCols}/${gridRows}`,
            }}
          >
            {Array.from({ length: screenCount }, (_, index) => (
              <div 
                key={index}
                className="grid-cell"
                style={{
                  backgroundColor: '#e3f2fd',
                  border: '1px solid #4a90e2',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '10px',
                  fontWeight: 'bold',
                }}
              >
                {index + 1}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ScreenLayout;
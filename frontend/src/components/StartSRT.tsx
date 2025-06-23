import React, { useState } from 'react';

interface StartSRTProps {
  setOutput: (msg: string) => void;
  selectedVideo: string;
  disabled?: boolean;
  isStarting?: boolean;
}

const StartSRT: React.FC<StartSRTProps> = ({ 
  setOutput, 
  selectedVideo, 
  disabled = false,
  isStarting = false
}) => {
  // Looping control state
  const [enableLooping, setEnableLooping] = useState<boolean>(true);
  const [loopMode, setLoopMode] = useState<string>('infinite'); // 'infinite', 'finite', 'once'
  const [loopCount, setLoopCount] = useState<number>(5);

  const handleStart = async () => {
    try {
      // Determine loop count based on mode
      let actualLoopCount: number;
      switch (loopMode) {
        case 'infinite':
          actualLoopCount = -1;
          break;
        case 'once':
          actualLoopCount = 0;
          break;
        case 'finite':
          actualLoopCount = loopCount;
          break;
        default:
          actualLoopCount = -1;
      }

      // Build output message
      let loopDescription = '';
      if (!enableLooping || loopMode === 'once') {
        loopDescription = ' (plays once)';
      } else if (loopMode === 'infinite') {
        loopDescription = ' (infinite loop)';
      } else {
        loopDescription = ` (loops ${loopCount} times)`;
      }

      setOutput(`Starting SRT with ${selectedVideo ? 'video: ' + selectedVideo : 'test pattern'}${loopDescription}...`);
      
      // Make the API call with looping configuration
      const apiUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/start_group_srt`;
      
      const requestBody = {
        mp4_file: selectedVideo ? `uploads/${selectedVideo}` : null,
        enable_looping: enableLooping,
        loop_count: actualLoopCount
      };

      console.log('SRT request payload:', requestBody);
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });
      
      if (response.ok) {
        const data = await response.json();
        setOutput(`✅ ${data.message}`);
        
        // Log additional info
        if (data.loop_mode) {
          console.log(`Loop mode: ${data.loop_mode}`);
        }
      } else {
        const errorData = await response.json();
        setOutput(`❌ SRT start failed: ${errorData.error || 'Unknown error'}`);
      }
    } catch (err) {
      console.error("Error starting SRT:", err);
      setOutput("❌ Failed to connect to backend for SRT start.");
    }
  };

  return (
    <div className="start-srt-container">
      <div className="srt-controls">
        <h4>SRT Stream Configuration</h4>
        
        {/* Video Looping Controls */}
        <div className="looping-controls">
          <div className="control-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={enableLooping}
                onChange={(e) => setEnableLooping(e.target.checked)}
                disabled={disabled || isStarting}
              />
              Enable Video Looping
            </label>
          </div>

          {enableLooping && (
            <div className="control-group">
              <label>Loop Mode:</label>
              <select
                value={loopMode}
                onChange={(e) => setLoopMode(e.target.value)}
                disabled={disabled || isStarting}
                className="loop-mode-select"
              >
                <option value="infinite">Infinite Loop</option>
                <option value="finite">Loop Specific Times</option>
                <option value="once">Play Once</option>
              </select>

              {loopMode === 'finite' && (
                <div className="loop-count-container">
                  <label>Loop Count:</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={loopCount}
                    onChange={(e) => setLoopCount(parseInt(e.target.value) || 1)}
                    disabled={disabled || isStarting}
                    className="loop-count-input"
                  />
                  <span className="loop-explanation">
                    (Total plays: {loopCount + 1})
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Current Configuration Display */}
        <div className="config-summary">
          <strong>Configuration:</strong>
          <ul>
            <li>Video: {selectedVideo || 'Test Pattern'}</li>
            <li>
              Looping: {
                !enableLooping || loopMode === 'once' 
                  ? 'Disabled (plays once)'
                  : loopMode === 'infinite' 
                    ? 'Infinite loop'
                    : `${loopCount} loops (${loopCount + 1} total plays)`
              }
            </li>
          </ul>
        </div>

        {/* Start Button */}
        <button 
          onClick={handleStart}
          disabled={disabled || isStarting}
          className="start-srt-button"
        >
          {isStarting ? 'Starting...' : 'Start SRT Stream'}
        </button>
      </div>
    </div>
  );
};

export default StartSRT;
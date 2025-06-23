import React from 'react';

interface StreamSettings {
  resolution: string;
  framerate: number;
  seiUuid: string;
}

interface StatusDisplayProps {
  output: string;
  streamSettings: StreamSettings;
  updateSetting: (setting: keyof StreamSettings, value: string | number) => void;
  setOutput: (output: string) => void;
  handleFileUpload: (file: File) => Promise<void>;
}

const StatusDisplay: React.FC<StatusDisplayProps> = ({
  output,
  setOutput
}) => {
  return (
    <div className="status-section-full">
      <div className="output-display">
        <h3>System Output</h3>
        <div className="output-log">{output}</div>
        <button onClick={() => setOutput('Output cleared')}>Clear</button>
      </div>
    </div>
  );
};

export default StatusDisplay;
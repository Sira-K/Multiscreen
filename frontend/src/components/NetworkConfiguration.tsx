import React from 'react';

interface Screen {
  id: number;
  selectedStream: string;
}

interface NetworkConfigurationProps {
  screens: Screen[];
  screenIPs: { [key: number]: string };
  handleIPChange: (screenId: number, value: string) => void;
  saveIPsToBackend: (
    screenIPs: { [key: number]: string },
    screenCount: number,
    orientation: 'horizontal' | 'vertical'
  ) => Promise<void>;
  screenCount: number;
  orientation: 'horizontal' | 'vertical';
}

const NetworkConfiguration: React.FC<NetworkConfigurationProps> = ({
  screens,
  screenIPs,
  handleIPChange,
  saveIPsToBackend,
  screenCount,
  orientation
}) => {
  return (
    <div className="screen-config-section">
      <h3>Network Configuration</h3>
      <div className="screen-ip-inputs">
        {screens.map(screen => (
          <div key={screen.id} className="screen-ip-input">
            <label>Screen {screen.id} IP:</label>
            <input
              type="text"
              placeholder={`IP for screen ${screen.id}`}
              value={screenIPs[screen.id] || ''}
              onChange={e => handleIPChange(screen.id, e.target.value)}
            />
          </div>
        ))}
      </div>
      <button
        onClick={() => saveIPsToBackend(screenIPs, screenCount, orientation)}
        className="save-ips-button"
      >
        Save Screen IPs
      </button>
    </div>
  );
};

export default NetworkConfiguration;
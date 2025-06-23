import React from 'react';
import './index.css';

interface SystemStatusBarProps {
  systemStatus: {
    srt: boolean;
  };
  serverPing: number | null;
}

const SystemStatusBar: React.FC<SystemStatusBarProps> = ({ systemStatus, serverPing }) => {
  return (
    <div className="status-bar">
      <div className="server-status">
        SRT Server: <span className={systemStatus.srt ? 'active' : 'inactive'}>
          {systemStatus.srt ? 'Running' : 'Stopped'}
        </span>
      </div>
      <div className="ping-status">
        Last Ping: {serverPing ? `${serverPing}ms` : 'Not tested'}
      </div>
    </div>
  );
};

export default SystemStatusBar;
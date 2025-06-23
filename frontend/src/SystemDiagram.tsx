import React from 'react';
import './index.css';

interface SystemDiagramProps {
  systemStatus: {
    server: boolean;
    srt: boolean;
  };
  clientConfigs: Array<{
    id: number;
    name: string;
    active: boolean;
    screen: string;
  }>;
}

const SystemDiagram: React.FC<SystemDiagramProps> = ({ systemStatus, clientConfigs }) => {
  return (
    <div className="system-diagram">
      <div className={`node server ${systemStatus.server ? 'active' : ''}`}>Server</div>
      <div className="arrow">→</div>
      <div className={`node srt ${systemStatus.srt ? 'active' : ''}`}>SRT Server</div>
      <div className="arrow">→</div>
      <div className="clients">
        {clientConfigs.map(client => (
          <div key={`client-${client.id}`} className={`node client ${client.active ? 'active' : ''}`}>
            {client.name}
            <div className="client-screen">{client.screen}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SystemDiagram;
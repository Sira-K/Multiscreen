// frontend/src/components/ui/GroupCard/sections/ActiveStreamsSection.tsx

import React from 'react';
import { Group } from '../../../../types';

interface ActiveStreamsSectionProps {
  group: Group;
  localIsStreaming: boolean;
}

const ActiveStreamsSection: React.FC<ActiveStreamsSectionProps> = ({
  group,
  localIsStreaming
}) => {
  // Only show when streaming and streams are available
  if (!localIsStreaming || !group.available_streams || group.available_streams.length === 0) {
    return null;
  }

  return (
    <div className="p-2 bg-green-50 rounded text-xs">
      <div className="font-medium text-green-800 mb-1">Active Streams</div>
      <div className="space-y-1 max-h-16 overflow-y-auto">
        {group.available_streams.slice(0, 1).map((streamPath, index) => (
          <div key={index} className="font-mono bg-white p-1 rounded border text-xs break-all">
            srt://127.0.0.1:{group.ports?.srt_port || 10080}?streamid=#!::r={streamPath},m=request
          </div>
        ))}
        {group.available_streams.length > 1 && (
          <div className="text-green-700">
            +{group.available_streams.length - 1} more streams available
          </div>
        )}
      </div>
    </div>
  );
};

export default ActiveStreamsSection;
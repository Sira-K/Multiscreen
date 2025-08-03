// frontend/src/components/ui/GroupCard/sections/DockerInfoSection.tsx

import React from 'react';
import { Group } from '../../../../types';

interface DockerInfoSectionProps {
  group: Group;
}

const DockerInfoSection: React.FC<DockerInfoSectionProps> = ({ group }) => {
  return (
    <div className="p-2 bg-blue-50 rounded text-xs">
      <div className="font-medium text-blue-800 mb-1">Container Info</div>
      <div className="grid grid-cols-2 gap-1 text-blue-700">
        <span>ID: {group.container_id ? group.container_id.substring(0, 8) : 'N/A'}</span>
        <span>Status: {group.docker_status || 'unknown'}</span>
      </div>
    </div>
  );
};

export default DockerInfoSection;
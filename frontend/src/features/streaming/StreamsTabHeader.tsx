// frontend/src/features/StreamsTab/StreamsTabHeader.tsx

import React from 'react';
import { Plus } from 'lucide-react';
import { Button } from "@/components/ui/button";
import CreateGroupDialog from '@/components/ui/CreateGroupDialog';
import { RefreshCw } from "lucide-react";

interface StreamsTabHeaderProps {
  showCreateForm: boolean;
  setShowCreateForm: (show: boolean) => void;
  refreshData: () => Promise<void>;
  refreshing: boolean;
  newGroupForm: {
    name: string;
    description: string;
    screen_count: number;
    orientation: 'horizontal' | 'vertical' | 'grid';
    streaming_mode: 'multi_video' | 'single_video_split';
  };
  setNewGroupForm: (form: any) => void;
  createGroup: () => Promise<void>;
  operationInProgress: string | null;
}

const StreamsTabHeader: React.FC<StreamsTabHeaderProps> = ({
  showCreateForm,
  setShowCreateForm,
  refreshData,
  refreshing,
  newGroupForm,
  setNewGroupForm,
  createGroup,
  operationInProgress
}) => {
  return (
    <div className="flex justify-between items-center">
      <div>
        <h2 className="text-2xl font-bold text-gray-800">Streaming Groups</h2>
        <p className="text-gray-600">Manage multi-screen video streaming groups and client assignments</p>
      </div>
      
      <div className="flex gap-2">
        <Button
          variant="outline"
          onClick={refreshData}
          disabled={refreshing}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
        
        <CreateGroupDialog
          showCreateForm={showCreateForm}
          setShowCreateForm={setShowCreateForm}
          newGroupForm={newGroupForm}
          setNewGroupForm={setNewGroupForm}
          createGroup={createGroup}
          operationInProgress={operationInProgress}
        />
      </div>
    </div>
  );
};

export default StreamsTabHeader;
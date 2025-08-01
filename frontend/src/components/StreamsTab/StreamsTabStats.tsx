// frontend/src/components/StreamsTab/StreamsTabStats.tsx

import React from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { Users, Monitor, Play } from "lucide-react";
import type { Group, Client } from '../../types';

interface StreamsTabStatsProps {
  groups: Group[];
  streamingStatus: { [groupId: string]: boolean };
  clients: Client[];
}

const StreamsTabStats: React.FC<StreamsTabStatsProps> = ({
  groups,
  streamingStatus,
  clients
}) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          <div className="flex items-center">
            <div className="flex-1 p-6">
              <div className="flex items-center">
                <div className="flex-1">
                  <p className="text-sm font-medium text-muted-foreground">Total Groups</p>
                  <p className="text-2xl font-bold">{groups.length}</p>
                </div>
                <div className="ml-4 rounded-full bg-blue-100 p-3">
                  <Monitor className="h-6 w-6 text-blue-600" />
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <CardContent className="p-0">
          <div className="flex items-center">
            <div className="flex-1 p-6">
              <div className="flex items-center">
                <div className="flex-1">
                  <p className="text-sm font-medium text-muted-foreground">Active Streams</p>
                  <p className="text-2xl font-bold">
                    {Object.values(streamingStatus).filter(Boolean).length}
                  </p>
                </div>
                <div className="ml-4 rounded-full bg-green-100 p-3">
                  <Play className="h-6 w-6 text-green-600" />
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <CardContent className="p-0">
          <div className="flex items-center">
            <div className="flex-1 p-6">
              <div className="flex items-center">
                <div className="flex-1">
                  <p className="text-sm font-medium text-muted-foreground">Connected Clients</p>
                  <p className="text-2xl font-bold">{clients.filter(c => c.status === 'active').length}</p>
                </div>
                <div className="ml-4 rounded-full bg-purple-100 p-3">
                  <Users className="h-6 w-6 text-purple-600" />
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default StreamsTabStats;
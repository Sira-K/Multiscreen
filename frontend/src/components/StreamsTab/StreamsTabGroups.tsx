// frontend/src/components/StreamsTab/StreamsTabGroups.tsx - Updated with Screen Assignment

import React from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import GroupCard from '../ui/GroupCard/GroupCard';
import { Plus, Monitor } from "lucide-react";
import type { Group, Video, Client } from '../../types';

interface StreamsTabGroupsProps {
  groups: Group[];
  videos: Video[];
  clients: Client[];
  streamingStatus: { [groupId: string]: boolean };
  operationInProgress: string | null;
  getUnassignedClients: () => Client[];
  getClientsForGroup: (groupId: string) => Client[];
  handleAssignClient: (clientId: string, groupId: string) => Promise<void>;

  //  Screen assignment functions
  getClientsWithScreenAssignments: (groupId: string) => {
    allGroupClients: Client[];
    assignedToScreens: Client[];
    unassignedToScreens: Client[];
  };
  handleAssignClientToScreen: (clientId: string, groupId: string, screenNumber: number) => Promise<void>;
  handleUnassignClientFromScreen: (clientId: string) => Promise<void>;
  handleAutoAssignScreens: (groupId: string) => Promise<void>;
  getScreenAssignments: (groupId: string) => Promise<any>;

  deleteGroup: (groupId: string, groupName: string) => Promise<void>;
  handleStreamingStatusChange: (groupId: string, isStreaming: boolean) => void;
  refreshData: () => Promise<void>;
  setShowCreateForm: (show: boolean) => void;
}

const StreamsTabGroups: React.FC<StreamsTabGroupsProps> = ({
  groups,
  videos,
  clients,
  streamingStatus,
  operationInProgress,
  getUnassignedClients,
  getClientsForGroup,
  handleAssignClient,

  //  Screen assignment functions
  getClientsWithScreenAssignments,
  handleAssignClientToScreen,
  handleUnassignClientFromScreen,
  handleAutoAssignScreens,
  getScreenAssignments,

  deleteGroup,
  handleStreamingStatusChange,
  refreshData,
  setShowCreateForm
}) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800">Active Groups</h3>

        {/* Debug Info - Show client counts */}
        <div className="text-sm text-gray-500">
          Total clients: {clients.length} | Unassigned: {getUnassignedClients().length}
        </div>
      </div>

      {groups.length === 0 ? (
        <Card className="p-0">
          <CardContent className="text-center py-12 px-6" style={{ paddingTop: '48px' }}>
            <Monitor className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-800 mb-2">No Groups Found</h3>
            <p className="text-gray-600 mb-6">
              No Docker containers with multi-screen labels were discovered.
              Create your first group to get started with multi-screen streaming.
            </p>
            <Button onClick={() => setShowCreateForm(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Your First Group
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6">
          {groups.map((group) => {
            const rawGroupStreamingStatus = streamingStatus[group.id];

            // IMPORTANT: Ensure we always pass a boolean
            let isStreamingBoolean = false;
            if (typeof rawGroupStreamingStatus === 'boolean') {
              isStreamingBoolean = rawGroupStreamingStatus;
            } else if (typeof rawGroupStreamingStatus === 'object' && rawGroupStreamingStatus !== null) {
              // Type assertion to handle API response objects
              isStreamingBoolean = (rawGroupStreamingStatus as any).is_streaming || false;
            }

            // Calculate clients for this specific rendering
            const groupClients = getClientsForGroup(group.id);
            const unassignedClients = getUnassignedClients();

            //  Get screen assignment information
            const screenAssignmentInfo = getClientsWithScreenAssignments(group.id);

            console.log(` RENDERING GROUP ${group.name}:`, {
              groupId: group.id,
              groupClientsCount: groupClients.length,
              unassignedClientsCount: unassignedClients.length,
              clientsAssignedToScreens: screenAssignmentInfo.assignedToScreens.length,
              clientsUnassignedToScreens: screenAssignmentInfo.unassignedToScreens.length,
              totalClientsInState: clients.length,
              isStreamingBoolean: isStreamingBoolean
            });

            return (
              <GroupCard
                key={group.id}
                group={group}
                videos={videos}
                clients={groupClients}                    //  Only clients assigned to this group
                unassignedClients={unassignedClients}     //  All unassigned clients
                isStreaming={isStreamingBoolean}
                onDelete={deleteGroup}
                onStreamingStatusChange={handleStreamingStatusChange}
                onRefresh={refreshData}
                onAssignClient={handleAssignClient}       //  Group assignment handler

                //  Screen assignment props
                onAssignClientToScreen={handleAssignClientToScreen}
                onUnassignClientFromScreen={handleUnassignClientFromScreen}
                onAutoAssignScreens={handleAutoAssignScreens}
                getScreenAssignments={getScreenAssignments}
                screenAssignmentInfo={screenAssignmentInfo}
              />
            );
          })}
        </div>
      )}
    </div>
  );
};

export default StreamsTabGroups;
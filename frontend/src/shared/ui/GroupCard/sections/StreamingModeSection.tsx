// frontend/src/components/ui/GroupCard/sections/StreamingModeSection.tsx

import React, { useState } from 'react';
import { Button } from '../../button';
import { Badge } from '../../badge';
import { Settings, Info, MoreVertical, Copy, VideoIcon } from 'lucide-react';
import { Group } from '../../../../types';
import { VideoAssignment } from '../types';

interface StreamingModeSectionProps {
  group: Group;
  localIsStreaming: boolean;
  videoAssignments: VideoAssignment[];
  selectedVideoFile: string;
  hasCompleteAssignments: boolean;
  setShowVideoConfig: (show: boolean) => void;
}

const StreamingModeSection: React.FC<StreamingModeSectionProps> = ({
  group,
  localIsStreaming,
  videoAssignments,
  selectedVideoFile,
  hasCompleteAssignments,
  setShowVideoConfig
}) => {
  const [showStreamingModeDropdown, setShowStreamingModeDropdown] = useState(false);

  const getStreamingModeIcon = () => {
    switch (group.streaming_mode) {
      case 'single_video_split':
        return <Copy className="w-4 h-4 text-blue-600" />;
      case 'multi_video':
        return <VideoIcon className="w-4 h-4 text-purple-600" />;
      default:
        return <VideoIcon className="w-4 h-4 text-gray-600" />;
    }
  };

  const getStreamingModeDescription = () => {
    const mode = group.streaming_mode || 'multi_video';

    if (mode === 'multi_video') {
      return {
        title: "Multi-Video Mode",
        description: "Each screen displays different content. You must assign a separate video file to each screen before streaming can begin.",
        requirements: [
          `Assign ${group.screen_count} different video files`,
          "One video per screen",
          "Each screen shows unique content"
        ],
        canStart: hasCompleteAssignments
      };
    } else {
      return {
        title: "Single Video Split Mode",
        description: "One video is automatically divided into equal sections across all screens. You must assign one video file to the group.",
        requirements: [
          "Assign 1 video file to the group",
          `Video split into ${group.screen_count} equal sections`,
          "All screens show synchronized content"
        ],
        canStart: selectedVideoFile !== ''
      };
    }
  };

  return (
    <>
      {/* Dropdown overlay */}
      {showStreamingModeDropdown && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowStreamingModeDropdown(false)}
        />
      )}

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700">Streaming Configuration</label>
          <div className="relative">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowStreamingModeDropdown(!showStreamingModeDropdown)}
              className="h-6 w-6 p-0"
            >
              <MoreVertical className="h-3 w-3" />
            </Button>

            {showStreamingModeDropdown && (
              <div className="absolute right-0 top-full mt-1 z-50 bg-white border border-gray-200 rounded-lg shadow-lg min-w-80 p-4">
                <div className="space-y-3">
                  {/* Header */}
                  <div className="flex items-center gap-2 pb-2 border-b">
                    <Settings className="w-4 h-4 text-blue-600" />
                    <h5 className="font-medium text-gray-900">Streaming Configuration</h5>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowStreamingModeDropdown(false)}
                      className="ml-auto h-5 w-5 p-0"
                    >

                    </Button>
                  </div>

                  {/* Current Mode Info */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      {getStreamingModeIcon()}
                      <span className="font-medium">{getStreamingModeDescription().title}</span>
                      {localIsStreaming && (
                        <div className="flex items-center gap-1">
                          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                          <span className="text-xs text-green-600 font-medium">Active</span>
                        </div>
                      )}
                    </div>

                    <p className="text-sm text-gray-600">
                      {getStreamingModeDescription().description}
                    </p>
                  </div>

                  {/* Requirements */}
                  <div className="space-y-2">
                    <h6 className="text-sm font-medium text-gray-700 flex items-center gap-1">
                      <Info className="w-3 h-3" />
                      Requirements
                    </h6>
                    <ul className="text-xs text-gray-600 space-y-1">
                      {getStreamingModeDescription().requirements.map((req, index) => (
                        <li key={index} className="flex items-start gap-2">
                          <span className="text-blue-600"></span>
                          <span>{req}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Status */}
                  <div className={`p-2 rounded text-sm ${getStreamingModeDescription().canStart
                      ? 'bg-green-50 border border-green-200 text-green-800'
                      : 'bg-yellow-50 border border-yellow-200 text-yellow-800'
                    }`}>
                    {getStreamingModeDescription().canStart ? (
                      <div className="flex items-center gap-2">
                        <span className="text-green-600"></span>
                        Ready to start streaming
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span className="text-yellow-600"></span>
                        {group.streaming_mode === 'multi_video'
                          ? `Need ${group.screen_count - videoAssignments.filter(a => a.file).length} more video assignments`
                          : 'Need to select a video file'}
                      </div>
                    )}
                  </div>

                  {/* Quick Actions */}
                  {!localIsStreaming && (
                    <div className="pt-2 border-t space-y-2">
                      <h6 className="text-sm font-medium text-gray-700">Quick Actions</h6>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setShowStreamingModeDropdown(false);
                          setShowVideoConfig(true);
                        }}
                        className="w-full text-xs"
                      >
                        {group.streaming_mode === 'multi_video'
                          ? 'Configure Video Assignments'
                          : 'Select Video File'}
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 text-sm">
          {getStreamingModeIcon()}
          <span>{group.streaming_mode === 'multi_video' ? 'Multi-Video Mode' : 'Single Video Split Mode'}</span>
        </div>
      </div>
    </>
  );
};

export default StreamingModeSection;
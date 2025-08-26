// frontend/src/components/ui/GroupCard/sections/VideoConfigurationSection.tsx

import React from 'react';
import { Button } from '../../button';
import { Badge } from '../../badge';
import { Label } from '../../label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../select';
import { Video, Copy, RotateCcw, ChevronUp, ChevronDown } from 'lucide-react';
import { Group, Video as VideoType } from '@/types';
import { VideoAssignment } from '../types';

interface VideoConfigurationSectionProps {
  group: Group;
  videos: VideoType[];
  videoAssignments: VideoAssignment[];
  selectedVideoFile: string;
  showVideoConfig: boolean;
  setShowVideoConfig: (show: boolean) => void;
  setSelectedVideoFile: (file: string) => void;
  handleVideoAssignmentChange: (screenIndex: number, fileName: string) => void;
  resetVideoAssignments: () => void;
  hasAnyAssignments: boolean;
  hasCompleteAssignments: boolean;
}

const VideoConfigurationSection: React.FC<VideoConfigurationSectionProps> = ({
  group,
  videos,
  videoAssignments,
  selectedVideoFile,
  showVideoConfig,
  setShowVideoConfig,
  setSelectedVideoFile,
  handleVideoAssignmentChange,
  resetVideoAssignments,
  hasAnyAssignments,
  hasCompleteAssignments
}) => {
  if (group.streaming_mode === 'multi_video') {
    return (
      <div className="border rounded-lg overflow-hidden">
        <div
          className="bg-gray-50 px-3 py-2 flex items-center justify-between cursor-pointer hover:bg-gray-100 transition-colors"
          onClick={() => setShowVideoConfig(!showVideoConfig)}
        >
          <div className="flex items-center gap-2">
            <Video className="w-4 h-4 text-gray-600" />
            <h4 className="text-sm font-medium text-gray-700">Video Assignments</h4>
            {hasAnyAssignments && (
              <Badge variant="outline" className="text-green-600 border-green-300 text-xs">
                {videoAssignments.filter(a => a.file).length}/{group.screen_count}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            {hasAnyAssignments && (
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  resetVideoAssignments();
                }}
                className="h-6 w-6 p-0"
                title="Reset all assignments"
              >
                <RotateCcw className="h-3 w-3" />
              </Button>
            )}
            {showVideoConfig ? (
              <ChevronUp className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            )}
          </div>
        </div>

        {showVideoConfig && (
          <div className="p-3 border-t bg-white space-y-3">
            <div className="text-xs text-gray-600">
              Assign one video file to each screen. Each screen will display its assigned video.
            </div>

            <div className="grid gap-2">
              {videoAssignments.map((assignment, index) => (
                <div key={index} className="flex items-center gap-2">
                  <Label className="w-16 text-xs">Screen {index + 1}:</Label>
                  <Select
                    value={assignment.file || ""}
                    onValueChange={(value) => handleVideoAssignmentChange(index, value)}
                  >
                    <SelectTrigger className="flex-1 h-8 text-xs">
                      <SelectValue placeholder="Select video..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__CLEAR__">
                        <span className="text-gray-400">Clear assignment</span>
                      </SelectItem>
                      {videos.map((video) => (
                        <SelectItem key={video.name} value={video.name}>
                          {video.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ))}
            </div>

            <div className="text-xs text-gray-500">
              Layout: {group.screen_count} screens in {group.orientation} orientation
            </div>

            {hasAnyAssignments && (
              <div className="bg-green-50 border border-green-200 rounded p-2">
                <div className="text-xs text-green-800 font-medium">
                  {videoAssignments.filter(a => a.file).length} of {group.screen_count} screens configured
                </div>
                {!hasCompleteAssignments && (
                  <div className="text-xs text-green-600 mt-1">
                    {group.screen_count - videoAssignments.filter(a => a.file).length} screens still need video assignments
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  // Single Video Split Mode
  return (
    <div className="border rounded-lg overflow-hidden">
      <div
        className="bg-gray-50 px-3 py-2 flex items-center justify-between cursor-pointer hover:bg-gray-100 transition-colors"
        onClick={() => setShowVideoConfig(!showVideoConfig)}
      >
        <div className="flex items-center gap-2">
          <Copy className="w-4 h-4 text-gray-600" />
          <h4 className="text-sm font-medium text-gray-700">Video Selection</h4>
          {selectedVideoFile && (
            <Badge variant="outline" className="text-green-600 border-green-300 text-xs">
              Selected
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {selectedVideoFile && (
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedVideoFile('');
              }}
              className="h-6 w-6 p-0"
              title="Clear selection"
            >
              <RotateCcw className="h-3 w-3" />
            </Button>
          )}
          {showVideoConfig ? (
            <ChevronUp className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          )}
        </div>
      </div>

      {showVideoConfig && (
        <div className="p-3 border-t bg-white space-y-3">
          <div className="text-xs text-gray-600">
            Select one video file that will be automatically split into {group.screen_count} equal sections
            and distributed {group.orientation === 'horizontal' ? 'side-by-side' : 'top-to-bottom'} across all screens.
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-medium">Video File:</Label>
            <Select
              value={selectedVideoFile || ""}
              onValueChange={setSelectedVideoFile}
            >
              <SelectTrigger className="h-8 text-sm">
                <SelectValue placeholder="Select video file to split" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__CLEAR__">
                  <span className="text-gray-400">Clear selection</span>
                </SelectItem>
                {videos.map((video) => (
                  <SelectItem key={video.name} value={video.name}>
                    {video.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedVideoFile && (
            <div className="bg-blue-50 p-2 rounded border-l-4 border-blue-400">
              <p className="text-xs text-blue-800">
                <strong>{selectedVideoFile}</strong> will be automatically cropped into {group.screen_count} equal {group.orientation} sections.
                Each client will receive their designated section.
              </p>
            </div>
          )}

          {selectedVideoFile && (
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedVideoFile('')}
                className="text-xs"
              >
                Clear Selection
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default VideoConfigurationSection;
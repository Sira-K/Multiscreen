// frontend/src/components/ui/GroupCard/StreamingDialogs.tsx

import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from '../button';
import { Label } from '../label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../select';
import { Group, Video as VideoType } from '../../../types';
import { VideoAssignment } from './types';

interface StreamingDialogsProps {
  group: Group;
  videos: VideoType[];
  videoAssignments: VideoAssignment[];
  selectedVideoFile: string;
  setSelectedVideoFile: (file: string) => void;
  handleVideoAssignmentChange: (screenIndex: number, fileName: string) => void;
  showMultiVideoDialog: boolean;
  setShowMultiVideoDialog: (show: boolean) => void;
  showSingleVideoDialog: boolean;
  setShowSingleVideoDialog: (show: boolean) => void;
  handleStartMultiVideo: () => void;
  handleStartSingleVideoSplit: () => void;
  isStartingMultiVideo: boolean;
  isStartingSingleVideo: boolean;
}

const StreamingDialogs: React.FC<StreamingDialogsProps> = ({
  group,
  videos,
  videoAssignments,
  selectedVideoFile,
  setSelectedVideoFile,
  handleVideoAssignmentChange,
  showMultiVideoDialog,
  setShowMultiVideoDialog,
  showSingleVideoDialog,
  setShowSingleVideoDialog,
  handleStartMultiVideo,
  handleStartSingleVideoSplit,
  isStartingMultiVideo,
  isStartingSingleVideo
}) => {
  return (
    <>
      {/* Multi-Video Dialog - fallback for incomplete assignments */}
      {showMultiVideoDialog && group.streaming_mode === 'multi_video' && (
        <Dialog open={showMultiVideoDialog} onOpenChange={setShowMultiVideoDialog}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Configure Multi-Video Streaming</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Assign a different video to each screen. Each client will display different content.
              </p>
              
              <div className="space-y-3">
                {videoAssignments.map((assignment, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <div className="w-20 text-sm font-medium">
                      Screen {index + 1}:
                    </div>
                    <Select
                      value={assignment.file || ""}
                      onValueChange={(value) => handleVideoAssignmentChange(index, value)}
                    >
                      <SelectTrigger className="flex-1">
                        <SelectValue placeholder="Select video file" />
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
              
              <div className="flex justify-end gap-2">
                <Button
                  onClick={handleStartMultiVideo}
                  disabled={isStartingMultiVideo || videoAssignments.filter(a => a.file).length !== group.screen_count}
                >
                  {isStartingMultiVideo ? 'Starting...' : 'Start Multi-Video'}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setShowMultiVideoDialog(false)}
                  disabled={isStartingMultiVideo}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Simplified Single Video Split Dialog - only for video selection */}
      {showSingleVideoDialog && group.streaming_mode === 'single_video_split' && (
        <Dialog open={showSingleVideoDialog} onOpenChange={setShowSingleVideoDialog}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Select Video for Split Mode</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Select one video that will be automatically split into {group.screen_count} sections 
                and distributed {group.orientation === 'horizontal' ? 'side-by-side' : 'top-to-bottom'} 
                across all screens.
              </p>
              
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
              
              <div className="flex justify-end gap-2">
                {selectedVideoFile && (
                  <Button
                    onClick={() => {
                      setShowSingleVideoDialog(false);
                      handleStartSingleVideoSplit();
                    }}
                    disabled={isStartingSingleVideo}
                    size="sm"
                  >
                    {isStartingSingleVideo ? 'Starting...' : 'Start Split Video'}
                  </Button>
                )}
                <Button
                  variant="outline"
                  onClick={() => setShowSingleVideoDialog(false)}
                  disabled={isStartingSingleVideo}
                  size="sm"
                >
                  Cancel
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
};

export default StreamingDialogs;
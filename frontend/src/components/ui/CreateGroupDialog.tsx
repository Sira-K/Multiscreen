// frontend/src/components/CreateGroupDialog.tsx

import React from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Monitor, VideoIcon, Copy } from "lucide-react";

interface GroupFormState {
  name: string;
  description: string;
  screen_count: number;
  orientation: 'horizontal' | 'vertical' | 'grid';
  streaming_mode: 'multi_video' | 'single_video_split';
}

interface CreateGroupDialogProps {
  showCreateForm: boolean;
  setShowCreateForm: (show: boolean) => void;
  newGroupForm: GroupFormState;
  setNewGroupForm: React.Dispatch<React.SetStateAction<GroupFormState>>;
  createGroup: () => void;
  operationInProgress: string | null;
}

const CreateGroupDialog: React.FC<CreateGroupDialogProps> = ({
  showCreateForm,
  setShowCreateForm,
  newGroupForm,
  setNewGroupForm,
  createGroup,
  operationInProgress
}) => {
  return (
    <Dialog open={showCreateForm} onOpenChange={setShowCreateForm}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Create Group
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-none w-[98vw] h-[95vh] max-h-[95vh] overflow-hidden flex flex-col">
        <DialogHeader className="flex-shrink-0 px-6 pt-6 pb-4 border-b">
          <DialogTitle>Create New Streaming Group</DialogTitle>
          <DialogDescription>
            Set up a new multi-screen streaming group with Docker container management.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-auto px-6 py-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-full">
            {/* Left Column */}
            <div className="space-y-6">
              {/* Basic Info */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Basic Information</h3>
                <div>
                  <Label htmlFor="group-name" className="text-base">Group Name *</Label>
                  <Input
                    id="group-name"
                    placeholder="Enter group name"
                    value={newGroupForm.name}
                    onChange={(e) => setNewGroupForm(prev => ({ ...prev, name: e.target.value }))}
                    className="mt-2 text-base h-12"
                  />
                </div>

                <div>
                  <Label htmlFor="group-description" className="text-base">Description (Optional)</Label>
                  <Input
                    id="group-description"
                    placeholder="Enter group description"
                    value={newGroupForm.description}
                    onChange={(e) => setNewGroupForm(prev => ({ ...prev, description: e.target.value }))}
                    className="mt-2 text-base h-12"
                  />
                </div>
              </div>

              {/* Screen Configuration */}
              <div className="space-y-4 border-t pt-6">
                <h3 className="text-lg font-semibold">Screen Configuration</h3>

                <div>
                  <Label htmlFor="screen-count" className="text-base">Number of Screens</Label>
                  <Select
                    value={newGroupForm.screen_count.toString()}
                    onValueChange={(value) => setNewGroupForm(prev => ({ ...prev, screen_count: parseInt(value) }))}
                  >
                    <SelectTrigger className="mt-2 h-12 text-base">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {[2, 3, 4, 5, 6, 8, 9, 10, 12].map(count => (
                        <SelectItem key={count} value={count.toString()}>
                          {count} screens
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="orientation" className="text-base">Screen Orientation</Label>
                  <Select
                    value={newGroupForm.orientation}
                    onValueChange={(value: 'horizontal' | 'vertical' | 'grid') =>
                      setNewGroupForm(prev => ({ ...prev, orientation: value }))
                    }
                  >
                    <SelectTrigger className="mt-2 h-12 text-base">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="horizontal">
                        <div className="flex items-center gap-2">
                          <Monitor className="w-5 h-5" />
                          Horizontal (side-by-side)
                        </div>
                      </SelectItem>
                      <SelectItem value="vertical">
                        <div className="flex items-center gap-2">
                          <Monitor className="w-5 h-5 rotate-90" />
                          Vertical (top-bottom)
                        </div>
                      </SelectItem>
                      <SelectItem value="grid">
                        <div className="flex items-center gap-2">
                          <Monitor className="w-5 h-5" />
                          Grid Layout
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* Right Column */}
            <div className="space-y-6">
              {/* Streaming Mode */}
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold">Streaming Mode</h3>
                  <p className="text-base text-gray-600 mt-1">
                    Choose how video content will be distributed across screens
                  </p>
                </div>

                <div className="space-y-4">
                  {/* Multi-Video Mode */}
                  <div
                    className={`p-6 border-2 rounded-xl cursor-pointer transition-all ${newGroupForm.streaming_mode === 'multi_video'
                      ? 'border-blue-500 bg-blue-50 shadow-md'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    onClick={() => setNewGroupForm(prev => ({ ...prev, streaming_mode: 'multi_video' }))}
                  >
                    <div className="flex items-start gap-4">
                      <input
                        type="radio"
                        className="mt-1.5 w-4 h-4"
                        checked={newGroupForm.streaming_mode === 'multi_video'}
                        onChange={() => setNewGroupForm(prev => ({ ...prev, streaming_mode: 'multi_video' }))}
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-3 font-semibold text-gray-900 text-base">
                          <VideoIcon className="w-5 h-5" />
                          Multi-Video Mode
                        </div>
                        <p className="text-base text-gray-600 mt-2">
                          Each screen displays different video content. You'll assign a separate video file to each screen.
                        </p>
                        <div className="text-sm text-gray-500 mt-3 space-y-1">
                          <div> Different content per screen</div>
                          <div> Maximum flexibility</div>
                          <div> Independent video files</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Single Video Split Mode */}
                  <div
                    className={`p-6 border-2 rounded-xl cursor-pointer transition-all ${newGroupForm.streaming_mode === 'single_video_split'
                      ? 'border-blue-500 bg-blue-50 shadow-md'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    onClick={() => setNewGroupForm(prev => ({ ...prev, streaming_mode: 'single_video_split' }))}
                  >
                    <div className="flex items-start gap-4">
                      <input
                        type="radio"
                        className="mt-1.5 w-4 h-4"
                        checked={newGroupForm.streaming_mode === 'single_video_split'}
                        onChange={() => setNewGroupForm(prev => ({ ...prev, streaming_mode: 'single_video_split' }))}
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-3 font-semibold text-gray-900 text-base">
                          <Copy className="w-5 h-5" />
                          Single Video Split Mode
                        </div>
                        <p className="text-base text-gray-600 mt-2">
                          One video is automatically divided into {newGroupForm.screen_count} equal sections across all screens.
                        </p>
                        <div className="text-sm text-gray-500 mt-3 space-y-1">
                          <div> Single video source</div>
                          <div> Automatic {newGroupForm.orientation} division</div>
                          <div> Synchronized playback</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Configuration Preview */}
              <div className="bg-gray-50 p-6 rounded-xl border-t-4 border-blue-200">
                <h4 className="font-semibold mb-3 text-gray-900 text-base">Configuration Preview</h4>
                <div className="text-base text-gray-600 space-y-2">
                  <div> {newGroupForm.screen_count} screens in {newGroupForm.orientation} layout</div>
                  <div>
                    {newGroupForm.streaming_mode === 'multi_video'
                      ? `${newGroupForm.screen_count} different videos (one per screen)`
                      : `1 video split into ${newGroupForm.screen_count} sections`}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter className="flex-shrink-0 px-6 py-4 border-t bg-gray-50">"
          <Button variant="outline" size="lg" onClick={() => setShowCreateForm(false)} className="text-base px-8">
            Cancel
          </Button>
          <Button
            size="lg"
            onClick={createGroup}
            disabled={operationInProgress === 'create' || !newGroupForm.name.trim()}
            className="text-base px-8"
          >
            {operationInProgress === 'create' ? 'Creating...' : 'Create Group'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default CreateGroupDialog;
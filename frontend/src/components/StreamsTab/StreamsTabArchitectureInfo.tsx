// frontend/src/components/StreamsTab/StreamsTabArchitectureInfo.tsx

import React from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { CheckCircle } from "lucide-react";

const StreamsTabArchitectureInfo: React.FC = () => {
  return (
    <Card className="bg-blue-50 border border-blue-200">
      <CardContent className="p-6">
        <div className="flex items-center gap-2 text-blue-800 mb-2">
          <CheckCircle className="h-4 w-4" />
          <span className="font-medium">Hybrid Architecture Active</span>
        </div>
        <p className="text-sm text-blue-700">
          Groups are managed through Docker discovery. Clients are tracked in real-time app state.
          Multi-video streaming supports different videos per screen with persistent assignments.
        </p>
      </CardContent>
    </Card>
  );
};

export default StreamsTabArchitectureInfo;
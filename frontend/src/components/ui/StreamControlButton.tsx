import { Button } from "@/components/ui/button";
import { Play, Square, Loader2, Wifi, WifiOff } from "lucide-react";

interface FlaskStreamControlButtonProps {
  streamId: string;
  streamName: string;
  isActive: boolean;
  onToggle: (streamId: string) => void;
  size?: "default" | "sm" | "lg" | "icon";
  className?: string;
  // Flask WebSocket props
  startStream: (streamId: string) => boolean;
  stopStream: (streamId: string) => boolean;
  isLoading: boolean;
  isConnected: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  // Optional group information for Flask backend
  groupId?: string;
  groupName?: string;
}

const FlaskStreamControlButton = ({
  streamId,
  streamName,
  isActive,
  onToggle,
  size = "sm",
  className = "",
  startStream,
  stopStream,
  isLoading,
  isConnected,
  connectionStatus,
  groupId,
  groupName
}: FlaskStreamControlButtonProps) => {

  const handleClick = async () => {
    // Use groupId if available, otherwise use streamId
    const targetId = groupId || streamId;
    const success = isActive ? stopStream(targetId) : startStream(targetId);
    
    // Only update local state if WebSocket command was sent successfully
    // The actual state update will come from the WebSocket response
    if (success) {
      // Optimistic update - will be corrected by WebSocket if needed
      onToggle(streamId);
    }
  };

  const getConnectionIndicator = () => {
    switch (connectionStatus) {
      case 'connected':
        return <Wifi className="w-3 h-3 text-green-500" />;
      case 'connecting':
        return <Loader2 className="w-3 h-3 text-yellow-500 animate-spin" />;
      case 'disconnected':
      case 'error':
        return <WifiOff className="w-3 h-3 text-red-500" />;
    }
  };

  const isDisabled = isLoading || !isConnected || connectionStatus === 'error';

  const displayName = groupName || streamName;
  const actionText = isActive ? 'Stop' : 'Start';

  return (
    <div className="flex items-center gap-1">
      {/* Connection Status Indicator */}
      <div className="flex items-center" title={`Connection: ${connectionStatus}`}>
        {getConnectionIndicator()}
      </div>
      
      {/* Main Control Button */}
      <Button
        size={size}
        variant={isActive ? 'destructive' : 'default'}
        onClick={handleClick}
        disabled={isDisabled}
        className={`${isActive 
          ? 'bg-red-600 hover:bg-red-700 text-white' 
          : 'bg-green-600 hover:bg-green-700 text-white'
        } ${isDisabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}
        title={
          !isConnected 
            ? `Cannot control stream - ${connectionStatus}` 
            : `${actionText} ${displayName}`
        }
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          isActive ? <Square className="w-4 h-4" /> : <Play className="w-4 h-4" />
        )}
      </Button>
    </div>
  );
};

export default FlaskStreamControlButton;
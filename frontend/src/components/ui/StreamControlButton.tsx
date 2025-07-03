import { Button } from "@/components/ui/button";
import { Play, Square } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface StreamControlButtonProps {
  streamId: string;
  streamName: string;
  isActive: boolean;
  onToggle: (streamId: string) => void;
  size?: "default" | "sm" | "lg" | "icon";
  className?: string;
}

const StreamControlButton = ({
  streamId,
  streamName,
  isActive,
  onToggle,
  size = "sm",
  className = ""
}: StreamControlButtonProps) => {
  const { toast } = useToast();

  const handleClick = () => {
    onToggle(streamId);
    
    // Show toast notification
    toast({
      title: isActive ? "Stream Stopped" : "Stream Started",
      description: `${streamName} is now ${isActive ? 'inactive' : 'active'}`
    });
  };

  return (
    <Button
      size={size}
      variant={isActive ? 'destructive' : 'default'}
      onClick={handleClick}
      className={`${isActive 
        ? 'bg-red-600 hover:bg-red-700 text-white' 
        : 'bg-green-600 hover:bg-green-700 text-white'
      } ${className}`}
      title={isActive ? `Stop ${streamName}` : `Start ${streamName}`}
    >
      {isActive ? <Square className="w-4 h-4" /> : <Play className="w-4 h-4" />}
    </Button>
  );
};

export default StreamControlButton;
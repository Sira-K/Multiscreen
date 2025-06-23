import React from 'react';

interface StopAllDockerProps {
  setOutput: (msg: string) => void;
}

const StopAllDocker: React.FC<StopAllDockerProps> = ({ setOutput }) => {
  const handleStopAll = async () => {
    try {
      setOutput("🔄 Stopping all Docker containers...");
      
      const apiUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/stop_all_docker`;
      const res = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      
      const data = await res.json();
      
      if (res.ok) {
        if (data.stopped_containers && data.stopped_containers.length > 0) {
          const stoppedCount = data.stopped_containers.length;
          const containerIds = data.stopped_containers.join(', ');
          setOutput(`🛑 Stopped ${stoppedCount} Docker containers: ${containerIds}`);
        } else {
          setOutput("No running Docker containers found.");
        }
        
        // Add information about failed containers if any
        if (data.failed_containers && data.failed_containers.length > 0) {
          const failedInfo = data.failed_containers
            .map((container: any) => `${container.id}: ${container.error}`)
            .join('\n');
          
          setOutput(`🛑 Stopped some containers, but failed on others:\n${failedInfo}`);
        }
      } else {
        setOutput(`❌ Failed to stop all Docker containers: ${data.error}`);
      }
    } catch (err) {
      setOutput("❌ Failed to connect to backend for stopping all Docker containers.");
    }
  };
  
  return <button onClick={handleStopAll}>Stop All Docker</button>;
};

export default StopAllDocker;
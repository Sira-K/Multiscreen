import React from 'react';

interface StopDockerProps {
  setOutput: (msg: string) => void;
  containerId: string | null;
}

const StopDocker: React.FC<StopDockerProps> = ({ setOutput, containerId }) => {
  const handleStop = async () => {
    if (!containerId) {
      setOutput("⚠️ No container ID available. Please start Docker first.");
      return;
    }

    try {
      const apiUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/stop_docker`;
      const res = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ container_id: containerId }),
      });

      const data = await res.json();

      if (res.ok) {
        setOutput(`🛑 Docker stopped: ${data.message}`);
      } else {
        setOutput(`❌ Docker stop failed: ${data.error}`);
      }
    } catch (err) {
      setOutput("❌ Failed to connect to backend for Docker stop.");
    }
  };

  return <button onClick={handleStop}>Stop Docker</button>;
};

export default StopDocker;

import React from 'react';

interface StartDockerProps {
  setOutput: (msg: string) => void;
  setContainerId: (id: string) => void;
}

const StartDocker: React.FC<StartDockerProps> = ({ setOutput, setContainerId }) => {
  const handleStart = async () => {
    try {
      const apiUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/start_docker`;
      const res = await fetch(apiUrl, { method: "POST" });
      const data = await res.json();

      if (res.ok) {
        setOutput(`✅ Docker started. ${data.message || ''}`);
        if (data.container_id) setContainerId(data.container_id);
      } else {
        setOutput(`❌ Docker start failed: ${data.error}`);
      }
    } catch (err) {
      setOutput("❌ Failed to connect to backend for Docker start.");
    }
  };

  return <button onClick={handleStart}>Start Docker</button>;
};

export default StartDocker;

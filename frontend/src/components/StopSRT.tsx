import React from 'react';

const StopSRT: React.FC<{ setOutput: (msg: string) => void }> = ({ setOutput }) => {
  const handleStop = async () => {
    try {
      setOutput("Stopping SRT stream...");
      
      const apiUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/stop_srt`;
      const res = await fetch(apiUrl, { 
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({}) // Send empty JSON object
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setOutput(`🛑 SRT stopped. Process ${data.pid} terminated. ${data.message || ''}`);
      } else {
        setOutput(`❌ SRT stop failed: ${data.error}`);
      }
    } catch (err) {
      console.error("Error stopping SRT:", err);
      setOutput(`❌ Failed to connect to backend for SRT stop: ${err}`);
    }
  };

  return (
    <button 
      onClick={handleStop}
      className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
    >
      Stop SRT
    </button>
  );
};

export default StopSRT;
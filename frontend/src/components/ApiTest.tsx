import { useEffect, useState } from 'react';
import { systemApi } from '@/lib/api';

export const ApiTest = () => {
  const [status, setStatus] = useState('Testing...');
  
  useEffect(() => {
    const testConnection = async () => {
      try {
        const response = await systemApi.ping();
        setStatus(`✅ Connected! ${response.message}`);
      } catch (error) {
        setStatus(`❌ Connection failed: ${error.message}`);
      }
    };
    
    testConnection();
  }, []);
  
  return <div className="p-4 bg-blue-100 rounded">{status}</div>;
};
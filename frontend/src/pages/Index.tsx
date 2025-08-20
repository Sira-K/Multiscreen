import React, { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Monitor, Users, Video } from "lucide-react";
import StreamsTab from "@/components/StreamsTab/StreamsTab";
import ClientsTab from "@/components/ClientsTab";
import VideoFilesTab from "@/components/VideoFilesTab";

const STORAGE_KEY = 'activeTab';

const Index = () => {
  const [activeTab, setActiveTab] = useState<string>('streams');
  const [clientsRefreshed, setClientsRefreshed] = useState<number>(0);

  const getInitialTab = (): string => {
    try {
      const savedTab = localStorage.getItem(STORAGE_KEY);
      if (savedTab && ['streams', 'clients', 'videos'].includes(savedTab)) {
        return savedTab;
      }
    } catch (error) {
      console.warn('Failed to read tab from localStorage:', error);
    }
    return 'streams';
  };

  useEffect(() => {
    const initialTab = getInitialTab();
    setActiveTab(initialTab);
  }, []);

  const handleTabChange = (value: string) => {
    setActiveTab(value);
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch (error) {
      console.warn('Failed to save tab to localStorage:', error);
    }
  };

  const handleClientsRefreshed = () => {
    // Increment counter to trigger StreamsTab refresh
    setClientsRefreshed(prev => prev + 1);
    console.log('Clients refreshed, notifying StreamsTab to refresh...');
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Streaming Management System</h1>
          <p className="text-gray-600">Manage your streaming groups, clients, and video content</p>
        </div>

        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-8 bg-white border border-gray-200 shadow-sm">
            <TabsTrigger
              value="streams"
              className="flex items-center gap-2 data-[state=active]:bg-blue-600 data-[state=active]:text-white text-gray-700"
            >
              <Monitor className="w-4 h-4" />
              Streams
            </TabsTrigger>
            <TabsTrigger
              value="clients"
              className="flex items-center gap-2 data-[state=active]:bg-green-600 data-[state=active]:text-white text-gray-700"
            >
              <Users className="w-4 h-4" />
              Clients
            </TabsTrigger>
            <TabsTrigger
              value="videos"
              className="flex items-center gap-2 data-[state=active]:bg-purple-600 data-[state=active]:text-white text-gray-700"
            >
              <Video className="w-4 h-4" />
              Videos
            </TabsTrigger>
          </TabsList>

          <TabsContent value="streams">
            <StreamsTab clientsRefreshed={clientsRefreshed} />
          </TabsContent>
          <TabsContent value="clients">
            <ClientsTab onClientsRefreshed={handleClientsRefreshed} />
          </TabsContent>
          <TabsContent value="videos">
            <VideoFilesTab />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default Index;
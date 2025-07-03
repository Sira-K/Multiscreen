import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import StreamsTab from "@/components/StreamsTab";
import ClientsTab from "@/components/ClientsTab";
import VideoFilesTab from "@/components/VideoFilesTab";
import { Monitor, Users, Video } from "lucide-react";

interface Stream {
  id: string;
  name: string;
  url: string;
  port: number;
  status: 'active' | 'inactive';
  clients: string[];
}

interface Client {
  id: string;
  name: string;
  ip: string;
  status: 'active' | 'inactive';
  connectedStream: string | null;
  lastSeen: string;
  order: number;
}

const Index = () => {
  const [streams, setStreams] = useState<Stream[]>([]);
  const [clients, setClients] = useState<Client[]>([]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="container mx-auto px-6 py-8">
        <header className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">SRT Streaming Casdontrol Panel</h1>
          <p className="text-gray-600">Manage streams, clients, and video files for your digital signage system</p>
        </header>

        <Tabs defaultValue="streams" className="w-full">
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
              className="flex items-center gap-2 data-[state=active]:bg-blue-600 data-[state=active]:text-white text-gray-700"
            >
              <Users className="w-4 h-4" />
              Clients
            </TabsTrigger>
            <TabsTrigger 
              value="videos"
              className="flex items-center gap-2 data-[state=active]:bg-blue-600 data-[state=active]:text-white text-gray-700"
            >
              <Video className="w-4 h-4" />
              Video Files
            </TabsTrigger>
          </TabsList>

          <TabsContent value="streams" className="mt-0">
            <StreamsTab 
              streams={streams} 
              setStreams={setStreams}
              clients={clients}
            />
          </TabsContent>

          <TabsContent value="clients" className="mt-0">
            <ClientsTab 
              clients={clients} 
              setClients={setClients}
            />
          </TabsContent>

          <TabsContent value="videos" className="mt-0">
            <VideoFilesTab />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default Index;

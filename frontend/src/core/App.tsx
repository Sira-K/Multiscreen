import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { TooltipProvider } from '@/shared/ui/tooltip';
import { ErrorProvider } from "@/shared/ErrorSystem/ErrorContext";
import ErrorNotification from "@/shared/ErrorSystem/ErrorNotification";
import Index from '@/core/pages/Index';
import NotFound from '@/core/pages/NotFound';

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ErrorProvider>
      <TooltipProvider>
        <ErrorNotification />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </ErrorProvider>
  </QueryClientProvider>
);

export default App;

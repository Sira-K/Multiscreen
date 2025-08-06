import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 3000,
    watch: {
      usePolling: true,    // Poll for file changes instead of using file events
      interval: 100,       // Check every 100ms
    },
    hmr: {
      overlay: true,       // Show errors in browser overlay
    }
  },
  plugins: [
    react(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  envDir: './src',  // ← Tell Vite to look for .env files in src folder
}));
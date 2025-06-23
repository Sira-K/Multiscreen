// hooks/useVideoFetching.tsx
import { useState, useEffect, useCallback } from 'react';

// Global timestamp to track the last successful fetch across all components
let lastVideoFetchTimestamp = 0;
// Global cache to store the latest videos data
let videosCache: any[] = [];
// Flag to indicate if a fetch is in progress
let isFetchingInProgress = false;

// Minimum time between fetches (5 seconds)
const THROTTLE_INTERVAL = 5000;

/**
 * Custom hook for fetching and managing video files
 * with proper throttling to prevent excessive API calls
 */
export const useVideoFetching = () => {
  const [availableVideos, setAvailableVideos] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  /**
   * Throttled function to fetch videos from the server
   * Will not make a new request if:
   * 1. Another fetch is already in progress
   * 2. Less than 5 seconds have passed since the last successful fetch
   * 3. forceRefresh is false and we're just checking
   */
  const fetchVideos = useCallback(async (forceRefresh: boolean = false) => {
    try {
      // If we're just checking and not forcing a refresh
      if (!forceRefresh) {
        // Return cached videos if we have them and less than 5 seconds have passed
        const now = Date.now();
        if (now - lastVideoFetchTimestamp < THROTTLE_INTERVAL) {
          console.log('Using cached videos - throttled');
          // Still update the component state with the cached videos
          setAvailableVideos(videosCache);
          return videosCache;
        }
      }

      // Don't make a new request if one is already in progress
      if (isFetchingInProgress) {
        console.log('Skipping fetch - already in progress');
        return videosCache;
      }

      // Mark fetch as in progress and set loading state
      isFetchingInProgress = true;
      setLoading(true);

      console.log(`Fetching videos at ${new Date().toISOString()}`);
      const apiUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/get_videos`;
      
      const response = await fetch(apiUrl);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch videos: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      const videos = data.videos || [];
      
      // Update the global timestamp and cache
      lastVideoFetchTimestamp = Date.now();
      videosCache = videos;
      
      // Update component state
      setAvailableVideos(videos);
      return videos;
      
    } catch (error) {
      console.error('Error fetching videos:', error);
      return [];
    } finally {
      // Clear the in-progress flag and loading state
      isFetchingInProgress = false;
      setLoading(false);
    }
  }, []);

  // Initial fetch when the hook is first used
  useEffect(() => {
    fetchVideos(false);
    
    // Set up a polling interval (every 5 seconds)
    const interval = setInterval(() => {
      fetchVideos(false);
    }, THROTTLE_INTERVAL);
    
    // Clean up interval on unmount
    return () => clearInterval(interval);
  }, [fetchVideos]);

  /**
   * Force a refresh of the videos, bypassing the time-based throttle
   * but still respecting the in-progress flag to prevent duplicate requests
   */
  const forceRefreshVideos = useCallback(async () => {
    return fetchVideos(true);
  }, [fetchVideos]);

  return {
    availableVideos,
    loading,
    fetchVideos: forceRefreshVideos // Export only the force refresh function
  };
};

export default useVideoFetching;
// frontend/src/components/ui/GroupCard/hooks/useVideoAssignments.ts

import { useState, useEffect } from 'react';
import { VideoAssignment } from '../types';

// Helper function to get storage key for a group's video assignments
const getStorageKey = (groupId: string) => `video_assignments_${groupId}`;

// Helper function to save video assignments and selected video to localStorage
const saveVideoAssignments = (groupId: string, assignments: VideoAssignment[], selectedVideo?: string) => {
  try {
    const key = getStorageKey(groupId);
    const data = {
      assignments,
      selectedVideo: selectedVideo || '',
      timestamp: Date.now(),
      version: '1.0'
    };
    localStorage.setItem(key, JSON.stringify(data));
    console.log(`💾 Saved video assignments for group ${groupId}:`, assignments, 'selectedVideo:', selectedVideo);
  } catch (error) {
    console.warn('⚠️ Failed to save video assignments to localStorage:', error);
  }
};

// Helper function to load video assignments and selected video from localStorage
const loadVideoAssignments = (groupId: string, screenCount: number): { assignments: VideoAssignment[], selectedVideo: string } => {
  try {
    const key = getStorageKey(groupId);
    const stored = localStorage.getItem(key);
    
    if (stored) {
      const data = JSON.parse(stored);
      const assignments = data.assignments || [];
      const selectedVideo = data.selectedVideo || '';
      
      // Validate that we have the right number of screens and structure
      if (Array.isArray(assignments) && assignments.length === screenCount) {
        // Validate each assignment has the correct structure
        const validAssignments = assignments.every((assignment, index) => 
          assignment && 
          typeof assignment === 'object' && 
          assignment.screen === index &&
          typeof assignment.file === 'string'
        );
        
        if (validAssignments) {
          console.log(`📂 Loaded video assignments for group ${groupId}:`, assignments, 'selectedVideo:', selectedVideo);
          return { assignments, selectedVideo };
        }
      }
    }
  } catch (error) {
    console.warn('⚠️ Failed to load video assignments from localStorage:', error);
  }
  
  // Return empty assignments if loading failed or data is invalid
  return {
    assignments: Array.from({ length: screenCount }, (_, index) => ({
      screen: index,
      file: ""
    })),
    selectedVideo: ''
  };
};

export const useVideoAssignments = (groupId: string, screenCount: number) => {
  const [videoAssignments, setVideoAssignments] = useState<VideoAssignment[]>([]);
  const [showVideoConfig, setShowVideoConfig] = useState(false);
  const [selectedVideoFile, setSelectedVideoFile] = useState<string>('');

  // Load saved video assignments and selected video when group changes or component mounts
  useEffect(() => {
    const savedData = loadVideoAssignments(groupId, screenCount);
    setVideoAssignments(savedData.assignments);
    setSelectedVideoFile(savedData.selectedVideo);
    
    // Auto-expand video config if assignments exist
    const hasAssignments = savedData.assignments.some(assignment => assignment.file);
    setShowVideoConfig(hasAssignments);
  }, [groupId, screenCount]);

  // Handle video assignment change and save to localStorage
  const handleVideoAssignmentChange = (screenIndex: number, fileName: string) => {
    // Convert special clear value to empty string
    const actualFileName = fileName === "__CLEAR__" ? "" : fileName;
    
    const newAssignments = videoAssignments.map((assignment, index) => 
      index === screenIndex ? { ...assignment, file: actualFileName } : assignment
    );
    
    setVideoAssignments(newAssignments);
    
    // Save to localStorage immediately when user makes changes
    saveVideoAssignments(groupId, newAssignments, selectedVideoFile);
  };

  // Reset video assignments to empty
  const resetVideoAssignments = () => {
    const emptyAssignments: VideoAssignment[] = Array.from({ length: screenCount }, (_, index) => ({
      screen: index,
      file: ""
    }));
    setVideoAssignments(emptyAssignments);
    setSelectedVideoFile(''); // Also reset selected video
    saveVideoAssignments(groupId, emptyAssignments, '');
  };

  // Wrapper for setSelectedVideoFile that also saves to localStorage
  const setSelectedVideoFileAndSave = (fileName: string) => {
    setSelectedVideoFile(fileName);
    saveVideoAssignments(groupId, videoAssignments, fileName);
  };

  // Check if all screens have video assignments
  const hasCompleteAssignments = videoAssignments.every(assignment => assignment.file);
  
  // Check if any assignments exist
  const hasAnyAssignments = videoAssignments.some(assignment => assignment.file);

  return {
    videoAssignments,
    showVideoConfig,
    setShowVideoConfig,
    selectedVideoFile,
    setSelectedVideoFile: setSelectedVideoFileAndSave, // Use the wrapper that saves to localStorage
    handleVideoAssignmentChange,
    resetVideoAssignments,
    hasCompleteAssignments,
    hasAnyAssignments
  };
};
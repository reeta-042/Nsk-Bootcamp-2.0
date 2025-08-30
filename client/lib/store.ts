import { create } from 'zustand';
import { JourneyData } from '@shared/api';

export interface UserLocation {
  latitude: number;
  longitude: number;
  accuracy?: number;
}

interface JourneyStore {
  // Location state
  userLocation: UserLocation | null;
  locationError: string | null;
  locationLoading: boolean;
  
  // Journey state
  journeyData: JourneyData | null;
  isGeneratingJourney: boolean;
  journeyError: string | null;
  
  // UI state
  isJourneyCardVisible: boolean;
  searchQuery: string;
  
  // Upload state
  uploadedImages: File[];
  isUploading: boolean;
  uploadError: string | null;
  
  // Actions
  setUserLocation: (location: UserLocation | null) => void;
  setLocationError: (error: string | null) => void;
  setLocationLoading: (loading: boolean) => void;
  
  setJourneyData: (data: JourneyData | null) => void;
  setGeneratingJourney: (loading: boolean) => void;
  setJourneyError: (error: string | null) => void;
  
  setJourneyCardVisible: (visible: boolean) => void;
  setSearchQuery: (query: string) => void;
  
  addUploadedImage: (file: File) => void;
  removeUploadedImage: (index: number) => void;
  setUploading: (uploading: boolean) => void;
  setUploadError: (error: string | null) => void;
  clearUploadedImages: () => void;
  
  // Complex actions
  generateJourney: (query: string) => Promise<void>;
  uploadImage: (file: File) => Promise<void>;
  requestLocation: () => Promise<void>;
}

export const useJourneyStore = create<JourneyStore>((set, get) => ({
  // Initial state
  userLocation: null,
  locationError: null,
  locationLoading: false,
  
  journeyData: null,
  isGeneratingJourney: false,
  journeyError: null,
  
  isJourneyCardVisible: false,
  searchQuery: '',
  
  uploadedImages: [],
  isUploading: false,
  uploadError: null,
  
  // Basic setters
  setUserLocation: (location) => set({ userLocation: location }),
  setLocationError: (error) => set({ locationError: error }),
  setLocationLoading: (loading) => set({ locationLoading: loading }),
  
  setJourneyData: (data) => set({ journeyData: data }),
  setGeneratingJourney: (loading) => set({ isGeneratingJourney: loading }),
  setJourneyError: (error) => set({ journeyError: error }),
  
  setJourneyCardVisible: (visible) => set({ isJourneyCardVisible: visible }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  
  addUploadedImage: (file) => 
    set((state) => ({ uploadedImages: [...state.uploadedImages, file] })),
  removeUploadedImage: (index) =>
    set((state) => ({
      uploadedImages: state.uploadedImages.filter((_, i) => i !== index),
    })),
  setUploading: (uploading) => set({ isUploading: uploading }),
  setUploadError: (error) => set({ uploadError: error }),
  clearUploadedImages: () => set({ uploadedImages: [] }),
  
  // Complex actions
  generateJourney: async (query: string) => {
    const { userLocation } = get();
    if (!userLocation) {
      set({ journeyError: 'Location not available' });
      return;
    }
    
    set({ isGeneratingJourney: true, journeyError: null });
    
    try {
      const response = await fetch('/api/generate-journey', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          location: userLocation,
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate journey');
      }
      
      const journeyData: JourneyData = await response.json();
      set({ 
        journeyData, 
        isGeneratingJourney: false,
        isJourneyCardVisible: true,
      });
    } catch (error) {
      set({ 
        journeyError: error instanceof Error ? error.message : 'Unknown error',
        isGeneratingJourney: false,
      });
    }
  },
  
  uploadImage: async (file: File) => {
    set({ isUploading: true, uploadError: null });
    
    try {
      const formData = new FormData();
      formData.append('image', file);
      
      const response = await fetch('/api/upload-image', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('Failed to upload image');
      }
      
      get().addUploadedImage(file);
      set({ isUploading: false });
    } catch (error) {
      set({ 
        uploadError: error instanceof Error ? error.message : 'Upload failed',
        isUploading: false,
      });
    }
  },
  
  requestLocation: async () => {
    set({ locationLoading: true, locationError: null });
    
    try {
      if (!navigator.geolocation) {
        throw new Error('Geolocation is not supported by this browser');
      }
      
      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 60000,
        });
      });
      
      const userLocation: UserLocation = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
      };
      
      set({ userLocation, locationLoading: false });
    } catch (error) {
      set({ 
        locationError: error instanceof Error ? error.message : 'Location access denied',
        locationLoading: false,
      });
    }
  },
}));

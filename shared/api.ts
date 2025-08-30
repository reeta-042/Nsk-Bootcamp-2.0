/**
 * Shared code between client and server
 * Useful to share types between client and server
 * and/or small pure JS functions that can be used on both client and server
 */

/**
 * Example response type for /api/demo
 */
export interface DemoResponse {
  message: string;
}

/**
 * Journey data structure
 */
export interface JourneyData {
  id: string;
  title: string;
  narrative: string;
  images: string[];
  route: {
    coordinates: [number, number][];
    duration?: number;
    distance?: number;
  };
  destinations: {
    name: string;
    coordinates: [number, number];
    description?: string;
  }[];
}

/**
 * Request type for journey generation
 */
export interface GenerateJourneyRequest {
  query: string;
  location: {
    latitude: number;
    longitude: number;
    accuracy?: number;
  };
}

/**
 * Response type for image upload
 */
export interface ImageUploadResponse {
  success: boolean;
  imageUrl: string;
  filename: string;
  size: number;
  uploadedAt: string;
}

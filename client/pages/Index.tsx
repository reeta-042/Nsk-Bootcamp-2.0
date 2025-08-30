import { useEffect } from 'react';
import { FallbackMap } from '@/components/FallbackMap';
import { SmartCompass } from '@/components/SmartCompass';
import { JourneyCard } from '@/components/JourneyCard';
import { ImageUpload } from '@/components/ImageUpload';
import { MapSetupInfo } from '@/components/MapSetupInfo';
import { useJourneyStore } from '@/lib/store';
import { MapPin, Camera, Compass } from 'lucide-react';

export default function Index() {
  const { userLocation, journeyData, requestLocation } = useJourneyStore();

  useEffect(() => {
    // Request location permission on mount
    if (!userLocation) {
      requestLocation();
    }
  }, [userLocation, requestLocation]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="relative z-10 bg-card/80 backdrop-blur-md border-b border-border">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-primary to-journey rounded-lg flex items-center justify-center">
                <Compass className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold font-display text-foreground">
                  Journey Compass
                </h1>
                <p className="text-sm text-muted-foreground">
                  Discover adventures near you
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              {userLocation && (
                <>
                  <MapPin className="h-4 w-4" />
                  <span>
                    {userLocation.latitude.toFixed(4)}, {userLocation.longitude.toFixed(4)}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative">
        {/* Map Background */}
        <div className="h-screen w-full">
          <FallbackMap />
        </div>

        {/* Floating UI Elements */}
        <div className="absolute inset-0 pointer-events-none">
          {/* Top Search Bar */}
          <div className="absolute top-8 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4 pointer-events-auto">
            <SmartCompass />
          </div>

          {/* Map Setup Info - show when user has location but no journey */}
          {userLocation && !journeyData && (
            <div className="absolute top-8 right-8 pointer-events-auto hidden lg:block">
              <MapSetupInfo />
            </div>
          )}

          {/* Bottom Panel - Image Upload */}
          <div className="absolute bottom-8 right-8 w-80 pointer-events-auto hidden lg:block">
            <div className="bg-card/90 backdrop-blur-md rounded-xl border border-border shadow-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Camera className="h-5 w-5 text-primary" />
                <h3 className="font-semibold">Capture Your Journey</h3>
              </div>
              <ImageUpload />
            </div>
          </div>

          {/* Mobile Bottom Panel */}
          <div className="absolute bottom-4 left-4 right-4 lg:hidden pointer-events-auto">
            <div className="bg-card/90 backdrop-blur-md rounded-xl border border-border shadow-2xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <Camera className="h-4 w-4 text-primary" />
                <h3 className="text-sm font-semibold">Capture Your Journey</h3>
              </div>
              <ImageUpload />
            </div>
          </div>

          {/* Welcome Message for First Time Users */}
          {!userLocation && (
            <div className="absolute inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
              <div className="bg-card rounded-2xl p-8 max-w-md text-center shadow-2xl">
                <div className="w-16 h-16 bg-gradient-to-br from-primary to-journey rounded-full flex items-center justify-center mx-auto mb-4">
                  <Compass className="h-8 w-8 text-white" />
                </div>
                <h2 className="text-2xl font-bold font-display mb-3">
                  Welcome to Journey Compass
                </h2>
                <p className="text-muted-foreground mb-4">
                  Discover amazing adventures and hidden gems near your location.
                  Share your location to start exploring personalized journeys.
                </p>
                <p className="text-xs text-muted-foreground mb-6 bg-accent/50 rounded p-2">
                  <strong>Demo Version:</strong> Using simplified map visualization.
                  Add your Mapbox token for full interactive maps.
                </p>
                <button
                  onClick={requestLocation}
                  className="w-full bg-primary text-primary-foreground py-3 px-6 rounded-lg font-medium hover:bg-primary/90 transition-colors"
                >
                  Enable Location & Start Exploring
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Journey Card Modal */}
        <JourneyCard />
      </main>

      {/* Features Section (Hidden behind map, shown when scrolling) */}
      <section className="relative z-10 bg-card py-16">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold font-display mb-4">
              How Journey Compass Works
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              AI-powered adventure discovery that creates personalized journeys 
              based on your interests and location.
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <MapPin className="h-8 w-8 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Share Your Location</h3>
              <p className="text-muted-foreground">
                Enable location access to discover personalized adventures near you.
              </p>
            </div>
            
            <div className="text-center">
              <div className="w-16 h-16 bg-secondary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <Compass className="h-8 w-8 text-secondary" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Describe Your Adventure</h3>
              <p className="text-muted-foreground">
                Tell us what you're interested in exploring and we'll craft the perfect journey.
              </p>
            </div>
            
            <div className="text-center">
              <div className="w-16 h-16 bg-journey/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <Camera className="h-8 w-8 text-journey" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Capture & Share</h3>
              <p className="text-muted-foreground">
                Document your discoveries and share your unique adventure story.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

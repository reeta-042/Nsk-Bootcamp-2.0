import { useEffect } from 'react';
import { useJourneyStore } from '@/lib/store';
import { MapPin, Navigation, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FallbackMapProps {
  className?: string;
}

export function FallbackMap({ className }: FallbackMapProps) {
  const { 
    userLocation, 
    journeyData, 
    locationLoading,
    requestLocation 
  } = useJourneyStore();

  useEffect(() => {
    // Request location on mount
    if (!userLocation) {
      requestLocation();
    }
  }, [userLocation, requestLocation]);

  return (
    <div className={cn("relative w-full h-full bg-gradient-to-br from-slate-100 to-slate-300", className)}>
      {/* Background pattern */}
      <div 
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: `radial-gradient(circle at 20px 20px, #64748b 1px, transparent 0)`,
          backgroundSize: '40px 40px'
        }}
      />
      
      {/* Map Container */}
      <div className="relative w-full h-full flex items-center justify-center">
        
        {/* User Location Display */}
        {userLocation && (
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
            <div className="relative">
              {/* User location marker */}
              <div className="w-6 h-6 bg-primary rounded-full border-4 border-white shadow-lg animate-pulse">
                <div className="absolute inset-0 bg-primary/30 rounded-full animate-ping scale-150"></div>
              </div>
              
              {/* Location info */}
              <div className="absolute top-8 left-1/2 transform -translate-x-1/2 bg-card/90 backdrop-blur-sm rounded-lg p-3 shadow-lg min-w-48">
                <div className="flex items-center gap-2 text-sm">
                  <MapPin className="h-4 w-4 text-primary" />
                  <span className="font-medium">Your Location</span>
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {userLocation.latitude.toFixed(6)}, {userLocation.longitude.toFixed(6)}
                </div>
                {userLocation.accuracy && (
                  <div className="text-xs text-muted-foreground">
                    Accuracy: ±{Math.round(userLocation.accuracy)}m
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Journey Route Display */}
        {journeyData && journeyData.destinations.length > 0 && (
          <div className="absolute inset-0">
            {/* Simple route visualization */}
            <svg className="w-full h-full">
              <defs>
                <linearGradient id="routeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#00A6D6" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#7C3AED" stopOpacity="0.6" />
                </linearGradient>
              </defs>
              
              {/* Route path */}
              {journeyData.route.coordinates.length > 1 && (
                <polyline
                  points={journeyData.route.coordinates.map((coord, index) => {
                    // Simple positioning - in a real map this would be projected
                    const x = 200 + index * 100;
                    const y = 200 + Math.sin(index) * 50;
                    return `${x},${y}`;
                  }).join(' ')}
                  fill="none"
                  stroke="url(#routeGradient)"
                  strokeWidth="4"
                  strokeLinecap="round"
                  strokeDasharray="5,5"
                  className="animate-pulse"
                />
              )}
            </svg>
            
            {/* Destination markers */}
            {journeyData.destinations.map((destination, index) => (
              <div
                key={index}
                className="absolute"
                style={{
                  left: `${20 + index * 15}%`,
                  top: `${30 + index * 10}%`,
                }}
              >
                <div className="relative group">
                  <div className="w-8 h-8 bg-secondary rounded-full border-2 border-white shadow-lg flex items-center justify-center text-sm font-bold text-secondary-foreground hover:scale-110 transition-transform cursor-pointer">
                    {index + 1}
                  </div>
                  
                  {/* Tooltip */}
                  <div className="absolute bottom-10 left-1/2 transform -translate-x-1/2 bg-card/95 backdrop-blur-sm rounded-lg p-2 shadow-lg opacity-0 group-hover:opacity-100 transition-opacity min-w-32 z-10">
                    <div className="text-xs font-medium">{destination.name}</div>
                    {destination.description && (
                      <div className="text-xs text-muted-foreground mt-1">
                        {destination.description}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Loading state */}
        {locationLoading && (
          <div className="absolute top-4 left-4 bg-card/90 backdrop-blur-sm rounded-lg p-3 shadow-lg">
            <div className="flex items-center gap-2 text-sm">
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
              <span>Getting your location...</span>
            </div>
          </div>
        )}

        {/* No location fallback */}
        {!userLocation && !locationLoading && (
          <div className="text-center p-8">
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
              <Navigation className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">Map View</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Enable location access to see your position and journey routes
            </p>
            <button
              onClick={requestLocation}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
            >
              Enable Location
            </button>
          </div>
        )}

        {/* Map attribution (simplified) */}
        <div className="absolute bottom-2 right-2 text-xs text-muted-foreground bg-card/80 backdrop-blur-sm px-2 py-1 rounded">
          Journey Compass Map
        </div>
      </div>
    </div>
  );
}

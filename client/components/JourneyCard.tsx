import { useEffect } from 'react';
import { X, MapPin, Clock, Route, Camera, Share2, Download } from 'lucide-react';
import { useJourneyStore } from '@/lib/store';
import { cn } from '@/lib/utils';

interface JourneyCardProps {
  className?: string;
}

export function JourneyCard({ className }: JourneyCardProps) {
  const { 
    journeyData, 
    isJourneyCardVisible, 
    setJourneyCardVisible,
  } = useJourneyStore();

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setJourneyCardVisible(false);
      }
    };

    if (isJourneyCardVisible) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isJourneyCardVisible, setJourneyCardVisible]);

  if (!isJourneyCardVisible || !journeyData) return null;

  const formatDuration = (minutes?: number) => {
    if (!minutes) return 'Duration unknown';
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  const formatDistance = (meters?: number) => {
    if (!meters) return 'Distance unknown';
    if (meters < 1000) {
      return `${meters}m`;
    }
    return `${(meters / 1000).toFixed(1)}km`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => setJourneyCardVisible(false)}
      />
      
      {/* Modal */}
      <div className={cn(
        "relative w-full max-w-2xl max-h-[90vh] bg-card rounded-t-2xl sm:rounded-2xl shadow-2xl",
        "flex flex-col overflow-hidden",
        className
      )}>
        {/* Header */}
        <div className="relative p-6 border-b">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h2 className="text-2xl font-bold font-display text-foreground mb-2">
                {journeyData.title}
              </h2>
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                {journeyData.route.duration && (
                  <div className="flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    <span>{formatDuration(journeyData.route.duration)}</span>
                  </div>
                )}
                {journeyData.route.distance && (
                  <div className="flex items-center gap-1">
                    <Route className="h-4 w-4" />
                    <span>{formatDistance(journeyData.route.distance)}</span>
                  </div>
                )}
                <div className="flex items-center gap-1">
                  <MapPin className="h-4 w-4" />
                  <span>{journeyData.destinations.length} stops</span>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <button className="p-2 hover:bg-accent rounded-lg transition-colors">
                <Share2 className="h-5 w-5 text-muted-foreground" />
              </button>
              <button className="p-2 hover:bg-accent rounded-lg transition-colors">
                <Download className="h-5 w-5 text-muted-foreground" />
              </button>
              <button 
                onClick={() => setJourneyCardVisible(false)}
                className="p-2 hover:bg-accent rounded-lg transition-colors"
              >
                <X className="h-5 w-5 text-muted-foreground" />
              </button>
            </div>
          </div>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {/* Journey Images */}
          {journeyData.images.length > 0 && (
            <div className="p-6 border-b">
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <Camera className="h-5 w-5" />
                Journey Gallery
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {journeyData.images.map((image, index) => (
                  <div
                    key={index}
                    className="aspect-square rounded-lg overflow-hidden bg-muted"
                  >
                    <img
                      src={image}
                      alt={`Journey image ${index + 1}`}
                      className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Narrative */}
          <div className="p-6 border-b">
            <h3 className="text-lg font-semibold mb-3">Your Adventure Story</h3>
            <div className="prose prose-sm max-w-none">
              <p className="text-foreground leading-relaxed whitespace-pre-wrap">
                {journeyData.narrative}
              </p>
            </div>
          </div>
          
          {/* Destinations */}
          {journeyData.destinations.length > 0 && (
            <div className="p-6">
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <MapPin className="h-5 w-5" />
                Key Destinations
              </h3>
              <div className="space-y-3">
                {journeyData.destinations.map((destination, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-3 p-3 rounded-lg bg-accent/50 hover:bg-accent transition-colors"
                  >
                    <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-primary-foreground font-semibold text-sm">
                      {index + 1}
                    </div>
                    <div className="flex-1">
                      <h4 className="font-medium text-foreground">{destination.name}</h4>
                      {destination.description && (
                        <p className="text-sm text-muted-foreground mt-1">
                          {destination.description}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground mt-1">
                        {destination.coordinates[1].toFixed(6)}, {destination.coordinates[0].toFixed(6)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        {/* Footer Actions */}
        <div className="p-6 border-t bg-muted/20">
          <div className="flex items-center justify-between gap-4">
            <button
              onClick={() => setJourneyCardVisible(false)}
              className="px-6 py-2 text-muted-foreground hover:text-foreground transition-colors"
            >
              Close
            </button>
            <div className="flex gap-3">
              <button className="px-6 py-2 border border-border rounded-lg hover:bg-accent transition-colors">
                Save Journey
              </button>
              <button className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors">
                Start Adventure
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

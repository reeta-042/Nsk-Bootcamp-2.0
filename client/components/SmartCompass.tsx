import { useState } from 'react';
import { Search, Compass, Loader2, MapPin } from 'lucide-react';
import { useJourneyStore } from '@/lib/store';
import { cn } from '@/lib/utils';

interface SmartCompassProps {
  className?: string;
}

export function SmartCompass({ className }: SmartCompassProps) {
  const [inputValue, setInputValue] = useState('');
  const { 
    searchQuery,
    isGeneratingJourney,
    journeyError,
    userLocation,
    locationLoading,
    generateJourney,
    setSearchQuery,
  } = useJourneyStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isGeneratingJourney || !userLocation) return;
    
    setSearchQuery(inputValue);
    await generateJourney(inputValue);
  };

  const isDisabled = !userLocation || locationLoading || isGeneratingJourney;

  const placeholderTexts = [
    "Find hidden waterfalls near me",
    "Discover local street art",
    "Adventure to mountain peaks",
    "Explore historic neighborhoods",
    "Find the best sunset spots",
    "Discover scenic hiking trails",
  ];

  const [placeholderIndex] = useState(Math.floor(Math.random() * placeholderTexts.length));
  
  return (
    <div className={cn("w-full max-w-2xl", className)}>
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 z-10">
            {locationLoading ? (
              <Loader2 className="h-5 w-5 text-muted-foreground animate-spin" />
            ) : userLocation ? (
              <Compass className="h-5 w-5 text-primary" />
            ) : (
              <MapPin className="h-5 w-5 text-muted-foreground" />
            )}
          </div>
          
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={
              locationLoading 
                ? "Getting your location..." 
                : !userLocation 
                ? "Location access needed..."
                : placeholderTexts[placeholderIndex]
            }
            disabled={isDisabled}
            className={cn(
              "w-full h-14 pl-12 pr-16 rounded-xl border-2 bg-card/50 backdrop-blur-sm",
              "text-lg font-medium placeholder:text-muted-foreground",
              "transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-primary/20",
              !userLocation 
                ? "border-muted-foreground/20 cursor-not-allowed" 
                : "border-border hover:border-primary/50 focus:border-primary shadow-lg"
            )}
          />
          
          <button
            type="submit"
            disabled={isDisabled || !inputValue.trim()}
            className={cn(
              "absolute right-2 top-1/2 -translate-y-1/2",
              "h-10 w-10 rounded-lg bg-primary text-primary-foreground",
              "flex items-center justify-center transition-all duration-200",
              "hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary/20",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {isGeneratingJourney ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Search className="h-5 w-5" />
            )}
          </button>
        </div>
        
        {/* Status indicators */}
        <div className="mt-3 space-y-2">
          {!userLocation && !locationLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <MapPin className="h-4 w-4" />
              <span>Location access is required to discover journeys</span>
            </div>
          )}
          
          {journeyError && (
            <div className="flex items-center gap-2 text-sm text-destructive">
              <div className="w-1 h-1 bg-destructive rounded-full" />
              <span>{journeyError}</span>
            </div>
          )}
          
          {userLocation && !isGeneratingJourney && (
            <div className="flex items-center gap-2 text-sm text-success">
              <div className="w-1 h-1 bg-success rounded-full animate-pulse" />
              <span>Ready to explore from your location</span>
            </div>
          )}
        </div>
      </form>
      
      {/* Quick suggestions */}
      <div className="mt-6">
        <p className="text-sm font-medium text-muted-foreground mb-3">Popular discoveries:</p>
        <div className="flex flex-wrap gap-2">
          {[
            "🏔️ Mountain adventures",
            "🌊 Waterfront walks", 
            "🎨 Art & culture",
            "🌳 Nature escapes",
            "🏛️ Historic sites",
            "☕ Local cafes"
          ].map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => setInputValue(suggestion.split(' ').slice(1).join(' '))}
              disabled={isDisabled}
              className={cn(
                "px-3 py-1.5 text-sm rounded-full border border-border",
                "bg-card/50 backdrop-blur-sm hover:bg-accent transition-colors",
                "disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

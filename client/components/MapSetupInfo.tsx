import { Info, ExternalLink } from 'lucide-react';

export function MapSetupInfo() {
  return (
    <div className="absolute top-4 right-4 bg-card/90 backdrop-blur-sm rounded-lg p-4 shadow-lg max-w-80 z-10">
      <div className="flex items-start gap-3">
        <Info className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
        <div>
          <h4 className="font-semibold text-sm mb-2">Demo Map</h4>
          <p className="text-xs text-muted-foreground mb-3">
            This is a simplified map view. For full interactive maps with satellite imagery and navigation:
          </p>
          <ol className="text-xs text-muted-foreground space-y-1 mb-3">
            <li>1. Get a free <a href="https://account.mapbox.com/" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline inline-flex items-center gap-1">Mapbox token <ExternalLink className="h-3 w-3" /></a></li>
            <li>2. Replace the token in <code className="bg-muted px-1 rounded">JourneyMap.tsx</code></li>
            <li>3. Switch back to <code className="bg-muted px-1 rounded">JourneyMap</code> component</li>
          </ol>
          <p className="text-xs text-success">
            ✅ All other features work perfectly!
          </p>
        </div>
      </div>
    </div>
  );
}

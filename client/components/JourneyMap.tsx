import { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import { useJourneyStore } from '@/lib/store';
import { cn } from '@/lib/utils';

// You'll need to set your Mapbox access token
// For now, using a public demo token (replace with your own)
mapboxgl.accessToken = 'pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw';

interface JourneyMapProps {
  className?: string;
}

export function JourneyMap({ className }: JourneyMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const userMarker = useRef<mapboxgl.Marker | null>(null);
  const [isMapLoaded, setIsMapLoaded] = useState(false);
  
  const { 
    userLocation, 
    journeyData, 
    locationLoading,
    requestLocation 
  } = useJourneyStore();

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/outdoors-v12',
      center: [-74.006, 40.7128], // Default to NYC
      zoom: 13,
      attributionControl: false,
    });

    map.current.addControl(new mapboxgl.AttributionControl(), 'bottom-right');
    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');

    map.current.on('load', () => {
      setIsMapLoaded(true);
    });

    // Request location on mount
    requestLocation();

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [requestLocation]);

  // Update user location marker
  useEffect(() => {
    if (!map.current || !userLocation || !isMapLoaded) return;

    // Remove existing marker
    if (userMarker.current) {
      userMarker.current.remove();
    }

    // Create custom user location marker
    const el = document.createElement('div');
    el.className = 'user-location-marker';
    el.innerHTML = `
      <div class="relative">
        <div class="w-4 h-4 bg-primary rounded-full border-2 border-white shadow-lg animate-pulse"></div>
        <div class="absolute top-0 left-0 w-4 h-4 bg-primary/30 rounded-full animate-ping"></div>
      </div>
    `;

    userMarker.current = new mapboxgl.Marker(el)
      .setLngLat([userLocation.longitude, userLocation.latitude])
      .addTo(map.current);

    // Fly to user location
    map.current.flyTo({
      center: [userLocation.longitude, userLocation.latitude],
      zoom: 15,
      duration: 2000,
    });
  }, [userLocation, isMapLoaded]);

  // Update journey route
  useEffect(() => {
    if (!map.current || !journeyData || !isMapLoaded) return;

    const routeCoordinates = journeyData.route.coordinates;
    
    if (routeCoordinates.length === 0) return;

    // Add route source if it doesn't exist
    if (!map.current.getSource('route')) {
      map.current.addSource('route', {
        type: 'geojson',
        data: {
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'LineString',
            coordinates: routeCoordinates,
          },
        },
      });

      // Add route layer
      map.current.addLayer({
        id: 'route',
        type: 'line',
        source: 'route',
        layout: {
          'line-join': 'round',
          'line-cap': 'round',
        },
        paint: {
          'line-color': '#00A6D6', // Primary color
          'line-width': 4,
          'line-opacity': 0.8,
        },
      });

      // Add route glow effect
      map.current.addLayer({
        id: 'route-glow',
        type: 'line',
        source: 'route',
        layout: {
          'line-join': 'round',
          'line-cap': 'round',
        },
        paint: {
          'line-color': '#00A6D6',
          'line-width': 8,
          'line-opacity': 0.3,
          'line-blur': 2,
        },
      }, 'route');
    } else {
      // Update existing route
      const source = map.current.getSource('route') as mapboxgl.GeoJSONSource;
      source.setData({
        type: 'Feature',
        properties: {},
        geometry: {
          type: 'LineString',
          coordinates: routeCoordinates,
        },
      });
    }

    // Add destination markers
    journeyData.destinations.forEach((destination, index) => {
      const el = document.createElement('div');
      el.className = 'destination-marker';
      el.innerHTML = `
        <div class="w-8 h-8 bg-secondary rounded-full border-2 border-white shadow-lg flex items-center justify-center text-sm font-bold text-secondary-foreground">
          ${index + 1}
        </div>
      `;

      new mapboxgl.Marker(el)
        .setLngLat(destination.coordinates)
        .setPopup(
          new mapboxgl.Popup({ offset: 25 })
            .setHTML(`
              <div class="p-2">
                <h3 class="font-semibold text-sm">${destination.name}</h3>
                ${destination.description ? `<p class="text-xs text-muted-foreground mt-1">${destination.description}</p>` : ''}
              </div>
            `)
        )
        .addTo(map.current!);
    });

    // Fit map to show the entire route
    const bounds = new mapboxgl.LngLatBounds();
    routeCoordinates.forEach(coord => bounds.extend(coord));
    journeyData.destinations.forEach(dest => bounds.extend(dest.coordinates));
    
    if (userLocation) {
      bounds.extend([userLocation.longitude, userLocation.latitude]);
    }

    map.current.fitBounds(bounds, {
      padding: 50,
      duration: 1000,
    });
  }, [journeyData, isMapLoaded, userLocation]);

  return (
    <div className={cn("relative w-full h-full", className)}>
      <div ref={mapContainer} className="w-full h-full rounded-lg overflow-hidden" />
      
      {locationLoading && (
        <div className="absolute top-4 left-4 bg-card/90 backdrop-blur-sm rounded-lg p-3 shadow-lg">
          <div className="flex items-center gap-2 text-sm">
            <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span>Getting your location...</span>
          </div>
        </div>
      )}
    </div>
  );
}

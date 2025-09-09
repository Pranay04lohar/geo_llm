"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

export default function MiniMap({ onOpenFullScreen, embedded = false }) {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  const [lng] = useState(78.9629);
  const [lat] = useState(20.5937);
  const [zoom] = useState(3);

  const createFallbackStyle = () => ({
    version: 8,
    sources: {
      fallback: {
        type: "raster",
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
        attribution: "© Esri",
        maxzoom: 19,
      },
    },
    layers: [{ id: "fallback-layer", type: "raster", source: "fallback" }],
  });

  const initMap = useCallback(() => {
    if (map.current || !mapContainer.current) return;
    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: createFallbackStyle(),
      center: [lng, lat],
      zoom,
      interactive: false,
    });
    map.current.on("load", () => setMapLoaded(true));
  }, [lng, lat, zoom]);

  useEffect(() => {
    initMap();
    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, [initMap]);

  if (embedded) {
    return (
      <div
        onClick={onOpenFullScreen}
        className="w-full h-40 cursor-pointer relative"
        title="Open Map"
      >
        <div ref={mapContainer} className="w-full h-full" />
        <div className="absolute inset-x-0 bottom-0 bg-black/50 text-white text-xs px-3 py-1 text-left">
          Open Full
        </div>
      </div>
    );
  }

  return (
    <button
      onClick={onOpenFullScreen}
      className="fixed bottom-6 right-6 z-40 w-52 h-36 rounded-xl overflow-hidden shadow-2xl border border-white/20 bg-black/30 backdrop-blur-md hover:scale-105 transition-transform"
      title="Open Map"
    >
      <div ref={mapContainer} className="w-full h-full" />
      <div className="absolute inset-x-0 bottom-0 bg-black/50 text-white text-xs px-3 py-2 text-left">
        Open Full Map
      </div>
    </button>
  );
}



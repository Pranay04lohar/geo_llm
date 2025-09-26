"use client";

import { useState, useRef, useEffect } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { FaExpand, FaEye, FaEyeSlash } from "react-icons/fa";

export default function AnalysisResult({ content }) {
  // Parse map data from content if it exists
  const mapDataMatch = content.match(/\[MAP_DATA:(.*?)\]$/);
  const hasMapData = mapDataMatch !== null;
  const mapData = hasMapData ? JSON.parse(mapDataMatch[1]) : null;
  const textContent = hasMapData
    ? content.replace(/\[MAP_DATA:.*?\]$/, "").trim()
    : content;

  // Generate unique ID for this map instance
  const mapId = useRef(
    `analysis-map-${Math.random().toString(36).substr(2, 9)}`
  );

  // Debug logging (can be removed in production)
  console.log("AnalysisResult - Has map data:", hasMapData);
  if (hasMapData) {
    console.log("AnalysisResult - Map data:", mapData);
  }

  const [showMap, setShowMap] = useState(false);
  const [mapLoaded, setMapLoaded] = useState(false);
  const mapContainer = useRef(null);
  const map = useRef(null);

  // Initialize map when showMap becomes true
  useEffect(() => {
    if (!showMap || !hasMapData || !mapContainer.current) return;
    if (map.current) return; // Prevent re-initialization

    console.log("Initializing map with data:", mapData);

    // Get center coordinates from ROI or use default
    let center = [78.9629, 20.5937]; // Default India center
    let zoom = 6;

    if (mapData.roi?.center) {
      center = mapData.roi.center;
      zoom = 10;
    }

    // Create base map style
    const createMapStyle = () => ({
      version: 8,
      sources: {
        satellite: {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          attribution: "© Esri",
        },
      },
      layers: [{ id: "satellite-layer", type: "raster", source: "satellite" }],
    });

    try {
      // Initialize map
      map.current = new maplibregl.Map({
        container: mapContainer.current,
        style: createMapStyle(),
        center: center,
        zoom: zoom,
      });

      map.current.on("load", () => {
        console.log("Map loaded successfully");
        setMapLoaded(true);

        // Add analysis layer if tile URL is available
        if (mapData.tile_url) {
          try {
            console.log("Adding analysis layer with URL:", mapData.tile_url);
            // Add the analysis layer
            map.current.addSource("analysis", {
              type: "raster",
              tiles: [mapData.tile_url],
              tileSize: 256,
            });

            map.current.addLayer({
              id: "analysis-layer",
              type: "raster",
              source: "analysis",
              paint: {
                "raster-opacity": 0.7,
              },
            });

            console.log("Analysis layer added successfully");
          } catch (error) {
            console.error("Error adding analysis layer:", error);
          }
        } else {
          console.warn("No tile URL available for analysis layer");
        }

        // Add ROI boundary if available
        if (mapData.roi?.geometry) {
          try {
            console.log("Adding ROI boundary");
            map.current.addSource("roi", {
              type: "geojson",
              data: {
                type: "Feature",
                geometry: mapData.roi.geometry,
              },
            });

            map.current.addLayer({
              id: "roi-boundary",
              type: "line",
              source: "roi",
              paint: {
                "line-color": "#ff0000",
                "line-width": 2,
                "line-opacity": 0.8,
              },
            });

            // Fit map to ROI bounds
            const coordinates = mapData.roi.geometry.coordinates[0];
            const bounds = new maplibregl.LngLatBounds();
            coordinates.forEach((coord) => bounds.extend(coord));
            map.current.fitBounds(bounds, { padding: 50 });
            console.log("ROI boundary added successfully");
          } catch (error) {
            console.error("Error adding ROI boundary:", error);
          }
        } else {
          console.warn("No ROI geometry available for boundary");
        }
      });

      map.current.on("error", (e) => {
        console.error("Map error:", e);
      });
    } catch (error) {
      console.error("Error initializing map:", error);
      setMapLoaded(false);
    }
  }, [showMap]); // Only depend on showMap, not mapData

  // Cleanup effect
  useEffect(() => {
    return () => {
      if (map.current) {
        console.log("Cleaning up map");
        map.current.remove();
        map.current = null;
        setMapLoaded(false);
      }
    };
  }, []);

  const getAnalysisTypeIcon = (analysisType) => {
    switch (analysisType?.toLowerCase()) {
      case "ndvi":
        return "🌱";
      case "water":
        return "💧";
      case "lulc":
        return "🏞️";
      case "lst":
        return "🌡️";
      default:
        return "📊";
    }
  };

  const getAnalysisTypeName = (analysisType) => {
    switch (analysisType?.toLowerCase()) {
      case "ndvi":
        return "Vegetation (NDVI)";
      case "water":
        return "Water Coverage";
      case "lulc":
        return "Land Use/Land Cover";
      case "lst":
        return "Land Surface Temperature";
      default:
        return "Analysis";
    }
  };

  return (
    <div className="space-y-4">
      {/* Text content */}
      <div className="whitespace-pre-wrap">{textContent}</div>

      {/* Debug info - remove this in production */}
      {!hasMapData && (
        <div className="text-xs text-gray-400 border border-gray-200 rounded p-2">
          Debug: No map data found in content. Looking for [MAP_DATA:...]
          pattern.
        </div>
      )}

      {/* Map visualization section */}
      {hasMapData && (
        <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
          <div className="bg-gray-50 px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="text-lg">
                {getAnalysisTypeIcon(mapData.analysis_type)}
              </span>
              <span className="font-medium text-gray-900">
                {getAnalysisTypeName(mapData.analysis_type)} Visualization
              </span>
              {mapData.roi?.display_name && (
                <span className="text-sm text-gray-500">
                  • {mapData.roi.display_name.split(",")[0]}
                </span>
              )}
            </div>
            <button
              onClick={() => setShowMap(!showMap)}
              className="flex items-center space-x-2 px-3 py-1.5 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors text-sm"
            >
              {showMap ? <FaEyeSlash /> : <FaEye />}
              <span>{showMap ? "Hide Map" : "Show Map"}</span>
            </button>
          </div>

          {showMap && (
            <div className="relative" key={mapId.current}>
              <div
                ref={mapContainer}
                className="w-full h-96"
                id={mapId.current}
              />
              {!mapLoaded && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
                  <div className="text-gray-500">Loading map...</div>
                </div>
              )}
              <div className="absolute top-2 right-2 bg-white/80 backdrop-blur-sm rounded px-2 py-1 text-xs text-gray-600">
                {mapData.service_used?.toUpperCase()} Analysis
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

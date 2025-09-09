"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { FaTrashAlt, FaTimes, FaPlus, FaMinus, FaCompass } from "react-icons/fa";

function FullScreenMap({ roiData, onClose, onExport }) {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [mapError, setMapError] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawingCoords, setDrawingCoords] = useState([]);
  const [mapStyle, setMapStyle] = useState("map"); // 'satellite' or 'map'
  const [roiList, setRoiList] = useState(roiData || []);
  const [roiCounter, setRoiCounter] = useState((roiData?.length || 0) + 1);

  // Refs to hold the latest state for map event listeners
  const isDrawingRef = useRef(isDrawing);
  const drawingCoordsRef = useRef(drawingCoords);

  // Keep refs in sync with state
  useEffect(() => {
    isDrawingRef.current = isDrawing;
  }, [isDrawing]);

  useEffect(() => {
    drawingCoordsRef.current = drawingCoords;
  }, [drawingCoords]);

  // Center of India (near Nagpur)
  const [lng] = useState(78.9629);
  const [lat] = useState(20.5937);
  const [zoom] = useState(4);

  // India bounds
  const indiaBounds = [
    [50.0, 0.0],
    [110.0, 45.0],
  ];

  // --- Map Style Definitions ---
  const createGoogleMapStyle = () => {
    const googleMapsApiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    if (
      !googleMapsApiKey ||
      googleMapsApiKey === "your_google_maps_api_key_here"
    ) {
      console.warn("Google Maps API key not found. Please add NEXT_PUBLIC_GOOGLE_MAPS_API_KEY to your .env.local file");
      return createFallbackStyle();
    }
    return {
      version: 8,
      sources: {
        "google-terrain": {
          type: "raster",
          tiles: [
            `https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}&key=${googleMapsApiKey}`,
          ],
          tileSize: 256,
          maxzoom: 20,
        },
      },
      layers: [
        {
          id: "google-terrain-layer",
          type: "raster",
          source: "google-terrain",
        },
      ],
    };
  };

  const createGoogleSatelliteStyle = () => {
    const googleMapsApiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    if (
      !googleMapsApiKey ||
      googleMapsApiKey === "your_google_maps_api_key_here"
    ) {
      console.warn("Google Maps API key not found. Please add NEXT_PUBLIC_GOOGLE_MAPS_API_KEY to your .env.local file");
      return createFallbackSatelliteStyle();
    }
    return {
      version: 8,
      sources: {
        "google-satellite": {
          type: "raster",
          tiles: [
            `https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}&key=${googleMapsApiKey}`,
          ],
          tileSize: 256,
          maxzoom: 20,
        },
      },
      layers: [
        {
          id: "google-satellite-layer",
          type: "raster",
          source: "google-satellite",
        },
      ],
    };
  };

  const createFallbackStyle = () => ({
    version: 8,
    sources: {
      fallback: {
        type: "raster",
        tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"],
        tileSize: 256,
        attribution: "© Esri",
        maxzoom: 19,
      },
    },
    layers: [{ id: "fallback-layer", type: "raster", source: "fallback" }],
  });

  const createFallbackSatelliteStyle = () => ({
    version: 8,
    sources: {
      satellite: {
        type: "raster",
        tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
        tileSize: 256,
        attribution: "© Esri",
        maxzoom: 19,
      },
    },
    layers: [{ id: "satellite-layer", type: "raster", source: "satellite" }],
  });

  const getCurrentMapStyle = useCallback(() => {
    return mapStyle === "satellite" ? createGoogleSatelliteStyle() : createGoogleMapStyle();
  }, [mapStyle]);

  // --- ROI Color Management ---
  const getROIColor = (index) => {
    const colors = [
      "#ff6b35", // 1. Bright Orange
      "#e74c3c", // 2. Bright Red
      "#3498db", // 3. Bright Blue
      "#2ecc71", // 4. Bright Green
      "#f39c12", // 5. Bright Orange-Yellow
      "#9b59b6", // 6. Purple
      "#1abc9c", // 7. Turquoise
      "#34495e", // 8. Dark Blue-Gray
      "#e67e22", // 9. Dark Orange
      "#8e44ad", // 10. Dark Purple
    ];
    return colors[(index - 1) % colors.length];
  };

  // --- Drawing Logic ---
  const updateDrawing = useCallback((coords, isComplete) => {
    if (!map.current || !map.current.getSource("drawing")) return;

    const features = [];
    if (coords.length > 0) {
      if (isComplete && coords.length > 0 && coords[0].length > 3) {
        features.push({
          type: "Feature",
          properties: {},
          geometry: { type: "Polygon", coordinates: coords },
        });
      } else if (!isComplete) {
        if (coords.length > 1) {
          features.push({
            type: "Feature",
            properties: {},
            geometry: { type: "LineString", coordinates: coords },
          });
        }
        coords.forEach((coord) => {
          features.push({
            type: "Feature",
            properties: {},
            geometry: { type: "Point", coordinates: coord },
          });
        });
      }
    }
    map.current.getSource("drawing").setData({ type: "FeatureCollection", features });
  }, []);

  const handleMapClick = useCallback(
    (e) => {
      if (!isDrawingRef.current) return;

      const coords = [e.lngLat.lng, e.lngLat.lat];
      const tolerance = 0.00001;
      const isDuplicate = drawingCoordsRef.current.some(
        (existingCoord) =>
          Math.abs(existingCoord[0] - coords[0]) < tolerance &&
          Math.abs(existingCoord[1] - coords[1]) < tolerance
      );

      if (isDuplicate) return;

      const newCoords = [...drawingCoordsRef.current, coords];
      setDrawingCoords(newCoords);
      updateDrawing(newCoords, false);
    },
    [updateDrawing]
  );

  const finishDrawing = useCallback(
    (e) => {
      if (!isDrawingRef.current || drawingCoordsRef.current.length < 3) {
        return;
      }
      e.preventDefault();

      const finalCoords = [
        ...drawingCoordsRef.current,
        drawingCoordsRef.current[0],
      ];
      const polygon = {
        type: "Feature",
        properties: {},
        geometry: { type: "Polygon", coordinates: [finalCoords] },
      };

      const defaultName = `ROI ${roiCounter}`;
      const userInput = window.prompt(`Name your ROI polygon:`, defaultName);

      if (userInput === null) {
        setIsDrawing(false);
        setDrawingCoords([]);
        map.current.getCanvas().style.cursor = "";
        map.current.off("click", handleMapClick);
        map.current.off("dblclick", finishDrawing);
        updateDrawing([], false);
        return;
      }

      const roiName = userInput.trim() || defaultName;
      const currentCounter = roiCounter;
      const newROI = {
        id: `roi-${currentCounter}`,
        name: roiName,
        geojson: polygon,
        color: getROIColor(currentCounter),
      };

      setRoiList((prev) => [...prev, newROI]);
      setRoiCounter((prev) => prev + 1);

      setIsDrawing(false);
      setDrawingCoords([]);
      map.current.getCanvas().style.cursor = "";
      map.current.off("click", handleMapClick);
      map.current.off("dblclick", finishDrawing);
      updateDrawing([], false);
    },
    [updateDrawing, handleMapClick, roiCounter]
  );

  // --- Map Initialization ---
  useEffect(() => {
    if (map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: getCurrentMapStyle(),
      center: [lng, lat],
      zoom: zoom,
      minZoom: 1,
      maxZoom: 20, // Google Maps supports higher zoom levels
    });

    map.current.setMaxBounds(indiaBounds);

    map.current.on("load", () => {
      setMapLoaded(true);
      setupDrawingLayers();
    });

    map.current.on("error", (e) => {
      setMapError("Failed to load map. Please check your internet connection.");
    });

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    const onStyleLoad = () => {
      setupDrawingLayers();
      if (isDrawingRef.current) {
        map.current.getCanvas().style.cursor = "crosshair";
        map.current.on("click", handleMapClick);
        map.current.on("dblclick", finishDrawing);
        if (drawingCoordsRef.current.length > 0) {
          updateDrawing(drawingCoordsRef.current, false);
        }
      }
    };

    map.current.once("style.load", onStyleLoad);
    map.current.setStyle(getCurrentMapStyle());

    return () => {
      if (map.current) {
        map.current.off("style.load", onStyleLoad);
      }
    };
  }, [mapStyle, roiList, updateDrawing, handleMapClick, finishDrawing]);

  // Effect to display ROI polygons
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    const currentRoiIds = roiList.map((roi) => roi.id);
    const mapSources = map.current.getStyle().sources;

    Object.keys(mapSources).forEach((sourceId) => {
      if (sourceId.startsWith("roi-") && !currentRoiIds.includes(sourceId)) {
        if (map.current.getLayer(`${sourceId}-fill`))
          map.current.removeLayer(`${sourceId}-fill`);
        if (map.current.getLayer(`${sourceId}-stroke`))
          map.current.removeLayer(`${sourceId}-stroke`);
        if (map.current.getSource(sourceId)) map.current.removeSource(sourceId);
      }
    });

    roiList.forEach((roi) => {
      if (!map.current.getSource(roi.id)) {
        map.current.addSource(roi.id, {
          type: "geojson",
          data: roi.geojson,
        });

        map.current.addLayer({
          id: `${roi.id}-fill`,
          type: "fill",
          source: roi.id,
          paint: { "fill-color": roi.color, "fill-opacity": 0.4 },
        });
        map.current.addLayer({
          id: `${roi.id}-stroke`,
          type: "line",
          source: roi.id,
          paint: { "line-color": roi.color, "line-width": 3 },
        });
      }
    });
  }, [roiList, mapLoaded, mapStyle]);

  const toggleMapStyle = () => {
    setMapStyle((prev) => (prev === "satellite" ? "map" : "satellite"));
  };

  const setupDrawingLayers = () => {
    if (map.current.getSource("drawing")) {
      map.current.removeLayer("polygon-vertices");
      map.current.removeLayer("polygon-stroke");
      map.current.removeLayer("polygon-fill");
      map.current.removeSource("drawing");
    }
    map.current.addSource("drawing", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });
    map.current.addLayer({
      id: "polygon-fill",
      type: "fill",
      source: "drawing",
      paint: { "fill-color": "#ff6b35", "fill-opacity": 0.4 },
    });
    map.current.addLayer({
      id: "polygon-stroke",
      type: "line",
      source: "drawing",
      paint: { "line-color": "#ff6b35", "line-width": 3 },
    });
    map.current.addLayer({
      id: "polygon-vertices",
      type: "circle",
      source: "drawing",
      paint: {
        "circle-radius": 6,
        "circle-color": "#ff6b35",
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 3,
      },
      filter: ["==", "$type", "Point"],
    });
  };

  const startDrawing = () => {
    if (!mapLoaded || !map.current) return;

    if (isDrawing) {
      cancelDrawing();
    }

    if (!map.current.getSource("drawing")) {
      setupDrawingLayers();
    }

    setIsDrawing(true);
    setDrawingCoords([]);
    map.current.getCanvas().style.cursor = "crosshair";
    updateDrawing([], false);

    map.current.off("click", handleMapClick);
    map.current.off("dblclick", finishDrawing);
    map.current.on("click", handleMapClick);
    map.current.on("dblclick", finishDrawing);
  };

  const cancelDrawing = () => {
    if (!mapLoaded || !map.current) return;
    setIsDrawing(false);
    setDrawingCoords([]);
    updateDrawing([], false);
    map.current.getCanvas().style.cursor = "";
    map.current.off("click", handleMapClick);
    map.current.off("dblclick", finishDrawing);
  };

  const zoomIn = () => {
    if (map.current) {
      map.current.zoomIn();
    }
  };

  const zoomOut = () => {
    if (map.current) {
      map.current.zoomOut();
    }
  };

  const resetView = () => {
    if (map.current) {
      map.current.flyTo({ center: [lng, lat], zoom: zoom });
    }
  };

  const handleExport = () => {
    if (onExport) {
      onExport(roiList);
    }
  };


  return (
    <div className="fixed inset-0 z-50 bg-black">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-10 bg-white/95 backdrop-blur-sm border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-gray-800">Interactive Map</h1>
            <div data-tour-target="map-layers" className="flex items-center gap-2">
              <button
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  mapStyle === "map"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                }`}
                onClick={toggleMapStyle}
              >
                Map
              </button>
              <button
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  mapStyle === "satellite"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                }`}
                onClick={toggleMapStyle}
              >
                Satellite
              </button>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              data-tour-target="drawing-tools"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                isDrawing
                  ? "bg-orange-500 text-white"
                  : "bg-gray-200 text-gray-700 hover:bg-gray-300"
              }`}
              onClick={isDrawing ? cancelDrawing : startDrawing}
            >
              {isDrawing ? "Cancel Drawing" : "Draw ROI"}
            </button>
            
            <button
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                roiList.length === 0
                  ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                  : "bg-green-600 text-white hover:bg-green-700"
              }`}
              onClick={handleExport}
              disabled={roiList.length === 0}
            >
              Export ROIs ({roiList.length})
            </button>
            
            <button
              className="p-2 rounded-lg bg-gray-200 text-gray-700 hover:bg-gray-300 transition-all"
              onClick={onClose}
            >
              <FaTimes />
            </button>
          </div>
        </div>
      </div>

      {/* Google Maps-style Zoom Controls */}
      <div data-tour-target="map-navigation" className="absolute top-20 right-4 z-10 flex flex-col gap-2">
        <button
          className="w-10 h-10 bg-white rounded-lg shadow-lg flex items-center justify-center text-gray-700 hover:bg-gray-50 transition-all"
          onClick={zoomIn}
        >
          <FaPlus />
        </button>
        <button
          className="w-10 h-10 bg-white rounded-lg shadow-lg flex items-center justify-center text-gray-700 hover:bg-gray-50 transition-all"
          onClick={zoomOut}
        >
          <FaMinus />
        </button>
        <button
          className="w-10 h-10 bg-white rounded-lg shadow-lg flex items-center justify-center text-gray-700 hover:bg-gray-50 transition-all"
          onClick={resetView}
        >
          <FaCompass />
        </button>
      </div>

      {/* Drawing Instructions */}
      {isDrawing && (
        <div className="absolute top-20 left-1/2 transform -translate-x-1/2 z-10 bg-black/80 text-white px-4 py-2 rounded-lg">
          <p className="text-sm">Click to add points. Double-click to finish.</p>
        </div>
      )}

      {/* ROI List */}
      {roiList.length > 0 && (
        <div data-tour-target="roi-management" className="absolute bottom-4 left-4 z-10 bg-white/95 backdrop-blur-sm rounded-lg p-4 max-w-sm max-h-64 overflow-y-auto">
          <h3 className="font-semibold text-gray-800 mb-2">Active ROIs ({roiList.length})</h3>
          {roiList.map((roi) => (
            <div key={roi.id} className="flex items-center gap-2 mb-2 p-2 bg-gray-50 rounded">
              <span
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: roi.color }}
              ></span>
              <span className="text-sm text-gray-700 flex-1">{roi.name}</span>
              <button
                className="text-red-500 hover:text-red-700 p-1"
                onClick={() => {
                  setRoiList((prev) => prev.filter((r) => r.id !== roi.id));
                }}
              >
                <FaTrashAlt size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Map Container */}
      <div className="w-full h-full pt-16">
        <div ref={mapContainer} className="w-full h-full" />
      </div>

      {/* Error Display */}
      {mapError && (
        <div className="absolute top-20 left-4 z-10 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {mapError}
        </div>
      )}

      {/* Loading Display */}
      {!mapLoaded && !mapError && (
        <div className="absolute inset-0 flex items-center justify-center bg-white">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading map...</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default FullScreenMap;

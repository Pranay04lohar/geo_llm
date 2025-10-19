"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  FaTrashAlt,
  FaTimes,
  FaPlus,
  FaMinus,
  FaCompass,
} from "react-icons/fa";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "https://geollm-backend-hbdccjdfhhdphyfx.canadacentral-01.azurewebsites.net";

// Debounce utility
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function FullScreenMap({ roiData, analysisData, onClose, onExport }) {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [mapError, setMapError] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawingCoords, setDrawingCoords] = useState([]);
  const [mapStyle, setMapStyle] = useState("map"); // 'satellite' or 'map'
  const [roiList, setRoiList] = useState(roiData || []);
  const [roiCounter, setRoiCounter] = useState((roiData?.length || 0) + 1);
  const [hoverInfo, setHoverInfo] = useState(null);
  const [showLegend, setShowLegend] = useState(true);

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

  // LST sampling cache and utilities
  const lstCacheRef = useRef(new Map());
  const keyFromLngLat = (lng, lat) => `${lng.toFixed(4)},${lat.toFixed(4)}`;

  const fetchLSTSample = async (lng, lat) => {
    try {
      const key = keyFromLngLat(lng, lat);
      if (lstCacheRef.current.has(key)) {
        return lstCacheRef.current.get(key);
      }

      const resp = await fetch(`${API_BASE}/lst/sample`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lng,
          lat,
          startDate: "2024-01-01",
          endDate: "2024-08-31",
          scale: 1000,
        }),
      });

      if (!resp.ok) return null;
      const data = await resp.json();
      lstCacheRef.current.set(key, data);
      return data;
    } catch (e) {
      console.error("LST sample error:", e);
      return null;
    }
  };

  // NDVI sampling cache and helper
  const ndviCacheRef = useRef(new Map());
  const fetchNDVISample = async (lng, lat) => {
    try {
      const key = keyFromLngLat(lng, lat);
      if (ndviCacheRef.current.has(key)) return ndviCacheRef.current.get(key);

      const resp = await fetch(`${API_BASE}/ndvi/sample`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lng,
          lat,
          startDate: "2024-01-01",
          endDate: "2024-08-31",
          scale: 30,
          cloudThreshold: 20,
        }),
      });
      if (!resp.ok) return null;
      const data = await resp.json();
      ndviCacheRef.current.set(key, data);
      return data;
    } catch (e) {
      console.error("NDVI sample error:", e);
      return null;
    }
  };

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
      console.warn(
        "Google Maps API key not found. Please add NEXT_PUBLIC_GOOGLE_MAPS_API_KEY to your .env.local file"
      );
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
      console.warn(
        "Google Maps API key not found. Please add NEXT_PUBLIC_GOOGLE_MAPS_API_KEY to your .env.local file"
      );
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
      osm: {
        type: "raster",
        tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
        tileSize: 256,
        attribution: "© OpenStreetMap contributors",
        maxzoom: 19,
      },
    },
    layers: [
      {
        id: "osm-layer",
        type: "raster",
        source: "osm",
        paint: {
          "raster-opacity": 1.0,
        },
      },
    ],
  });

  const createFallbackSatelliteStyle = () => ({
    version: 8,
    sources: {
      "esri-satellite": {
        type: "raster",
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
        attribution: "© Esri",
        maxzoom: 19,
      },
    },
    layers: [
      {
        id: "esri-satellite-layer",
        type: "raster",
        source: "esri-satellite",
        paint: {
          "raster-opacity": 1.0,
        },
      },
    ],
  });

  const getCurrentMapStyle = useCallback(() => {
    return mapStyle === "satellite"
      ? createGoogleSatelliteStyle()
      : createGoogleMapStyle();
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

  // Simplified ROI styling - no blur effects to prevent WebGL issues
  const getROIStyle = (color) => ({
    fill: {
      "fill-color": color,
      "fill-opacity": 0.1,
    },
    stroke: {
      "line-color": color,
      "line-width": 2,
      "line-opacity": 0.8,
    },
  });

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
    map.current
      .getSource("drawing")
      .setData({ type: "FeatureCollection", features });
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
      maxZoom: 18, // Reduced max zoom to prevent WebGL issues
      preserveDrawingBuffer: true, // Helps with WebGL context
      antialias: false, // Disable antialiasing to improve performance
      failIfMajorPerformanceCaveat: false, // Allow fallback rendering
    });

    map.current.setMaxBounds(indiaBounds);

    map.current.on("load", () => {
      setMapLoaded(true);
      setupDrawingLayers();
      setupAnalysisLayers();
    });

    map.current.on("error", (e) => {
      console.error("Map error:", e);
      if (e.error && e.error.message && e.error.message.includes("WebGL")) {
        setMapError("WebGL rendering issue detected. Try refreshing the page.");
      } else {
        setMapError(
          "Failed to load map. Please check your internet connection."
        );
      }
    });

    // Handle WebGL context loss
    map.current.on("webglcontextlost", (e) => {
      console.warn("WebGL context lost, attempting recovery...");
      e.preventDefault();
    });

    map.current.on("webglcontextrestored", () => {
      console.log("WebGL context restored");
      setMapError(null);
    });

    // Add hover interactions for analysis layer
    map.current.on("mousemove", "analysis-tile-layer", (e) => {
      if (analysisData) {
        const coordinates = [e.lngLat.lng, e.lngLat.lat];
        const analysisType = analysisData.analysis_type || "analysis";
        const serviceUsed = analysisData.service_used || "GEE";

        // Create hover info based on analysis type
        let hoverData = {
          coordinates,
          analysisType,
          serviceUsed,
          location: analysisData.roi?.display_name || "Analysis Area",
        };

        // Add specific data based on analysis type
        if (analysisType === "water") {
          hoverData.title = "Water Analysis";
          hoverData.description = "Satellite-derived water detection";
          hoverData.data = {
            "Water Coverage": analysisData.water_percentage
              ? `${analysisData.water_percentage}%`
              : "Calculating...",
            "Non-Water": analysisData.non_water_percentage
              ? `${analysisData.non_water_percentage}%`
              : "Calculating...",
            "Data Source": "JRC Global Surface Water",
            Resolution: "30m",
            "Time Period": "2023",
          };
        } else if (analysisType === "ndvi") {
          hoverData.title = "Vegetation Analysis (NDVI)";
          hoverData.description = "Normalized Difference Vegetation Index";
          hoverData.data = {
            "Mean NDVI": analysisData.mean_ndvi
              ? analysisData.mean_ndvi.toFixed(3)
              : "Calculating...",
            "Vegetation Health":
              analysisData.mean_ndvi > 0.5
                ? "High"
                : analysisData.mean_ndvi > 0.3
                ? "Medium"
                : "Low",
            "Data Source": "Landsat 8/9",
            Resolution: "30m",
            "Time Period": "2023",
          };
        } else if (analysisType === "lst") {
          // For LST, fetch real-time value at cursor position
          hoverData.title = "Land Surface Temperature";
          hoverData.description = "Thermal analysis of surface temperature";
          hoverData.data = {
            LST: "Sampling...",
            "Data Source": "MODIS/061/MOD11A2",
            Resolution: "1000m",
            "Time Period": "2024",
          };

          // Fetch LST sample at this point
          fetchLSTSample(e.lngLat.lng, e.lngLat.lat).then((sampleData) => {
            if (sampleData) {
              hoverData.data["LST"] = `${sampleData.value_celsius.toFixed(
                1
              )}°C`;
              hoverData.data["Quality"] =
                sampleData.quality?.score != null
                  ? `${Math.round(sampleData.quality.score * 100)}%`
                  : "90%";
              setHoverInfo({ ...hoverData });
            }
          });
        } else if (analysisType === "lulc") {
          hoverData.title = "Land Use/Land Cover";
          hoverData.description = "Classification of land cover types";
          hoverData.data = {
            "Primary Class": analysisData.primary_class || "Analyzing...",
            Confidence: analysisData.confidence
              ? `${(analysisData.confidence * 100).toFixed(1)}%`
              : "Calculating...",
            "Data Source": "Dynamic World",
            Resolution: "10m",
            "Time Period": "2023",
          };
        }

        setHoverInfo(hoverData);
      }
    });

    // Clear hover info when mouse leaves analysis layer
    map.current.on("mouseleave", "analysis-tile-layer", () => {
      setHoverInfo(null);
    });

    // Change cursor when hovering over analysis layer
    map.current.on("mouseenter", "analysis-tile-layer", () => {
      map.current.getCanvas().style.cursor = "pointer";
    });

    map.current.on("mouseleave", "analysis-tile-layer", () => {
      map.current.getCanvas().style.cursor = "";
    });

    // Add click functionality for detailed analysis
    map.current.on("click", "analysis-tile-layer", (e) => {
      if (analysisData) {
        const coordinates = [e.lngLat.lng, e.lngLat.lat];
        console.log("Analysis clicked at:", coordinates);

        // You can add more detailed click functionality here
        // For example, opening a detailed analysis modal or showing more data
        alert(
          `Analysis clicked!\nCoordinates: ${coordinates[1].toFixed(
            4
          )}°N, ${coordinates[0].toFixed(4)}°E\nAnalysis Type: ${
            analysisData.analysis_type
          }`
        );
      }
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
      setupAnalysisLayers();
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
  }, [
    mapStyle,
    roiList,
    analysisData,
    updateDrawing,
    handleMapClick,
    finishDrawing,
  ]);

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

        const style = getROIStyle(roi.color);

        // Add fill
        map.current.addLayer({
          id: `${roi.id}-fill`,
          type: "fill",
          source: roi.id,
          paint: style.fill,
        });

        // Add stroke
        map.current.addLayer({
          id: `${roi.id}-stroke`,
          type: "line",
          source: roi.id,
          paint: style.stroke,
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

    // Add fill
    map.current.addLayer({
      id: "polygon-fill",
      type: "fill",
      source: "drawing",
      paint: {
        "fill-color": "#ff6b35",
        "fill-opacity": 0.3,
      },
    });

    // Add stroke
    map.current.addLayer({
      id: "polygon-stroke",
      type: "line",
      source: "drawing",
      paint: {
        "line-color": "#ff6b35",
        "line-width": 3,
        "line-opacity": 0.8,
      },
    });

    // Add vertices
    map.current.addLayer({
      id: "polygon-vertices",
      type: "circle",
      source: "drawing",
      paint: {
        "circle-radius": 6,
        "circle-color": "#ff6b35",
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 2,
      },
      filter: ["==", "$type", "Point"],
    });
  };

  const setupAnalysisLayers = useCallback(() => {
    try {
      if (!analysisData || !map.current) return;

      const analysisType = (analysisData?.analysis_type || "").toLowerCase();

      // Add raster analysis tile overlay if available
      const tileUrl =
        analysisData?.tile_url ||
        analysisData?.urlFormat ||
        analysisData?.visualization?.tile_url ||
        analysisData?.visualization?.urlFormat ||
        analysisData?.visualization?.url;
      if (tileUrl) {
        console.log(
          "FullScreenMap: adding analysis raster with tileUrl:",
          tileUrl
        );
        // Remove previous if reloading
        if (map.current.getLayer("analysis-tile-layer")) {
          map.current.removeLayer("analysis-tile-layer");
        }
        if (map.current.getSource("analysis-tile")) {
          map.current.removeSource("analysis-tile");
        }

        map.current.addSource("analysis-tile", {
          type: "raster",
          tiles: [tileUrl],
          tileSize: 256,
        });
        map.current.addLayer({
          id: "analysis-tile-layer",
          type: "raster",
          source: "analysis-tile",
          paint: { "raster-opacity": 0.85, "raster-fade-duration": 0 },
        });
        try {
          map.current.setLayoutProperty(
            "analysis-tile-layer",
            "visibility",
            "visible"
          );
        } catch (e) {}

        // Debug: log sources and layers after add
        try {
          const style = map.current.getStyle();
          console.log(
            "FullScreenMap: sources keys:",
            Object.keys(style.sources)
          );
          console.log(
            "FullScreenMap: has analysis source:",
            !!map.current.getSource("analysis-tile")
          );
          console.log(
            "FullScreenMap: has analysis layer:",
            !!map.current.getLayer("analysis-tile-layer")
          );
        } catch (e) {}

        // Listen for tile errors
        map.current.on("error", (ev) => {
          if (ev?.sourceId === "analysis-tile") {
            console.warn("FullScreenMap: raster source error:", ev);
          }
        });

        // Ensure raster sits below ROI layers if present (so borders are visible)
        try {
          const firstRoiId = roiList?.[0]?.id;
          if (firstRoiId && map.current.getLayer(`${firstRoiId}-fill`)) {
            map.current.moveLayer("analysis-tile-layer", `${firstRoiId}-fill`);
          }
        } catch (e) {
          console.warn("FullScreenMap: could not reorder raster layer:", e);
        }
      } else {
        console.warn("FullScreenMap: No tile URL present on analysisData");
      }

      // NDVI: load vector grid for instant hover
      if (analysisType === "ndvi" && analysisData?.roi_geojson) {
        const roiGeometry =
          analysisData.roi_geojson.geometry || analysisData.roi_geojson;

        fetch(`${API_BASE}/ndvi/grid`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            roi: roiGeometry,
            cellSizeKm: 1.0,
            startDate: "2024-01-01",
            endDate: "2024-08-31",
            scale: 30,
            cloudThreshold: 20,
          }),
        })
          .then((r) => r.json())
          .then((gridData) => {
            if (!gridData?.features) return;

            if (!map.current.getSource("ndvi-grid")) {
              map.current.addSource("ndvi-grid", {
                type: "geojson",
                data: gridData,
              });

              map.current.addLayer({
                id: "ndvi-grid-fill",
                type: "fill",
                source: "ndvi-grid",
                paint: {
                  "fill-color": [
                    "interpolate",
                    ["linear"],
                    ["get", "mean_ndvi"],
                    -0.2,
                    "#d73027",
                    0.0,
                    "#fdae61",
                    0.2,
                    "#fee08b",
                    0.4,
                    "#abdda4",
                    0.6,
                    "#66c2a5",
                    0.8,
                    "#3288bd",
                  ],
                  "fill-opacity": 0.3,
                },
              });

              map.current.addLayer({
                id: "ndvi-grid-outline",
                type: "line",
                source: "ndvi-grid",
                paint: {
                  "line-color": "#888",
                  "line-width": 0.5,
                  "line-opacity": 0.4,
                },
              });
            } else {
              map.current.getSource("ndvi-grid").setData(gridData);
            }
          })
          .catch((e) => console.error("Failed to load NDVI grid:", e));

        // Tooltip element
        let tooltip = document.getElementById("fs-ndvi-tooltip");
        if (!tooltip) {
          tooltip = document.createElement("div");
          tooltip.id = "fs-ndvi-tooltip";
          tooltip.style.pointerEvents = "none";
          tooltip.style.position = "fixed";
          tooltip.style.zIndex = "999999";
          tooltip.style.background = "white";
          tooltip.style.border = "1px solid #ddd";
          tooltip.style.borderRadius = "6px";
          tooltip.style.boxShadow = "0 6px 12px rgba(0,0,0,0.15)";
          tooltip.style.padding = "8px 12px";
          tooltip.style.fontSize = "12px";
          tooltip.style.display = "none";
          document.body.appendChild(tooltip);
        }

        const updateTooltip = (x, y, info) => {
          if (!info) {
            tooltip.style.display = "none";
            return;
          }
          const valueStr =
            typeof info.value === "number" ? info.value.toFixed(3) : "-";
          const typeStr = info.vegetation_type
            ? `<br/><strong>Type:</strong> ${info.vegetation_type}`
            : "";
          const srcStr = info.fromGrid
            ? "<small style='color:#666'>📍 1km grid</small>"
            : "<small style='color:#666'>🎯 precise (30m)</small>";
          tooltip.innerHTML = `<strong>NDVI:</strong> ${valueStr}${typeStr}<br/>${srcStr}`;
          tooltip.style.left = `${x + 15}px`;
          tooltip.style.top = `${y + 15}px`;
          tooltip.style.display = "block";
        };

        const debouncedSample = debounce(async (lng, lat, x, y) => {
          const data = await fetchNDVISample(lng, lat);
          if (!data) return;
          updateTooltip(x, y, {
            value: data.value_ndvi,
            vegetation_type: data.vegetation_type,
            fromGrid: false,
          });
        }, 300);

        // Hover handler
        map.current.on("mousemove", (e) => {
          if (!map.current.getLayer("ndvi-grid-fill")) return;
          const features = map.current.queryRenderedFeatures(e.point, {
            layers: ["ndvi-grid-fill"],
          });
          if (features && features.length) {
            const p = features[0].properties || {};
            const value = Number(p.mean_ndvi);
            updateTooltip(e.originalEvent.clientX, e.originalEvent.clientY, {
              value,
              vegetation_type: p.vegetation_type,
              fromGrid: true,
            });
          } else {
            // fallback precise sampling
            debouncedSample(
              e.lngLat.lng,
              e.lngLat.lat,
              e.originalEvent.clientX,
              e.originalEvent.clientY
            );
          }
        });

        map.current.on("mouseleave", () => {
          const el = document.getElementById("fs-ndvi-tooltip");
          if (el) el.style.display = "none";
        });
      }
    } catch (e) {
      console.error("setupAnalysisLayers error:", e);
    }
  }, [analysisData]);

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
            <div className="flex items-center gap-2">
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

              {analysisData && (
                <button
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    showLegend
                      ? "bg-green-600 text-white"
                      : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                  }`}
                  onClick={() => setShowLegend(!showLegend)}
                >
                  Legend
                </button>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
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
      <div className="absolute top-20 right-4 z-10 flex flex-col gap-2">
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
          <p className="text-sm">
            Click to add points. Double-click to finish.
          </p>
        </div>
      )}

      {/* Hover Tooltip */}
      {hoverInfo && (
        <div className="absolute top-20 left-4 z-20 bg-white/95 backdrop-blur-sm rounded-lg p-4 max-w-sm shadow-lg border border-gray-200">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">
              {hoverInfo.analysisType === "water"
                ? "💧"
                : hoverInfo.analysisType === "ndvi"
                ? "🌱"
                : hoverInfo.analysisType === "lst"
                ? "🌡️"
                : hoverInfo.analysisType === "lulc"
                ? "🏞️"
                : "📊"}
            </span>
            <h3 className="font-semibold text-gray-800">{hoverInfo.title}</h3>
          </div>
          <p className="text-sm text-gray-600 mb-3">{hoverInfo.description}</p>
          <div className="space-y-1">
            {Object.entries(hoverInfo.data).map(([key, value]) => (
              <div key={key} className="flex justify-between text-sm">
                <span className="text-gray-600">{key}:</span>
                <span className="font-medium text-gray-800">{value}</span>
              </div>
            ))}
          </div>
          <div className="mt-3 pt-2 border-t border-gray-200">
            <div className="text-xs text-gray-500">
              <div>Location: {hoverInfo.location}</div>
              <div>Service: {hoverInfo.serviceUsed}</div>
              <div>
                Coordinates: {hoverInfo.coordinates[1].toFixed(4)}°N,{" "}
                {hoverInfo.coordinates[0].toFixed(4)}°E
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Analysis Legend */}
      {analysisData && showLegend && (
        <div className="absolute bottom-4 right-4 z-10 bg-white/95 backdrop-blur-sm rounded-lg p-4 max-w-xs shadow-lg border border-gray-200">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-800">Analysis Legend</h3>
            <button
              onClick={() => setShowLegend(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              <FaTimes size={12} />
            </button>
          </div>

          {analysisData.analysis_type === "water" && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-blue-500 rounded"></div>
                <span className="text-sm text-gray-700">Water Bodies</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-gray-300 rounded"></div>
                <span className="text-sm text-gray-700">Land/Non-Water</span>
              </div>
              <div className="text-xs text-gray-500 mt-2">
                <div>Data: JRC Global Surface Water</div>
                <div>Resolution: 30m</div>
                <div>Hover for details</div>
              </div>
            </div>
          )}

          {analysisData.analysis_type === "ndvi" && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-green-600 rounded"></div>
                <span className="text-sm text-gray-700">High Vegetation</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-yellow-500 rounded"></div>
                <span className="text-sm text-gray-700">Medium Vegetation</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-red-500 rounded"></div>
                <span className="text-sm text-gray-700">Low Vegetation</span>
              </div>
              <div className="text-xs text-gray-500 mt-2">
                <div>Data: Landsat 8/9 NDVI</div>
                <div>Resolution: 30m</div>
                <div>Hover for details</div>
              </div>
            </div>
          )}

          {analysisData.analysis_type === "lst" && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-red-600 rounded"></div>
                <span className="text-sm text-gray-700">Hot Areas</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-yellow-500 rounded"></div>
                <span className="text-sm text-gray-700">
                  Moderate Temperature
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-blue-500 rounded"></div>
                <span className="text-sm text-gray-700">Cool Areas</span>
              </div>
              <div className="text-xs text-gray-500 mt-2">
                <div>Data: Landsat Thermal</div>
                <div>Resolution: 100m</div>
                <div>Hover for details</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ROI List */}
      {roiList.length > 0 && (
        <div className="absolute bottom-4 left-4 z-10 bg-white/95 backdrop-blur-sm rounded-lg p-4 max-w-sm max-h-64 overflow-y-auto">
          <h3 className="font-semibold text-gray-800 mb-2">
            Active ROIs ({roiList.length})
          </h3>
          {roiList.map((roi) => (
            <div
              key={roi.id}
              className="flex items-center gap-2 mb-2 p-2 bg-gray-50 rounded"
            >
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

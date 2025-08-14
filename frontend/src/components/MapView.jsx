"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { FaTrashAlt } from "react-icons/fa";
import "../styles/MapView.css";

function App() {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const [roiList, setRoiList] = useState([]); // Array of ROI objects with id, name, and geojson
  const [roiCounter, setRoiCounter] = useState(1); // Counter for ROI naming
  const [mapLoaded, setMapLoaded] = useState(false);
  const [mapError, setMapError] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawingCoords, setDrawingCoords] = useState([]);
  const [mapStyle, setMapStyle] = useState("satellite"); // 'satellite' or 'map'

  // Refs to hold the latest state for map event listeners to prevent stale closures
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
  const [zoom] = useState(1);

  // Expanded bounds
  const indiaBounds = [
    [50.0, 0.0],
    [110.0, 45.0],
  ];

  // --- Map Style Definitions ---
  const createGoogleSatelliteStyle = () => {
    const googleMapsApiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    if (
      !googleMapsApiKey ||
      googleMapsApiKey === "your_google_maps_api_key_here"
    ) {
      return createOpenStreetMapStyle();
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

  const createGoogleMapStyle = () => {
    const googleMapsApiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    if (
      !googleMapsApiKey ||
      googleMapsApiKey === "your_google_maps_api_key_here"
    ) {
      return createOpenStreetMapStyle();
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

  const createOpenStreetMapStyle = () => ({
    version: 8,
    sources: {
      osm: {
        type: "raster",
        tiles: ["https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"],
        tileSize: 256,
        attribution: "© OpenStreetMap",
      },
    },
    layers: [{ id: "osm-layer", type: "raster", source: "osm" }],
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

  // --- Drawing Logic ---

  const updateDrawing = useCallback((coords, isComplete) => {
    if (!map.current || !map.current.getSource("drawing")) return;

    const features = [];
    if (coords.length > 0) {
      if (isComplete && coords.length > 0 && coords[0].length > 3) {
        // coords is an array of coordinate arrays for completed polygon
        features.push({
          type: "Feature",
          properties: {},
          geometry: { type: "Polygon", coordinates: coords },
        });
        console.log("Added completed polygon to map with coordinates:", coords);
      } else if (!isComplete) {
        // coords is a flat array of coordinates for incomplete drawing
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
      console.log("Map clicked, isDrawing:", isDrawingRef.current);
      if (!isDrawingRef.current) return;

      const coords = [e.lngLat.lng, e.lngLat.lat];

      // Check for duplicate points (within a small tolerance for precision)
      const tolerance = 0.00001; // roughly 1 meter
      const isDuplicate = drawingCoordsRef.current.some(
        (existingCoord) =>
          Math.abs(existingCoord[0] - coords[0]) < tolerance &&
          Math.abs(existingCoord[1] - coords[1]) < tolerance
      );

      if (isDuplicate) {
        console.log("Duplicate point detected, ignoring:", coords);
        return;
      }

      console.log("Adding point:", coords);
      const newCoords = [...drawingCoordsRef.current, coords];
      setDrawingCoords(newCoords);
      updateDrawing(newCoords, false);
    },
    [updateDrawing]
  );

  const finishDrawing = useCallback(
    (e) => {
      console.log(
        "Double-click detected, current coords:",
        drawingCoordsRef.current.length
      );
      if (!isDrawingRef.current || drawingCoordsRef.current.length < 3) {
        console.log("Not enough points to finish polygon");
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

      console.log("Finishing polygon:", polygon);

      // Prompt user for ROI name
      const defaultName = `ROI ${roiCounter}`;
      const userInput = window.prompt(`Name your ROI polygon:`, defaultName);

      // If user cancels, don't create the ROI
      if (userInput === null) {
        console.log("ROI creation cancelled by user");
        setIsDrawing(false);
        setDrawingCoords([]);
        map.current.getCanvas().style.cursor = "";
        map.current.off("click", handleMapClick);
        map.current.off("dblclick", finishDrawing);
        updateDrawing([], false);
        return;
      }

      // Use provided name or default if empty
      const roiName = userInput.trim() || defaultName;

      // Create new ROI object with current counter value
      const currentCounter = roiCounter;
      const newROI = {
        id: `roi-${currentCounter}`,
        name: roiName,
        geojson: polygon,
        color: getROIColor(currentCounter),
      };

      // Add to ROI list and increment counter
      setRoiList((prev) => {
        console.log(
          `Adding ${newROI.name} to ROI list. Current list length: ${prev.length}`
        );
        return [...prev, newROI];
      });
      setRoiCounter((prev) => {
        const newCounter = prev + 1;
        console.log(`ROI counter updated from ${prev} to ${newCounter}`);
        return newCounter;
      });

      console.log(
        `Created ${newROI.name} with ID ${newROI.id} and color ${newROI.color}`
      );

      setIsDrawing(false);
      setDrawingCoords([]);

      map.current.getCanvas().style.cursor = "";
      map.current.off("click", handleMapClick);
      map.current.off("dblclick", finishDrawing);

      // Clear the drawing source since we now have a completed ROI
      updateDrawing([], false);
    },
    [updateDrawing, handleMapClick, roiCounter]
  );

  // --- Map Initialization and Style Switching ---

  useEffect(() => {
    if (map.current) return; // initialize map only once

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: getCurrentMapStyle(),
      center: [lng, lat],
      zoom: zoom,
      minZoom: 1,
      maxZoom: 18,
    });

    map.current.setMaxBounds(indiaBounds);

    map.current.on("load", () => {
      setMapLoaded(true);
      setupDrawingLayers();
    });

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    const onStyleLoad = () => {
      console.log("Map style changed, setting up layers...");
      setupDrawingLayers();

      // If we were in drawing mode, re-attach events
      if (isDrawingRef.current) {
        map.current.getCanvas().style.cursor = "crosshair";
        map.current.on("click", handleMapClick);
        map.current.on("dblclick", finishDrawing);

        if (drawingCoordsRef.current.length > 0) {
          updateDrawing(drawingCoordsRef.current, false);
        }
      }

      // The ROI display useEffect will handle restoring ROI layers
      console.log("Style load complete, ROI useEffect will restore polygons");
    };

    map.current.once("style.load", onStyleLoad); // ensure only one listener
    map.current.setStyle(getCurrentMapStyle());

    return () => {
      if (map.current) {
        map.current.off("style.load", onStyleLoad);
      }
    };
  }, [mapStyle, roiList, updateDrawing, handleMapClick, finishDrawing]);

  // Effect to display multiple ROI polygons
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    console.log(`ROI display effect triggered. Total ROIs: ${roiList.length}`);
    roiList.forEach((roi) => console.log(`- ${roi.name} (${roi.id})`));

    // Remove layers for ROIs that no longer exist
    const currentRoiIds = roiList.map((roi) => roi.id);
    const mapSources = map.current.getStyle().sources;

    Object.keys(mapSources).forEach((sourceId) => {
      if (sourceId.startsWith("roi-") && !currentRoiIds.includes(sourceId)) {
        // Remove layers for this ROI
        if (map.current.getLayer(`${sourceId}-fill`))
          map.current.removeLayer(`${sourceId}-fill`);
        if (map.current.getLayer(`${sourceId}-stroke`))
          map.current.removeLayer(`${sourceId}-stroke`);
        if (map.current.getSource(sourceId)) map.current.removeSource(sourceId);
        console.log(`Cleaned up ${sourceId} from map`);
      }
    });

    // Add all ROI polygons from the list
    roiList.forEach((roi) => {
      if (!map.current.getSource(roi.id)) {
        map.current.addSource(roi.id, {
          type: "geojson",
          data: roi.geojson,
        });

        // Add layers for this ROI
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

        console.log(`${roi.name} displayed on map with color ${roi.color}`);
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
    if (!mapLoaded || !map.current) {
      console.log("Map not ready for drawing");
      return;
    }

    // Multiple ROIs are supported, so no confirmation needed

    // Ensure drawing layers exist
    if (!map.current.getSource("drawing")) {
      console.log("Setting up drawing layers...");
      setupDrawingLayers();
    }

    console.log("Starting drawing mode");
    setIsDrawing(true);
    setDrawingCoords([]);
    map.current.getCanvas().style.cursor = "crosshair";
    updateDrawing([], false);

    // Remove any existing listeners first to prevent duplicates
    map.current.off("click", handleMapClick);
    map.current.off("dblclick", finishDrawing);

    // Add new listeners
    map.current.on("click", handleMapClick);
    map.current.on("dblclick", finishDrawing);
  };

  const cancelDrawing = () => {
    if (!mapLoaded || !map.current) return;
    console.log("Canceling drawing mode");
    setIsDrawing(false);
    setDrawingCoords([]);
    updateDrawing([], false);
    map.current.getCanvas().style.cursor = "";
    map.current.off("click", handleMapClick);
    map.current.off("dblclick", finishDrawing);
  };

  const renameROI = (roiId) => {
    const roi = roiList.find((r) => r.id === roiId);
    if (!roi) return;

    const newName = window.prompt(`Rename "${roi.name}" to:`, roi.name);

    if (newName === null || newName.trim() === roi.name) {
      return; // User cancelled or no change
    }

    const finalName = newName.trim() || roi.name;
    console.log(`Renaming ${roi.name} to ${finalName}`);

    setRoiList((prev) =>
      prev.map((r) => (r.id === roiId ? { ...r, name: finalName } : r))
    );
  };

  const removeROI = (roiId) => {
    if (!map.current) return;

    // Find the ROI to get its name for logging
    const roiToRemove = roiList.find((roi) => roi.id === roiId);
    const roiName = roiToRemove ? roiToRemove.name : roiId;

    console.log(`Removing ${roiName} (${roiId})`);

    // Remove from map layers immediately
    if (map.current.getLayer(`${roiId}-fill`)) {
      map.current.removeLayer(`${roiId}-fill`);
      console.log(`Removed ${roiId}-fill layer`);
    }
    if (map.current.getLayer(`${roiId}-stroke`)) {
      map.current.removeLayer(`${roiId}-stroke`);
      console.log(`Removed ${roiId}-stroke layer`);
    }
    if (map.current.getSource(roiId)) {
      map.current.removeSource(roiId);
      console.log(`Removed ${roiId} source`);
    }

    // Remove from state
    setRoiList((prev) => {
      const newList = prev.filter((roi) => roi.id !== roiId);
      console.log(`ROI list updated. Remaining ROIs: ${newList.length}`);
      return newList;
    });
  };

  const clearAll = () => {
    if (!mapLoaded) return;
    console.log("Clearing all ROI data");
    cancelDrawing();
    setRoiList([]);
    setRoiCounter(1);
  };

  const exportROI = () => {
    if (roiList.length === 0) {
      alert("No ROI polygons drawn yet.");
      return;
    }

    console.log(
      `=== Exporting ${roiList.length} ROI${roiList.length > 1 ? "s" : ""} ===`
    );

    const exportData = {
      type: "FeatureCollection",
      features: roiList.map((roi) => {
        // Create clean coordinates without duplicate closing point
        const originalCoords = roi.geojson.geometry.coordinates[0].slice(0, -1);
        return {
          ...roi.geojson,
          properties: {
            name: roi.name,
            id: roi.id,
            color: roi.color,
          },
          geometry: {
            ...roi.geojson.geometry,
            coordinates: [originalCoords],
          },
        };
      }),
    };

    console.log("All ROIs Export (clean coordinates):");
    console.log(JSON.stringify(exportData, null, 2));

    // Individual ROI summaries
    roiList.forEach((roi) => {
      const originalCoords = roi.geojson.geometry.coordinates[0].slice(0, -1);
      console.log(
        `${roi.name}: ${originalCoords.length} vertices, color: ${roi.color}`
      );
    });
  };

  return (
    <div className="app">
      <div className="controls">
        {mapLoaded && (
          <>
            <button className="btn btn-info" onClick={toggleMapStyle}>
              {mapStyle === "satellite" ? "🗺️ Map View" : "🛰️ Satellite View"}
            </button>
            <button
              className={`btn ${isDrawing ? "btn-warning" : "btn-secondary"}`}
              onClick={isDrawing ? cancelDrawing : startDrawing}
            >
              {isDrawing ? "❌ Cancel Drawing" : `✏️ Draw ROI ${roiCounter}`}
            </button>
          </>
        )}
        <button
          className="btn btn-primary"
          onClick={exportROI}
          disabled={roiList.length === 0}
        >
          📤 Export All ROIs ({roiList.length})
        </button>
        <button className="btn" onClick={clearAll} disabled={!mapLoaded}>
          <FaTrashAlt /> Clear All
        </button>
      </div>

      {mapError && (
        <div className="error">
          <p>Error loading map: {mapError}</p>
        </div>
      )}

      {!mapLoaded && !mapError && (
        <div className="loading">
          <p>Loading map...</p>
        </div>
      )}

      {isDrawing && (
        <div className="drawing-instructions">
          <p>✏️ Drawing Mode: Click to add points. Double-click to finish.</p>
        </div>
      )}

      {roiList.length > 0 && (
        <div className="roi-list">
          <h3>Active ROIs ({roiList.length})</h3>
          {roiList.map((roi) => (
            <div key={roi.id} className="roi-item">
              <span
                className="roi-color"
                style={{ backgroundColor: roi.color }}
              ></span>
              <span
                className="roi-name"
                onClick={() => renameROI(roi.id)}
                title={`Click to rename ${roi.name}`}
              >
                {roi.name}
              </span>
              <button
                className="roi-delete"
                onClick={() => {
                  if (
                    window.confirm(
                      `Are you sure you want to delete "${roi.name}"?`
                    )
                  ) {
                    removeROI(roi.id);
                  }
                }}
                title={`Delete ${roi.name}`}
              >
                <FaTrashAlt />
              </button>
            </div>
          ))}
        </div>
      )}

      <div ref={mapContainer} style={{ width: "100%", height: "100vh" }} />
    </div>
  );
}

export default App;

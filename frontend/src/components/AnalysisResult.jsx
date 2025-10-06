"use client";

import { useState, useRef, useEffect } from "react";
import * as turf from "@turf/turf";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { FaExpand, FaEye, FaEyeSlash } from "react-icons/fa";
import FullScreenMap from "./FullScreenMap";

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

// Point-in-polygon test (ray casting)
function isPointInPolygon(lng, lat, coords) {
  let inside = false;
  for (let i = 0, j = coords.length - 1; i < coords.length; j = i++) {
    const xi = coords[i][0],
      yi = coords[i][1];
    const xj = coords[j][0],
      yj = coords[j][1];

    const intersect =
      yi > lat !== yj > lat && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

// Clean up all orphaned tooltips from DOM
function cleanupAllTooltips() {
  const tooltips = document.querySelectorAll("[id^='lst-hover-tooltip']");
  tooltips.forEach((tooltip) => {
    if (tooltip.parentNode) {
      tooltip.parentNode.removeChild(tooltip);
    }
  });
}

export default function AnalysisResult({ content }) {
  // Parse map data from content if it exists
  const mapDataMatch = content.match(/\[MAP_DATA:(.*?)\]$/);
  const hasMapData = mapDataMatch !== null;
  const mapData = hasMapData ? JSON.parse(mapDataMatch[1]) : null;
  const textContent = hasMapData
    ? content.replace(/\[MAP_DATA:.*?\]$/, "").trim()
    : content;
  const debugEnabled = process.env.NEXT_PUBLIC_DEBUG_MAP === "1";

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
  const [showFullScreenMap, setShowFullScreenMap] = useState(false);
  const [hoverInfo, setHoverInfo] = useState(null);
  const [gridLoaded, setGridLoaded] = useState(false);
  const initialError =
    mapData?.error ||
    (mapData?.limit_exceeded
      ? `Area too large: ${
          mapData.area_km2 != null ? mapData.area_km2.toLocaleString() : ""
        } km² > ${
          mapData.limit_km2 != null
            ? mapData.limit_km2.toLocaleString()
            : "limit"
        }`
      : null);
  const [errorMessage, setErrorMessage] = useState(initialError);
  const mapContainer = useRef(null);
  const map = useRef(null);
  const lstGridData = useRef(null); // Store LST grid for instant hover

  // Initialize map when showMap becomes true
  useEffect(() => {
    if (!showMap || !hasMapData || !mapContainer.current) return;
    if (map.current) return; // Prevent re-initialization

    // Clean up any orphaned tooltips before initializing
    cleanupAllTooltips();

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

        // If backend sent an error in analysis data, show it prominently
        if (mapData?.error) {
          setErrorMessage(mapData.error);
        }

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

            // Add a near-invisible ROI fill layer for reliable hit-testing
            if (!map.current.getLayer("roi-hit")) {
              map.current.addLayer({
                id: "roi-hit",
                type: "fill",
                source: "roi",
                paint: {
                  "fill-color": "#ff0000",
                  "fill-opacity": 0.001,
                },
              });
            }

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

        // Load vector grid for instant hover (LST or NDVI analysis)
        // Use analysis_type to determine which workflow is active
        const analysisType = mapData.analysis_type?.toLowerCase();
        if (
          (analysisType === "lst" || analysisType === "ndvi") &&
          mapData.roi?.geometry
        ) {
          const gridEndpoint =
            analysisType === "lst"
              ? "http://localhost:8000/lst/grid"
              : "http://localhost:8000/ndvi/grid";

          console.log(
            `🔷 Loading ${analysisType.toUpperCase()} vector grid for fast hover...`
          );
          setGridLoaded(false);

          fetch(gridEndpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              roi: mapData.roi.geometry,
              cellSizeKm: 1.0, // 1km grid cells
              startDate: "2024-01-01",
              endDate: "2024-08-31",
              scale: 1000,
            }),
          })
            .then((resp) => resp.json())
            .then((gridData) => {
              if (gridData.success && gridData.features) {
                lstGridData.current = gridData;

                // Add grid source (used for instant sampling). For NDVI we also visualize the grid fill;
                // for LST we avoid adding a fill to prevent the map from looking washed out.
                if (!map.current.getSource("lst-grid")) {
                  map.current.addSource("lst-grid", {
                    type: "geojson",
                    data: gridData,
                  });

                  // Only render the colored grid fill for NDVI; for LST keep the grid hidden (used just for sampling)
                  if (analysisType === "ndvi") {
                    const fillPaint = {
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
                    };

                    map.current.addLayer({
                      id: "lst-grid-fill",
                      type: "fill",
                      source: "lst-grid",
                      paint: fillPaint,
                    });
                  }

                  // Add outline layer
                  map.current.addLayer({
                    id: "lst-grid-outline",
                    type: "line",
                    source: "lst-grid",
                    paint: {
                      "line-color": "#888",
                      "line-width": 0.5,
                      "line-opacity": analysisType === "ndvi" ? 0.4 : 0.0,
                    },
                  });
                }

                setGridLoaded(true);
                console.log(`✅ Loaded ${gridData.features.length} grid cells`);
              }
            })
            .catch((err) => {
              console.error("Failed to load LST grid:", err);
            });
        }

        // Hover sampling tooltip for LST
        // Remove any existing tooltip first to prevent duplicates
        const existingTooltip = document.getElementById("lst-hover-tooltip");
        if (existingTooltip) {
          existingTooltip.remove();
        }

        const tooltip = document.createElement("div");
        tooltip.id = "lst-hover-tooltip";
        tooltip.style.pointerEvents = "none";
        tooltip.style.display = "none";
        tooltip.style.position = "fixed"; // Use fixed positioning relative to viewport
        tooltip.style.zIndex = "999999";
        tooltip.style.backgroundColor = "white";
        tooltip.style.color = "black";
        tooltip.style.padding = "10px 14px";
        tooltip.style.borderRadius = "8px";
        tooltip.style.boxShadow = "0 6px 12px rgba(0, 0, 0, 0.2)";
        tooltip.style.border = "2px solid #3b82f6";
        tooltip.style.fontSize = "13px";
        tooltip.style.lineHeight = "1.5";
        tooltip.style.maxWidth = "280px";
        tooltip.style.fontFamily = "system-ui, -apple-system, sans-serif";
        // Append to body instead of map container
        document.body.appendChild(tooltip);
        console.log("Tooltip element created and appended to body:", tooltip);

        const cache = new Map();
        // Snap to 200m grid cells to reduce API calls
        const keyFromLngLat = (lng, lat) => {
          const gridSize = 0.002; // ~200m at mid-latitudes
          const gridLng = Math.round(lng / gridSize) * gridSize;
          const gridLat = Math.round(lat / gridSize) * gridSize;
          return `${gridLng.toFixed(3)},${gridLat.toFixed(3)}`;
        };

        // Use a ref to track current hover info for immediate tooltip updates
        const currentInfoRef = { current: null };

        const updateTooltipContent = (info) => {
          if (info?.value != null) {
            const isNDVI = info.isNDVI || analysisType === "ndvi";
            const label = isNDVI ? "NDVI" : "LST";
            const unit = isNDVI ? "" : " °C";

            let content = `<div style="line-height: 1.6;">
              <strong>${label}:</strong> ${info.value.toFixed(
              isNDVI ? 3 : 1
            )}${unit}`;

            if (isNDVI && info.vegetation_type) {
              content += `<br/><strong>Type:</strong> ${info.vegetation_type}`;
            }

            if (info.fromGrid) {
              // Show grid cell stats
              content += `<br/><strong>Min:</strong> ${
                info.min?.toFixed(isNDVI ? 3 : 1) || "-"
              }${unit}
              <br/><strong>Max:</strong> ${
                info.max?.toFixed(isNDVI ? 3 : 1) || "-"
              }${unit}
              <br/><strong>Std Dev:</strong> ${
                info.std?.toFixed(isNDVI ? 3 : 1) || "-"
              }${unit}
              <br/><small style="color: #666;">📍 1km grid cell (instant)</small>`;
            } else {
              // Show point sample metadata
              content += `<br/><strong>Dataset:</strong> ${
                info.dataset || (isNDVI ? "Sentinel-2" : "MODIS")
              }
              <br/><strong>Date:</strong> ${info.dateRange || "2024"}`;
              if (info.quality) {
                content += `<br/><strong>Quality:</strong> ${info.quality}`;
              }
            }

            content += `</div>`;
            tooltip.innerHTML = content;
          } else if (info === null) {
            tooltip.innerHTML = "<div style='color: #999;'>Outside ROI</div>";
          } else {
            tooltip.innerHTML = "<div>Sampling...</div>";
          }
        };

        const sampleDebounced = debounce(async (lngLat) => {
          try {
            const key = keyFromLngLat(lngLat.lng, lngLat.lat);

            if (cache.has(key)) {
              const cached = cache.get(key);
              currentInfoRef.current = cached;
              updateTooltipContent(cached);
              return;
            }

            // Try to find grid cell first (instant, no API call)
            if (lstGridData.current?.features) {
              for (const feature of lstGridData.current.features) {
                if (
                  isPointInPolygon(
                    lngLat.lng,
                    lngLat.lat,
                    feature.geometry.coordinates[0]
                  )
                ) {
                  const props = feature.properties;
                  const isNDVI = analysisType === "ndvi";
                  const info = {
                    value: isNDVI ? props.mean_ndvi : props.mean_lst,
                    dataset: isNDVI ? "Sentinel-2" : "MODIS/061/MOD11A2",
                    dateRange: "2024-01-01 → 2024-08-31",
                    quality: "Grid cell",
                    min: isNDVI ? props.min_ndvi : props.min_lst,
                    max: isNDVI ? props.max_ndvi : props.max_lst,
                    std: isNDVI ? props.std_ndvi : props.std_lst,
                    vegetation_type: props.vegetation_type,
                    isNDVI: isNDVI,
                    fromGrid: true,
                  };
                  cache.set(key, info);
                  currentInfoRef.current = info;
                  updateTooltipContent(info);
                  return;
                }
              }
            }

            // Fallback to API sampling if grid not loaded or point not in grid
            const sampleEndpoint =
              analysisType === "lst"
                ? "http://localhost:8000/lst/sample"
                : "http://localhost:8000/ndvi/sample";

            console.log(
              `Fetching ${analysisType.toUpperCase()} sample from backend...`
            );
            // avoid overlapping hover fetches
            if (sampleDebounced._inFlight) return;
            sampleDebounced._inFlight = true;
            const resp = await fetch(sampleEndpoint, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                lng: lngLat.lng,
                lat: lngLat.lat,
                startDate: "2024-01-01",
                endDate: "2024-08-31",
                scale: analysisType === "lst" ? 1000 : 30,
                ...(analysisType === "ndvi" ? { cloudThreshold: 20 } : {}),
              }),
            });

            console.log("Response status:", resp.status);
            if (!resp.ok) {
              console.error(
                "Sample request failed:",
                resp.status,
                resp.statusText
              );
              return;
            }

            const data = await resp.json();
            console.log("Received sample data:", data);

            const isNDVIResp = data && typeof data.value_ndvi === "number";
            const info = {
              value: isNDVIResp ? data.value_ndvi : data.value_celsius,
              dataset: data.dataset,
              dateRange: data?.date_range
                ? `${data.date_range.start} → ${data.date_range.end}`
                : undefined,
              quality:
                data?.quality?.score != null
                  ? `${Math.round(data.quality.score * 100)}%`
                  : undefined,
              vegetation_type: data.vegetation_type,
              isNDVI: isNDVIResp,
            };
            cache.set(key, info);
            currentInfoRef.current = info;
            updateTooltipContent(info);
            console.log("Tooltip updated with info:", info);
          } catch (e) {
            console.error("Hover sample error:", e);
          } finally {
            sampleDebounced._inFlight = false;
          }
        }, 300); // Increased to 300ms for large ROIs

        // Geographic inside-ROI test using Turf with MultiPolygon support and fallback
        const isInsideROIAtPoint = (_point, lngLat) => {
          if (!mapData.roi?.geometry) {
            console.warn("No ROI geometry available");
            return false;
          }

          const geomType = mapData.roi.geometry.type;
          const coords = mapData.roi.geometry.coordinates;

          console.log(
            `Checking point [${lngLat.lng.toFixed(4)}, ${lngLat.lat.toFixed(
              4
            )}] against ${geomType}`
          );

          try {
            const pt = turf.point([lngLat.lng, lngLat.lat]);

            if (geomType === "Polygon") {
              const poly = turf.polygon(coords);
              const result = turf.booleanPointInPolygon(pt, poly);
              console.log(`Polygon check result: ${result}`);
              return result;
            } else if (geomType === "MultiPolygon") {
              // Check across polygons
              for (let i = 0; i < (coords?.length || 0); i++) {
                const poly = turf.polygon(coords[i]);
                const result = turf.booleanPointInPolygon(pt, poly);
                if (result) {
                  console.log(`Point found in polygon ${i} of MultiPolygon`);
                  return true;
                }
              }
              console.log("Point not in any polygon of MultiPolygon");
              return false;
            } else {
              console.warn(`Unsupported geometry type: ${geomType}`);
              return false;
            }
          } catch (e) {
            console.error("ROI turf check failed:", e, {
              geomType,
              coordsLength: coords?.length,
              point: [lngLat.lng, lngLat.lat],
            });

            // Fallback to ray-casting for simple polygon ring
            if (geomType === "Polygon" && coords?.[0]) {
              console.log("Falling back to ray-casting algorithm");
              return isPointInPolygon(lngLat.lng, lngLat.lat, coords[0]);
            }

            return false;
          }
        };

        map.current.on("mousemove", (e) => {
          // Get mouse position relative to viewport (for fixed positioning)
          const x = e.originalEvent.clientX;
          const y = e.originalEvent.clientY;

          // Update tooltip position EVERY mousemove (not debounced)
          tooltip.style.left = `${x + 15}px`;
          tooltip.style.top = `${y + 15}px`;
          tooltip.style.display = "block";
          tooltip.style.visibility = "visible";
          tooltip.style.opacity = "1";

          // Check if inside ROI before sampling (using hit testing)
          if (!isInsideROIAtPoint(e.point, e.lngLat)) {
            updateTooltipContent(null); // Show "Outside ROI"
            return;
          }

          // Sample LST (debounced)
          // Immediately show sampling state to avoid stale "Outside ROI" while request is in-flight
          updateTooltipContent({});
          sampleDebounced(e.lngLat);
        });

        map.current.on("mouseleave", () => {
          tooltip.style.display = "none";
        });

        // Click to get precise point value (bypasses grid, calls API)
        map.current.on("click", async (e) => {
          if (!isInsideROI(e.lngLat.lng, e.lngLat.lat)) {
            return;
          }

          console.log("🎯 Click for precise sampling at:", e.lngLat);

          // Show loading state
          updateTooltipContent({ loading: true });
          tooltip.style.display = "block";
          tooltip.style.left = `${e.originalEvent.clientX + 15}px`;
          tooltip.style.top = `${e.originalEvent.clientY + 15}px`;
          tooltip.innerHTML = "<div>🔍 Sampling precise value...</div>";

          try {
            const clickEndpoint =
              analysisType === "lst"
                ? "http://localhost:8000/lst/sample"
                : "http://localhost:8000/ndvi/sample";

            const resp = await fetch(clickEndpoint, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                lng: e.lngLat.lng,
                lat: e.lngLat.lat,
                startDate: "2024-01-01",
                endDate: "2024-08-31",
                scale: analysisType === "lst" ? 1000 : 30,
              }),
            });

            if (!resp.ok) {
              tooltip.innerHTML =
                "<div style='color: red;'>Sampling failed</div>";
              return;
            }

            const data = await resp.json();
            const isNDVI = analysisType === "ndvi";
            const info = {
              value: isNDVI ? data.value_ndvi : data.value_celsius,
              dataset: data.dataset,
              dateRange: data?.date_range
                ? `${data.date_range.start} → ${data.date_range.end}`
                : undefined,
              quality:
                data?.quality?.score != null
                  ? `${Math.round(data.quality.score * 100)}%`
                  : undefined,
              vegetation_type: data.vegetation_type,
              isNDVI: isNDVI,
              fromGrid: false,
            };

            // Cache the precise value
            const key = keyFromLngLat(e.lngLat.lng, e.lngLat.lat);
            cache.set(key, info);
            updateTooltipContent(info);

            // Keep tooltip visible for 3 seconds after click
            setTimeout(() => {
              tooltip.style.display = "none";
            }, 3000);
          } catch (err) {
            console.error("Click sampling error:", err);
            tooltip.innerHTML = "<div style='color: red;'>Error sampling</div>";
          }
        });
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
      // Clean up all tooltips
      cleanupAllTooltips();
      console.log("Cleaned up all tooltips from DOM");

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
      <div className="whitespace-pre-wrap">
        {errorMessage ? (
          <div className="text-red-700">{errorMessage}</div>
        ) : (
          textContent
        )}
      </div>

      {/* Optional debug info */}
      {!hasMapData && debugEnabled && (
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
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setShowMap(!showMap)}
                className="flex items-center space-x-2 px-3 py-1.5 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors text-sm"
              >
                {showMap ? <FaEyeSlash /> : <FaEye />}
                <span>{showMap ? "Hide Map" : "Show Map"}</span>
              </button>

              <button
                onClick={() => setShowFullScreenMap(true)}
                className="flex items-center space-x-2 px-3 py-1.5 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors text-sm"
              >
                <FaExpand />
                <span>Open Full</span>
              </button>
            </div>
          </div>

          {errorMessage && (
            <div className="px-4 py-3 bg-red-50 text-red-700 border-b border-red-200 text-sm">
              {errorMessage}
            </div>
          )}

          {showMap && (
            <div className="relative overflow-visible" key={mapId.current}>
              <div
                ref={mapContainer}
                className="w-full h-96 relative"
                id={mapId.current}
                style={{ position: "relative", overflow: "visible" }}
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

      {/* Full Screen Map Modal */}
      {showFullScreenMap && hasMapData && (
        <FullScreenMap
          roiData={
            mapData.roi
              ? [
                  {
                    id: "analysis-roi",
                    name: mapData.roi.display_name || "Analysis Area",
                    geojson: mapData.roi.geometry
                      ? {
                          type: "Feature",
                          properties: {},
                          geometry: mapData.roi.geometry,
                        }
                      : null,
                    color: "#ff6b35",
                  },
                ]
              : []
          }
          analysisData={mapData} // Pass the analysis data for tile overlay
          onClose={() => setShowFullScreenMap(false)}
          onExport={(rois) => {
            console.log("Exported ROIs:", rois);
            // You can add export functionality here if needed
          }}
        />
      )}
    </div>
  );
}

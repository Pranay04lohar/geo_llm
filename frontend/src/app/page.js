"use client";

import { useState, useMemo, useEffect, useRef } from "react";
import {
  uploadFiles as ragUploadFiles,
  getSessionStats as ragGetSessionStats,
  retrieveSimple as ragRetrieveSimple,
  retrieveDetailed as ragRetrieveDetailed,
  getLastSimple as ragGetLastSimple,
  getLastDetailed as ragGetLastDetailed,
} from "@/utils/api";
// Simple API functions - no need for separate files
const RAG_API_BASE = "http://localhost:8002";
const DYNAMIC_RAG_BASE = "http://localhost:8000";
const CORE_AGENT_API_BASE = "http://localhost:8003";

async function uploadDocsAndGetSession(files) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  formData.append("user_id", "default_user");

  const response = await fetch(`${DYNAMIC_RAG_BASE}/api/v1/upload-temp`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status}`);
  }

  return await response.json();
}

async function askRag(query, sessionId) {
  const response = await fetch(`${RAG_API_BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      session_id: sessionId,
      k: 5,
      temperature: 0.7,
      max_tokens: 2000,
    }),
  });

  if (!response.ok) {
    throw new Error(`RAG query failed: ${response.status}`);
  }

  return await response.json();
}

async function askCoreAgent(query, ragSessionId = null) {
  const response = await fetch(`${CORE_AGENT_API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      rag_session_id: ragSessionId,
    }),
  });

  if (!response.ok) {
    throw new Error(`Core Agent query failed: ${response.status}`);
  }

  return await response.json();
}
import AnimatedEarth from "@/components/AnimatedEarth";
import CollapsibleSidebar from "@/components/CollapsibleSidebar";
import MapView from "@/components/MapView";
import MiniMap from "@/components/MiniMap";
import FullScreenMap from "@/components/FullScreenMap";
import AnalysisResult from "@/components/AnalysisResult";

export default function Home() {
  const [leftCollapsed, setLeftCollapsed] = useState(true); // Default to collapsed
  const [rightCollapsed, setRightCollapsed] = useState(true); // Deprecated: right panel removed
  const [isHydrated, setIsHydrated] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState("");
  const [ragSessionId, setRagSessionId] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [finalText, setFinalText] = useState(
    "GeoLLM is ready. Upload documents and ask a question or use geospatial analysis."
  );
  const [earthSpeed, setEarthSpeed] = useState(0.002);
  const [cotLines, setCotLines] = useState([]);
  const [messages, setMessages] = useState([]);
  const cotTimersRef = useRef([]);
  const messagesEndRef = useRef(null);
  const [showFullScreen, setShowFullScreen] = useState(false);
  const [roiData, setRoiData] = useState([]);
  const [ragMessage, setRagMessage] = useState("");

  // Load from localStorage after hydration
  useEffect(() => {
    const savedLeft = localStorage.getItem("geollm-left-sidebar-collapsed");
    const savedRight = localStorage.getItem("geollm-right-sidebar-collapsed");
    const savedMessages = localStorage.getItem("geollm-chat-messages");

    if (savedLeft !== null) {
      setLeftCollapsed(JSON.parse(savedLeft));
    }
    if (savedRight !== null) {
      setRightCollapsed(JSON.parse(savedRight));
    }
    if (savedMessages !== null) {
      setMessages(JSON.parse(savedMessages));
    }

    setIsHydrated(true);
  }, []);

  // Save state to localStorage whenever it changes
  const updateLeftCollapsed = (collapsed) => {
    setLeftCollapsed(collapsed);
    if (typeof window !== "undefined") {
      localStorage.setItem(
        "geollm-left-sidebar-collapsed",
        JSON.stringify(collapsed)
      );
    }
  };

  const updateRightCollapsed = (collapsed) => {
    setRightCollapsed(collapsed);
    if (typeof window !== "undefined") {
      localStorage.setItem(
        "geollm-right-sidebar-collapsed",
        JSON.stringify(collapsed)
      );
    }
  };

  // Memoize the Earth component to prevent re-renders
  const earthComponent = useMemo(
    () => <AnimatedEarth rotationSpeed={earthSpeed} />,
    [earthSpeed]
  );

  // Real-time COT state
  const [cotSteps, setCotSteps] = useState([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [isCOTProcessing, setIsCOTProcessing] = useState(false);

  // Helper function to extract location from query
  const extractLocationFromQuery = (query) => {
    const lowerQuery = query.toLowerCase();

    // Skip common non-location words
    const skipWords = [
      "analysis",
      "water",
      "lst",
      "ndvi",
      "lulc",
      "temperature",
      "vegetation",
      "land",
      "use",
      "cover",
      "coverage",
      "analyze",
      "show",
      "get",
      "find",
      "calculate",
      "compute",
    ];

    // Enhanced location patterns
    const locationPatterns = [
      // "Water analysis of Mumbai" or "LST in New York"
      /(?:analyze|analysis|water|lst|ndvi|lulc|temperature|vegetation|land|use|cover|coverage)\s+(?:of|in|for|at|around|near)\s+([^,]+(?:,\s*[^,]+)*)/i,

      // "in Mumbai" or "at London"
      /(?:in|at|for|around|near)\s+([^,]+(?:,\s*[^,]+)*)/i,

      // "Mumbai water analysis" or "New York LST"
      /^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:water|lst|ndvi|lulc|analysis|temperature|vegetation)/i,

      // "Show me water in Mumbai" or "Get LST for London"
      /(?:show|get|find|calculate|compute)\s+(?:me\s+)?(?:water|lst|ndvi|lulc|analysis|temperature|vegetation)\s+(?:in|for|at|around|near)\s+([^,]+(?:,\s*[^,]+)*)/i,

      // Direct location names (last resort)
      /([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/g,
    ];

    for (const pattern of locationPatterns) {
      const match = lowerQuery.match(pattern);
      if (match && match[1]) {
        const location = match[1].trim();

        // Clean up the location
        let cleanLocation = location
          .replace(/\s+/g, " ") // Multiple spaces to single
          .replace(/[^\w\s,.-]/g, "") // Remove special chars except basic punctuation
          .trim();

        // Skip if it's just common words
        const words = cleanLocation.toLowerCase().split(/\s+/);
        if (
          words.every((word) => skipWords.includes(word) || word.length < 2)
        ) {
          continue;
        }

        // Skip if it's too short or too long
        if (cleanLocation.length < 2 || cleanLocation.length > 100) {
          continue;
        }

        console.log(
          `🎯 Extracted location: "${cleanLocation}" from query: "${query}"`
        );
        return cleanLocation;
      }
    }

    console.log(`❌ No location found in query: "${query}"`);
    return null;
  };

  // Helper function to get ROI for any location using the backend search service
  // This uses our sophisticated NominatimClient with proper polygon fetching
  const getROIForLocation = async (location) => {
    try {
      console.log(
        `🔍 Looking up coordinates for: ${location} using search service`
      );

      // Call backend search service (uses sophisticated NominatimClient)
      const SEARCH_SERVICE_URL = "http://localhost:8001"; // Search service port

      const response = await fetch(
        `${SEARCH_SERVICE_URL}/search/location-data`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            location_name: location,
            location_type: "city",
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`Search service failed: ${response.status}`);
      }

      const data = await response.json();
      console.log(`📊 Search service response:`, {
        success: data.success,
        hasPolygon: !!data.polygon_geometry,
        polygonType: data.polygon_geometry?.type,
        isFallback: data.is_fallback,
        area: data.area_km2,
      });

      if (!data.success || !data.coordinates) {
        throw new Error(data.error || `Location not found: ${location}`);
      }

      const lat = data.coordinates.lat;
      const lng = data.coordinates.lng;
      const displayName = data.administrative_info?.name || location;

      console.log(`📍 Found coordinates: ${lat}, ${lng} for ${displayName}`);

      // Use polygon geometry from search service
      if (
        data.polygon_geometry &&
        data.polygon_geometry.type &&
        data.polygon_geometry.coordinates
      ) {
        const geojson = data.polygon_geometry;
        const geomType = geojson.type;
        let coordinates = geojson.coordinates;

        console.log(`🗺️ Received geometry type: ${geomType}`);

        // Handle different geometry types
        if (geomType === "Polygon") {
          const outerRing = coordinates[0];
          console.log(`   Polygon with ${outerRing.length} vertices`);
          console.log(
            `✅ Using actual city boundary polygon from search service`
          );

          return {
            type: "Polygon",
            coordinates: coordinates,
            display_name: displayName,
            center: [lng, lat],
          };
        } else if (geomType === "MultiPolygon") {
          // Use the largest polygon from MultiPolygon
          let largestPolygon = coordinates[0];
          let maxArea = 0;

          for (let i = 0; i < coordinates.length; i++) {
            const area = coordinates[i][0].length; // Rough area by vertex count
            if (area > maxArea) {
              maxArea = area;
              largestPolygon = coordinates[i];
            }
          }

          console.log(`   MultiPolygon with ${coordinates.length} parts`);
          console.log(
            `   Using largest polygon with ${largestPolygon[0].length} vertices`
          );
          console.log(
            `✅ Using actual city boundary polygon from search service`
          );

          return {
            type: "Polygon",
            coordinates: largestPolygon,
            display_name: displayName,
            center: [lng, lat],
          };
        }
      }

      // If no polygon geometry, use bounding box
      if (data.bounding_box) {
        const bbox = data.bounding_box;
        console.warn(
          `⚠️ No polygon geometry, using bounding box from search service`
        );

        return {
          type: "Polygon",
          coordinates: [
            [
              [bbox.west, bbox.south],
              [bbox.east, bbox.south],
              [bbox.east, bbox.north],
              [bbox.west, bbox.north],
              [bbox.west, bbox.south],
            ],
          ],
          display_name: displayName,
          center: [lng, lat],
        };
      }

      // Last resort: calculate bounding box from center
      console.warn(
        `⚠️ No polygon or bounding box data, creating estimated box`
      );
      const offset = 0.1; // ~11km
      return {
        type: "Polygon",
        coordinates: [
          [
            [lng - offset, lat - offset],
            [lng + offset, lat - offset],
            [lng + offset, lat + offset],
            [lng - offset, lat + offset],
            [lng - offset, lat - offset],
          ],
        ],
        display_name: displayName,
        center: [lng, lat],
      };
    } catch (error) {
      console.error(`❌ Error getting ROI for ${location}:`, error);

      // Fallback: Try to extract coordinates if location contains lat,lng
      const coordMatch = location.match(/(\d+\.?\d*),\s*(\d+\.?\d*)/);
      if (coordMatch) {
        const lat = parseFloat(coordMatch[1]);
        const lng = parseFloat(coordMatch[2]);

        console.log(`📍 Using provided coordinates: ${lat}, ${lng}`);

        return {
          type: "Polygon",
          coordinates: [
            [
              [lng - 0.1, lat - 0.1],
              [lng + 0.1, lat - 0.1],
              [lng + 0.1, lat + 0.1],
              [lng - 0.1, lat + 0.1],
              [lng - 0.1, lat - 0.1],
            ],
          ],
          display_name: `Location (${lat}, ${lng})`,
          center: [lng, lat],
          bounds: 0.1,
        };
      }

      throw error;
    }
  };

  // Handle file upload for RAG
  const handleFileUpload = async (files) => {
    if (!files || files.length === 0) return;

    setIsProcessing(true);
    try {
      const result = await uploadDocsAndGetSession(files);
      setRagSessionId(result.session_id);
      setUploadedFiles(files);
      setFinalText(
        `Documents uploaded successfully! Session ID: ${result.session_id.slice(
          0,
          8
        )}... You can now ask questions about the uploaded content.`
      );
    } catch (error) {
      setFinalText(`Upload failed: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle RAG query
  const handleRagQuery = async (query) => {
    if (!ragSessionId) {
      setFinalText("Please upload documents first before asking questions.");
      return;
    }

    setIsProcessing(true);
    try {
      const response = await askRag(query, ragSessionId);
      // Just get the answer - that's all we need!
      const answer = response?.answer || "No answer received";
      setFinalText(answer);
      console.log("RAG response:", response);
    } catch (error) {
      setFinalText(`RAG query failed: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Real-time COT streaming handler
  const handleCOTStream = async (userPrompt, roi) => {
    setIsCOTProcessing(true);
    setCotSteps([]);
    setCurrentStep(0);

    // Debug: Log ROI being sent to backend
    console.log("🚀 [SEND] ROI to backend:", {
      type: roi?.type,
      coordinates_rings: roi?.coordinates?.length,
      first_ring_points: roi?.coordinates?.[0]?.length,
      display_name: roi?.display_name,
    });

    // Store original ROI for comparison
    const originalROI = JSON.parse(JSON.stringify(roi));

    // Debug: Log the ROI being sent
    console.log("🚀 [SEND] ROI to backend:", {
      type: roi?.type,
      coordinates_rings: roi?.coordinates?.length,
      first_ring_points: roi?.coordinates?.[0]?.length,
      display_name: roi?.display_name,
      is_polygon: roi?.type === "Polygon",
      is_multipolygon: roi?.type === "MultiPolygon",
    });

    // Add initial COT message
    const cotMessageId = Date.now();
    setMessages((prev) => [
      ...prev,
      { type: "cot", content: "", id: cotMessageId, steps: [] },
    ]);

    // Set a timeout to prevent infinite processing
    const timeoutId = setTimeout(() => {
      console.warn("COT streaming timeout - stopping process");
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === cotMessageId
            ? {
                type: "assistant",
                content: `⏰ Analysis timed out after 3 minutes.\n\nGeospatial analysis can take time due to satellite data processing. Please try again or use a smaller area.`,
              }
            : msg
        )
      );
      setIsCOTProcessing(false);
    }, 180000); // 3 minute timeout for geospatial analysis

    try {
      const response = await fetch("http://localhost:8003/cot-stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_prompt: userPrompt,
          roi: roi || null,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const stepData = JSON.parse(line.slice(6));
              console.log("📊 Received step data:", stepData);

              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === cotMessageId
                    ? {
                        ...msg,
                        content: generateCOTContent(stepData),
                        steps: [...(msg.steps || []), stepData],
                      }
                    : msg
                )
              );

              setCurrentStep(stepData.step);
              setCotSteps((prev) => [...prev, stepData]);

              // Check if this step has an error status
              if (stepData.status === "error") {
                console.error("COT step failed:", stepData.message);
                clearTimeout(timeoutId); // Clear the timeout
                // Stop processing and show error
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === cotMessageId
                      ? {
                          type: "assistant",
                          content: `❌ Analysis failed: ${stepData.message}\n\nPlease try again with a different query.`,
                        }
                      : msg
                  )
                );
                // Force reset all processing states
                setIsCOTProcessing(false);
                setCurrentStep(0);
                setCotSteps([]);
                return; // Exit the streaming loop
              }

              // If this is the final step, replace COT with result
              if (stepData.final_result) {
                // Debug: Log ROI received from backend
                console.log("📥 [RECEIVE] ROI from backend:", {
                  type: stepData.final_result.roi?.type,
                  coordinates_rings:
                    stepData.final_result.roi?.coordinates?.length,
                  first_ring_points:
                    stepData.final_result.roi?.coordinates?.[0]?.length,
                  display_name: stepData.final_result.roi?.display_name,
                  full_roi: stepData.final_result.roi,
                });

                // Compare with original
                console.log("🔍 [COMPARE] Original vs Received:");
                console.log(
                  "  Original points:",
                  originalROI?.coordinates?.[0]?.length
                );
                console.log(
                  "  Received points:",
                  stepData.final_result.roi?.coordinates?.[0]?.length
                );

                // If ROI was simplified, use original
                if (
                  originalROI?.coordinates?.[0]?.length > 10 &&
                  stepData.final_result.roi?.coordinates?.[0]?.length <= 5
                ) {
                  console.warn(
                    "⚠️ ROI was simplified to bounding box! Using original polygon instead."
                  );
                  stepData.final_result.roi = originalROI;
                }

                setTimeout(() => {
                  const formattedResult = formatFinalResult(
                    stepData.final_result
                  );
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === cotMessageId
                        ? {
                            type: "assistant",
                            content: formattedResult,
                          }
                        : msg
                    )
                  );
                }, 2000); // Wait 2 seconds before showing final result
              }
            } catch (parseError) {
              console.error("Error parsing COT step:", parseError);
            }
          }
        }
      }
    } catch (error) {
      console.error("COT streaming failed:", error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === cotMessageId
            ? {
                type: "assistant",
                content: `❌ Real-time analysis failed: ${error.message}`,
              }
            : msg
        )
      );
    } finally {
      clearTimeout(timeoutId); // Clear the timeout
      setIsCOTProcessing(false);
      // Force reset any other processing states
      setCurrentStep(0);
      setCotSteps([]);
    }
  };

  // Generate COT content from step data
  const generateCOTContent = (stepData) => {
    const { step, status, message, progress, details } = stepData;

    let content = "🔍 Real-time Chain-of-Thought Analysis:\n";
    content += "Executing geospatial analysis step by step...\n\n";

    // Add completed steps
    for (let i = 1; i < step; i++) {
      content += `✅ Step ${i}: [Completed]\n`;
    }

    // Add current step
    const statusIcon =
      status === "completed"
        ? "✅"
        : status === "processing"
        ? "🔄"
        : status === "error"
        ? "❌"
        : "⏳";
    content += `${statusIcon} Step ${step}: ${message}\n`;

    if (details) {
      content += `   └─ ${details}\n`;
    }

    // Add progress bar
    if (progress !== undefined) {
      const progressBar =
        "█".repeat(Math.floor(progress / 5)) +
        "░".repeat(20 - Math.floor(progress / 5));
      content += `\n📊 Progress: [${progressBar}] ${progress}%\n`;
    }

    return content;
  };

  // Format final result with AI analysis
  const formatFinalResult = (finalResult) => {
    const { analysis_type, tile_url, stats, roi, service_used } = finalResult;

    // Debug: Log ROI structure from backend
    console.log(
      "🔍 DEBUG - formatFinalResult - Full finalResult:",
      finalResult
    );
    console.log("🔍 DEBUG - formatFinalResult - ROI structure:", roi);
    console.log("🔍 DEBUG - formatFinalResult - ROI.geometry:", roi?.geometry);
    console.log(
      "🔍 DEBUG - formatFinalResult - ROI type:",
      roi?.type || roi?.geometry?.type
    );

    // Generate AI analysis text based on the results
    let aiAnalysis = generateAIAnalysis(analysis_type, stats, roi);

    // Add the map data block
    aiAnalysis += `\n\n[MAP_DATA:${JSON.stringify({
      tile_url: tile_url,
      analysis_type: analysis_type,
      roi: roi, // roi already has the correct structure from backend
      service_used: service_used,
      stats: stats,
    })}]`;

    return aiAnalysis;
  };

  // Generate AI analysis text
  const generateAIAnalysis = (analysisType, stats, roi) => {
    const location = roi.display_name || "the specified region";
    const area = stats.total_area_km2 || 0;

    if (analysisType === "water") {
      const waterPct = stats.water_percentage || 0;
      const landPct = stats.non_water_percentage || 0;

      let analysis = `✅ Water Coverage Analysis Complete!\n\n`;

      if (waterPct > 20) {
        analysis += `🌊 **Significant Water Presence Detected**\n\n`;
        analysis += `The analysis reveals substantial water coverage in ${location}, with ${waterPct.toFixed(
          1
        )}% of the area classified as water bodies. This indicates a region rich in aquatic resources, including rivers, lakes, reservoirs, or coastal areas. Such significant water presence plays a vital role in local hydrology, supporting aquatic biodiversity, regulating microclimate, and providing essential ecosystem services. These water bodies may serve multiple functions including water supply, irrigation, fisheries, recreation, and flood regulation. Sustainable water resource management is crucial to maintain water quality, preserve aquatic habitats, and balance human needs with environmental conservation. Monitoring water levels and quality over time can help track seasonal variations and long-term trends related to climate change impacts.\n\n`;
      } else if (waterPct > 5) {
        analysis += `💧 **Moderate Water Coverage**\n\n`;
        analysis += `${location} shows moderate water presence at ${waterPct.toFixed(
          1
        )}%, suggesting a balanced mix of water bodies and terrestrial features. This could include smaller rivers, ponds, or seasonal water features that contribute to local water security and ecological diversity. These water resources are important for agricultural irrigation, domestic water supply, and supporting riparian ecosystems that provide habitat for various species. The moderate water coverage indicates potential vulnerability to seasonal variations and climate variability, making water conservation and watershed management priorities. Implementing rainwater harvesting, protecting existing water bodies from pollution and encroachment, and maintaining natural drainage systems can help ensure sustainable water availability. Understanding the seasonal dynamics of these water features is important for effective water resource planning.\n\n`;
      } else {
        analysis += `🏞️ **Primarily Terrestrial Region**\n\n`;
        analysis += `The analysis indicates that ${location} is predominantly a land-based region with only ${waterPct.toFixed(
          1
        )}% water coverage. This suggests an urban, agricultural, or forested landscape with minimal surface water bodies. While limited water coverage is typical for urban and developed areas, it highlights the importance of efficient water management, groundwater conservation, and development of water infrastructure for sustainable growth. In urban contexts, this emphasizes the need for innovative water solutions such as rainwater harvesting systems, wastewater recycling, and artificial recharge of groundwater to augment limited surface water resources. Creating and maintaining small water features like ponds, lakes, or wetlands can also provide multiple benefits including microclimate regulation, biodiversity support, and recreational amenities. For agricultural areas, water-efficient irrigation techniques and crop selection suited to local water availability are essential.\n\n`;
      }

      analysis += `**Key Statistics:**\n`;
      analysis += `• Water Coverage: ${waterPct.toFixed(1)}%\n`;
      analysis += `• Land Coverage: ${landPct.toFixed(1)}%\n`;
      analysis += `• Total Area: ${area.toFixed(1)} km²\n\n`;

      analysis += `**Dataset:** JRC Global Surface Water (2000-2021)\n`;
      analysis += `**Resolution:** 30 meters\n`;
      analysis += `**Methodology:** Pixel-level classification using occurrence threshold of 20%\n\n`;

      analysis += `The interactive map below shows the water/land classification with detailed sampling available on hover.`;

      return analysis;
    } else if (analysisType === "lst") {
      const lstStats = stats.lst_statistics || {};
      const meanTemp = lstStats.LST_mean || 0;
      const minTemp = lstStats.LST_min || 0;
      const maxTemp = lstStats.LST_max || 0;

      let analysis = `✅ Land Surface Temperature Analysis Complete!\n\n`;

      if (meanTemp > 35) {
        analysis += `🔥 **High Temperature Region**\n\n`;
        analysis += `${location} exhibits high land surface temperatures with an average of ${meanTemp.toFixed(
          1
        )}°C. This elevated thermal signature is indicative of urban heat island effects, where concrete and asphalt surfaces absorb and retain heat, or arid environmental conditions with limited vegetation cover. Such high temperatures can significantly impact human comfort, increase energy consumption for cooling, and exacerbate health risks during heat waves. Urban planning interventions such as increasing tree canopy cover, implementing cool roofing materials, creating water features, and developing green infrastructure can help mitigate these heat effects. In industrial zones, heat-reflective surfaces and strategic vegetation placement can reduce surface temperatures and improve working conditions.\n\n`;
      } else if (meanTemp > 25) {
        analysis += `🌡️ **Moderate Temperature Zone**\n\n`;
        analysis += `The region shows moderate thermal conditions with a mean temperature of ${meanTemp.toFixed(
          1
        )}°C, typical of temperate climates or mixed land use areas. This balanced thermal profile suggests a mix of built-up areas, vegetation patches, and open spaces that collectively moderate surface temperatures. Such temperature ranges are generally comfortable for human habitation, though localized hot spots may still exist in densely built areas with limited green cover. Maintaining this thermal balance through sustainable urban planning—including preservation of existing green spaces, promotion of mixed land use, and thoughtful building design—is crucial for long-term livability. Climate adaptation strategies should focus on enhancing resilience to future temperature increases through nature-based solutions and smart infrastructure.\n\n`;
      } else {
        analysis += `❄️ **Cool Temperature Region**\n\n`;
        analysis += `${location} displays relatively cool surface temperatures averaging ${meanTemp.toFixed(
          1
        )}°C, possibly indicating forested areas, water bodies, or high elevation zones. These cooler thermal conditions are highly beneficial, suggesting the presence of substantial vegetation cover, proximity to water sources, or favorable topographic features that naturally regulate temperature. Such areas provide important ecosystem services including microclimate regulation, air quality improvement, and urban cooling effects that can benefit surrounding regions. Preserving these cool zones is critical for climate resilience, as they serve as natural refuges during heat events and contribute to overall environmental health. If this area is experiencing development pressure, it's important to maintain green cover and natural features to preserve these thermal benefits.\n\n`;
      }

      analysis += `**Temperature Statistics:**\n`;
      analysis += `• Mean Temperature: ${meanTemp.toFixed(1)}°C\n`;
      analysis += `• Temperature Range: ${minTemp.toFixed(
        1
      )}°C to ${maxTemp.toFixed(1)}°C\n`;
      analysis += `• Total Area: ${area.toFixed(1)} km²\n\n`;

      analysis += `**Dataset:** MODIS Land Surface Temperature\n`;
      analysis += `**Resolution:** 1 km\n`;
      analysis += `**Time Period:** 2024\n\n`;

      analysis += `The thermal visualization below shows temperature distribution with interactive sampling available.`;

      return analysis;
    } else if (analysisType === "ndvi") {
      const ndviStats = stats.ndvi_statistics || stats;
      const meanNDVI = ndviStats.mean || 0;
      const vegType = stats.dominant_vegetation_type || "Unknown";

      let analysis = `✅ Vegetation Analysis Complete!\n\n`;

      if (meanNDVI > 0.6) {
        analysis += `🌿 **Dense Vegetation**\n\n`;
        analysis += `${location} shows excellent vegetation health with an NDVI of ${meanNDVI.toFixed(
          3
        )}, indicating dense forests, healthy crops, or well-maintained green spaces. This high vegetation index reflects thriving ecosystems with substantial photosynthetic activity, typically found in tropical forests, mature agricultural fields, or areas with extensive green cover. Such regions play a crucial role in carbon sequestration, biodiversity conservation, and maintaining local climate stability. The dense canopy cover also helps in soil conservation, water retention, and providing habitat for diverse flora and fauna.\n\n`;
      } else if (meanNDVI > 0.3) {
        analysis += `🌱 **Moderate Vegetation**\n\n`;
        analysis += `The region displays moderate vegetation cover (NDVI: ${meanNDVI.toFixed(
          3
        )}), typical of grasslands, agricultural areas, or mixed land use. This pattern is characteristic of semi-urban landscapes where built-up areas coexist with parks, gardens, and agricultural patches. For an urban area like this, the moderate NDVI values suggest opportunities for urban greening initiatives such as creating green corridors, expanding park networks, or implementing rooftop gardens. Enhancing vegetation cover could improve air quality, reduce urban heat island effects, and provide recreational spaces for residents. Seasonal variations may also influence these readings, with vegetation cover fluctuating based on agricultural cycles and monsoon patterns.\n\n`;
      } else if (meanNDVI > 0.1) {
        analysis += `🌾 **Sparse Vegetation**\n\n`;
        analysis += `${location} has limited vegetation (NDVI: ${meanNDVI.toFixed(
          3
        )}), suggesting arid conditions, urban areas, or recently harvested fields. This sparse vegetation pattern is typical for semi-arid urban regions where built-up infrastructure dominates the landscape. The scattered green patches indicate opportunities for strategic urban greening initiatives, such as tree planting programs along roadways, development of green corridors connecting existing parks, and promotion of vertical gardens on buildings. Improving vegetation cover in such areas can significantly enhance air quality by reducing particulate matter, mitigate urban heat island effects through increased shade and evapotranspiration, and create healthier living environments. Water-efficient native plant species would be ideal for sustainable greening in this climate zone.\n\n`;
      } else {
        analysis += `🏜️ **Minimal Vegetation**\n\n`;
        analysis += `The area shows very low vegetation index (NDVI: ${meanNDVI.toFixed(
          3
        )}), indicating water bodies, urban areas, or barren land. This minimal vegetation reading is characteristic of densely built-up urban cores, industrial zones, exposed soil, or water-dominated landscapes. In urban contexts, such low NDVI values highlight the need for comprehensive greening strategies to improve environmental quality and livability. Potential interventions include creating pocket parks in underutilized spaces, implementing green infrastructure like bioswales and rain gardens, encouraging vertical and terrace gardens, and establishing urban forest initiatives. For barren or degraded lands, soil restoration and afforestation programs could help rebuild vegetation cover. In water-dominated areas, these readings are normal and indicate healthy aquatic ecosystems.\n\n`;
      }

      analysis += `**Vegetation Statistics:**\n`;
      analysis += `• Mean NDVI: ${meanNDVI.toFixed(3)}\n`;
      analysis += `• Dominant Type: ${vegType}\n`;
      analysis += `• NDVI Range: ${ndviStats.min?.toFixed(3) || 0} to ${
        ndviStats.max?.toFixed(3) || 0
      }\n`;
      analysis += `• Total Area: ${area.toFixed(1)} km²\n\n`;

      analysis += `**Dataset:** Sentinel-2\n`;
      analysis += `**Resolution:** 30 meters\n`;
      analysis += `**Time Period:** 2024\n\n`;

      analysis += `The vegetation map below shows health distribution with detailed classification on hover.`;

      return analysis;
    }

    // Default fallback
    return `✅ ${analysisType.toUpperCase()} Analysis Complete!\n\nAnalysis results are ready for visualization.`;
  };

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      cotTimersRef.current.forEach((id) => clearTimeout(id));
      cotTimersRef.current = [];
    };
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (typeof window !== "undefined" && messages.length > 0) {
      localStorage.setItem("geollm-chat-messages", JSON.stringify(messages));
    }
  }, [messages]);

  // Clear chat messages
  const clearChat = () => {
    setMessages([]);
    setPrompt("");
    setResult("");
    setCotLines([]);
    if (typeof window !== "undefined") {
      localStorage.removeItem("geollm-chat-messages");
    }
  };

  // Don't render until hydrated to prevent hydration mismatch
  if (!isHydrated) {
    return (
      <div className="relative min-h-screen bg-black overflow-hidden">
        <div className="absolute inset-0 z-0 pointer-events-none">
          {earthComponent}
        </div>
        <div className="relative z-10 flex h-screen items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-white/60">Loading...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-black overflow-hidden">
      {/* Earth Background - Isolated from layout changes */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        {earthComponent}
      </div>

      <div className="relative z-10 flex h-screen">
        {/* Left Sidebar - Chat History */}
        <CollapsibleSidebar
          isCollapsed={leftCollapsed}
          onToggle={() => updateLeftCollapsed(!leftCollapsed)}
          position="left"
          onNewChat={clearChat}
          data-sidebar="left"
        >
          {/* Header with Logo */}
          <div className="p-6 border-b border-white/10">
            <div className="flex items-center gap-4 mb-6">
              <button
                id="left-sidebar-toggle"
                className="left-sidebar-toggle w-12 h-12 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-2xl flex items-center justify-center shadow-lg transition-all duration-200 cursor-pointer border border-blue-500/30 hover:shadow-xl hover:scale-105"
                onClick={() => updateLeftCollapsed(!leftCollapsed)}
              >
                <svg
                  className="w-6 h-6 text-white"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
                  />
                </svg>
              </button>
              <div className="flex items-center gap-3">
                <span className="text-white font-bold text-2xl">GeoLLM</span>
              </div>
            </div>

            {/* New Chat Button with Gradient */}
            <button
              id="new-chat-button"
              onClick={clearChat}
              className="new-chat-button w-full bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-2xl px-6 py-4 flex items-center gap-3 transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-[1.02] font-semibold text-base"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
              </svg>
              New Chat
            </button>
          </div>

          {/* Search Bar */}
          <div className="p-6">
            <div className="relative">
              <input
                id="chat-search"
                type="text"
                placeholder="Search chats..."
                className="chat-search w-full bg-white/8 rounded-2xl px-5 py-3 pl-12 text-white placeholder-white/60 focus:outline-none focus:bg-white/12 focus:shadow-lg transition-all duration-200 shadow-lg border border-white/15 focus:border-white/25 text-sm"
              />
              <svg
                className="w-5 h-5 absolute left-4 top-3.5 text-white/60"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </div>
          </div>

          {/* Chat History */}
          <div className="flex-1 overflow-y-auto px-6 space-y-3">
            <div className="text-xs text-white/60 uppercase tracking-wider mb-4 font-semibold">
              Recent Chats
            </div>
            {[
              {
                title: "Population data analysis",
                icon: "M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z",
              },
              {
                title: "Boundary extraction India",
                icon: "M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-1.447-.894L15 4m0 13V4m-6 3l6-3",
              },
              {
                title: "Geospatial clustering",
                icon: "M7 4V2a1 1 0 011-1h8a1 1 0 011 1v2m-9 0h10m-10 0a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V6a2 2 0 00-2-2",
              },
              {
                title: "Satellite imagery analysis",
                icon: "M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9v-9m0-9v9",
              },
            ].map((chat, index) => (
              <div
                key={index}
                className="bg-white/8 rounded-2xl p-4 cursor-pointer transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-[1.02] border border-white/10 group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-white/10 rounded-lg flex items-center justify-center transition-all duration-200">
                    <svg
                      className="w-4 h-4 text-white/70 group-hover:text-white"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d={chat.icon}
                      />
                    </svg>
                  </div>
                  <p className="text-white/90 text-sm truncate transition-colors duration-200 flex-1">
                    {chat.title}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* User Info */}
          <div className="p-6 border-t border-white/10">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-12 h-12 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-full flex items-center justify-center shadow-lg border border-blue-500/30 transition-all duration-200 hover:shadow-xl hover:scale-105">
                <svg
                  className="w-6 h-6 text-white"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                  />
                </svg>
              </div>
              <div className="flex-1">
                <p className="text-white text-base font-semibold">Pranay</p>
              </div>
            </div>
            {/* Notification Indicator */}
          </div>
        </CollapsibleSidebar>

        {/* Center - Chat Interface */}
        <div className="flex-1 flex flex-col relative transition-all duration-300 ease-in-out">
          {/* Chat Content - Layered on top */}
          <div className="relative z-10 flex flex-col h-full transition-all duration-300 ease-in-out">
            {/* Chat Header */}
            <div className="bg-black/40 backdrop-blur-xl p-4 shadow-2xl border-b border-white/10">
              <div className="flex items-center justify-between relative">
                {/* Center: Title */}
                <div className="flex-1 flex justify-center">
                  <h1 className="text-white font-bold text-3xl md:text-4xl">
                    GeoLLM
                  </h1>
                </div>

                {/* Right: Clear Chat Button */}
                <div className="flex items-center gap-3 flex-shrink-0">
                  {messages.length > 0 && (
                    <button
                      onClick={clearChat}
                      className="text-white/70 hover:text-white transition-all duration-200 p-2 rounded-xl hover:scale-110 hover:bg-white/10"
                      title="Clear chat history"
                    >
                      <svg
                        className="w-6 h-6"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Chat Messages - Welcome or Message History */}
            <div className="flex-1 overflow-y-auto p-8 pb-4">
              {messages.length === 0 && !isProcessing ? (
                <div className="flex items-center justify-center h-full -mt-12">
                  <div className="text-center max-w-2xl relative z-20 ml-16 w-full">
                    <div className="text-white font-medium text-5xl mb-6 leading-tight">
                      What&apos;s on your mind today?
                    </div>
                    <div className="text-white/70 text-lg font-bold max-w-lg mx-auto leading-relaxed">
                      Ask me anything about geography, boundaries, or spatial
                      data analysis
                    </div>
                  </div>
                </div>
              ) : (
                <div className="max-w-6xl mx-auto space-y-4">
                  {messages.map((message, index) => (
                    <div
                      key={index}
                      className={`flex ${
                        message.type === "user"
                          ? "justify-end"
                          : "justify-start"
                      } animate-fade-in-up`}
                    >
                      <div
                        className={`max-w-[85%] rounded-2xl px-5 py-4 ${
                          message.type === "user"
                            ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white"
                            : "bg-white/10 text-white/90 border border-white/20"
                        }`}
                      >
                        {message.type === "cot" ? (
                          <div className="flex flex-col gap-2">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-400"></div>
                                <span className="text-sm font-medium">
                                  Thinking...
                                </span>
                              </div>
                              {isCOTProcessing && (
                                <button
                                  onClick={() => {
                                    setIsCOTProcessing(false);
                                    setMessages((prev) => [
                                      ...prev,
                                      {
                                        type: "assistant",
                                        content:
                                          "🛑 Analysis stopped by user.\n\nYou can now start a new analysis.",
                                      },
                                    ]);
                                  }}
                                  className="px-3 py-1 text-xs bg-red-100 hover:bg-red-200 text-red-700 rounded-md transition-colors"
                                >
                                  Stop Analysis
                                </button>
                              )}
                            </div>
                            <div className="text-sm whitespace-pre-wrap">
                              {message.content}
                            </div>
                          </div>
                        ) : message.type === "assistant" ? (
                          <AnalysisResult content={message.content} />
                        ) : (
                          <div className="whitespace-pre-wrap">
                            {message.content}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* Chat Input Area */}
            <div className="pl-12 pr-4 -mt-8 pb-2">
              <div className="flex justify-center">
                <div className="w-full max-w-6xl">
                  <div className="relative">
                    <textarea
                      id="prompt-input"
                      placeholder="Ask anything about geography, boundaries, or spatial data..."
                      aria-label="Prompt input"
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      disabled={isProcessing || isCOTProcessing}
                      className="prompt-input w-full bg-black/50 rounded-3xl px-8 py-5 pr-28 text-white placeholder-white/60 focus:outline-none focus:bg-black/60 focus:shadow-xl resize-none shadow-xl transition-all duration-200 border border-white/10 focus:border-white/20 text-base"
                      rows={3}
                    />
                    <div className="absolute right-6 bottom-6 flex items-center gap-4">
                      {/* Upload Button in Chat */}
                      <label
                        id="file-upload"
                        className="file-upload text-white/80 transition-all duration-200 p-2 rounded-xl hover:scale-110 hover:bg-white/10 cursor-pointer"
                      >
                        <input
                          type="file"
                          multiple
                          accept=".geojson,.json,.shp,.zip,.tif,.tiff,.pdf,.txt,.docx,.md"
                          className="hidden"
                          onChange={async (event) => {
                            const files = Array.from(event.target.files || []);
                            if (files.length === 0) return;
                            const lower = files.map((f) =>
                              f.name.toLowerCase()
                            );
                            const isRag = lower.some(
                              (n) =>
                                n.endsWith(".pdf") ||
                                n.endsWith(".txt") ||
                                n.endsWith(".docx") ||
                                n.endsWith(".md")
                            );
                            try {
                              if (isRag) {
                                const selected = files.slice(0, 2);
                                // Use new RAG upload function
                                const res = await uploadDocsAndGetSession(
                                  selected
                                );
                                setRagSessionId(res.session_id);
                                setUploadedFiles(selected);
                                setRagMessage(
                                  `Uploaded ${
                                    selected.length
                                  } files to session ${res.session_id.slice(
                                    0,
                                    8
                                  )}...`
                                );
                                if (typeof window !== "undefined") {
                                  localStorage.setItem(
                                    "rag_session_id",
                                    res.session_id
                                  );
                                }
                                // Update finalText to show upload success
                                setFinalText(
                                  `Documents uploaded successfully! You can now ask questions about the uploaded content.`
                                );
                              } else {
                                const file = files[0];
                                const name = file.name.toLowerCase();
                                if (
                                  name.endsWith(".geojson") ||
                                  name.endsWith(".json")
                                ) {
                                  const text = await file.text();
                                  const data = JSON.parse(text);
                                  const fc =
                                    data.type === "FeatureCollection"
                                      ? data
                                      : {
                                          type: "FeatureCollection",
                                          features: [data],
                                        };
                                  setRoiData((prev) => {
                                    const base = prev.length;
                                    const newItems = fc.features.map(
                                      (feat, idx) => ({
                                        id: `roi-${base + idx + 1}`,
                                        name:
                                          feat.properties?.name ||
                                          `ROI ${base + idx + 1}`,
                                        geojson: feat,
                                        color: "#3498db",
                                      })
                                    );
                                    return [...prev, ...newItems];
                                  });
                                  setShowFullScreen(true);
                                } else if (
                                  name.endsWith(".tif") ||
                                  name.endsWith(".tiff")
                                ) {
                                  alert(
                                    "TIFF upload is not yet supported in the frontend. Consider server-side processing."
                                  );
                                } else if (
                                  name.endsWith(".shp") ||
                                  name.endsWith(".zip")
                                ) {
                                  alert(
                                    "Shapefile upload is not yet supported in the frontend. Please convert to GeoJSON."
                                  );
                                } else {
                                  alert(
                                    "Unsupported file type. Please upload GeoJSON or RAG-supported files (.pdf, .txt, .docx, .md)."
                                  );
                                }
                              }
                            } catch (e) {
                              alert("Upload failed. " + (e?.message || ""));
                            } finally {
                              event.target.value = "";
                            }
                          }}
                        />
                        <svg
                          className="w-6 h-6"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5-5m0 0l5 5m-5-5v12"
                          />
                        </svg>
                      </label>
                      <button
                        className="send-button bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-2xl p-3 transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-110 disabled:opacity-60"
                        aria-label="Send prompt"
                        disabled={
                          isProcessing || isCOTProcessing || !prompt.trim()
                        }
                        onClick={async () => {
                          if (!prompt.trim() || isProcessing || isCOTProcessing)
                            return;

                          const userPrompt = prompt.trim();
                          setPrompt("");

                          // Add user message immediately
                          setMessages((prev) => [
                            ...prev,
                            { type: "user", content: userPrompt },
                          ]);

                          setIsProcessing(true);
                          setEarthSpeed(0.0005);

                          // Use real-time COT for geospatial analysis
                          if (!ragSessionId) {
                            // For geospatial queries, use real-time COT
                            try {
                              // First try to get location from the query or use a default
                              const location =
                                extractLocationFromQuery(userPrompt) ||
                                "Mumbai, India";
                              const roi = await getROIForLocation(location);
                              await handleCOTStream(userPrompt, roi);
                            } finally {
                              // Always reset processing state
                              setIsProcessing(false);
                              setEarthSpeed(0.002);
                            }
                            return;
                          }

                          // For RAG queries, use static COT
                          const cotMessageId = Date.now();
                          setMessages((prev) => [
                            ...prev,
                            { type: "cot", content: "", id: cotMessageId },
                          ]);

                          // progressively reveal CoT lines for RAG
                          let cotContent = "";
                          const RAG_COT_SCRIPT = [
                            "Chain-of-Thought (CoT) Analysis:",
                            "Processing document-based query...",
                            "",
                            "Step 1: Analyzing uploaded documents and extracting relevant information.",
                            "Step 2: Searching through document content for relevant passages.",
                            "Step 3: Generating contextual response based on document content.",
                            "",
                            "Generating response...",
                          ];

                          RAG_COT_SCRIPT.forEach((line, idx) => {
                            const id = setTimeout(() => {
                              cotContent += line + "\n";
                              setMessages((prev) =>
                                prev.map((msg) =>
                                  msg.id === cotMessageId
                                    ? { ...msg, content: cotContent }
                                    : msg
                                )
                              );
                            }, 300 * idx);
                            cotTimersRef.current.push(id);
                          });

                          // Enhanced RAG processing with proper error handling
                          try {
                            let responseText = "";

                            if (ragSessionId) {
                              // Use RAG API for polished LLM responses
                              const ragResponse = await askRag(
                                userPrompt,
                                ragSessionId
                              );

                              // Just get the answer - that's all we need!
                              responseText =
                                ragResponse?.answer || "No answer received";
                              console.log("RAG response:", ragResponse);
                            } else {
                              // This should not happen due to early return above
                              responseText = "No analysis received";
                            }

                            // Replace CoT placeholder with response
                            setMessages((prev) =>
                              prev.map((msg) =>
                                msg.id === cotMessageId
                                  ? { type: "assistant", content: responseText }
                                  : msg
                              )
                            );
                          } catch (e) {
                            console.error("Query processing failed:", e);

                            // Enhanced error handling with helpful messages
                            let errorMessage =
                              "I encountered an error processing your request.";

                            if (e.message.includes("Session")) {
                              errorMessage =
                                "📚 Session expired or invalid. Please upload your documents again.";
                            } else if (
                              e.message.includes("network") ||
                              e.message.includes("fetch")
                            ) {
                              errorMessage =
                                "🌐 Network error. Please check your connection and try again.";
                            } else if (e.message.includes("timeout")) {
                              errorMessage =
                                "⏰ Request timed out. The server might be busy. Please try again.";
                            }

                            // Replace CoT placeholder with error
                            setMessages((prev) =>
                              prev.map((msg) =>
                                msg.id === cotMessageId
                                  ? { type: "assistant", content: errorMessage }
                                  : msg
                              )
                            );
                          } finally {
                            setIsProcessing(false);
                          }
                        }}
                      >
                        <svg
                          className="w-6 h-6"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 mt-6 justify-center">
                    {ragSessionId && (
                      <div className="text-white/80 text-sm px-4 py-2 rounded-xl bg-white/10 border border-white/15">
                        RAG session:{" "}
                        <span className="font-mono">{ragSessionId}</span>
                        {ragMessage ? ` · ${ragMessage}` : ""}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel - Interactive Map Tools with MiniMap */}
        <CollapsibleSidebar
          isCollapsed={rightCollapsed}
          onToggle={() => updateRightCollapsed(!rightCollapsed)}
          position="right"
          data-sidebar="right"
        >
          <div className="p-6 border-b border-white/10">
            <div className="flex items-center justify-between">
              <h2 className="text-white font-bold text-xl">Map</h2>
              <button
                id="right-sidebar-toggle"
                className="right-sidebar-toggle w-12 h-12 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-2xl flex items-center justify-center shadow-lg transition-all duration-200 cursor-pointer border border-blue-500/30 hover:shadow-xl hover:scale-105"
                onClick={() => updateRightCollapsed(!rightCollapsed)}
              >
                <svg
                  className="w-6 h-6 text-white"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-1.447-.894L15 4m0 13V4m-6 3l6-3"
                  />
                </svg>
              </button>
            </div>
          </div>
          <div className="p-6">
            <div
              id="mini-map"
              className="mini-map bg-white/8 rounded-3xl overflow-hidden border border-white/15"
              style={{ minHeight: "180px" }}
            >
              <MiniMap
                embedded
                onOpenFullScreen={() => setShowFullScreen(true)}
              />
            </div>
          </div>
        </CollapsibleSidebar>

        {showFullScreen && (
          <div id="fullscreen-map" className="fullscreen-map">
            <FullScreenMap
              roiData={roiData}
              onClose={() => setShowFullScreen(false)}
              onExport={(data) => {
                setRoiData(data);
                setShowFullScreen(false);
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

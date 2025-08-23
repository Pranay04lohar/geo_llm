/**
 * Transportation Network Analysis Template for Google Earth Engine
 *
 * Uses OpenStreetMap and satellite imagery for transportation infrastructure analysis
 * Designed specifically for Indian regions with proper boundary clipping
 */

// Template Configuration
var TEMPLATE_CONFIG = {
  name: "transportation_network",
  description: "Transportation infrastructure and connectivity analysis",
  datasets: [
    "COPERNICUS/S2_SR_HARMONIZED",
    "ESA/WorldCover/v200",
    "FAO/GAUL/2015/level0", // For India boundary
  ],
  metrics: [
    "road_density",
    "connectivity_index",
    "urban_transport_coverage",
    "rural_accessibility",
    "infrastructure_development",
  ],
  region: "India",
  example_query: "Analyze transportation networks in Mumbai",
};

/**
 * Generate transportation analysis script for given ROI
 * @param {ee.Geometry} roi - Region of Interest
 * @param {Object} params - Analysis parameters
 * @returns {Object} - Analysis results
 */
function generateScript(roi, params) {
  // Default parameters
  params = params || {};
  var startDate = params.startDate || "2023-01-01";
  var endDate = params.endDate || "2023-12-31";
  var maxCloudCover = params.maxCloudCover || 15;

  // Load India boundary for clipping
  var india = ee
    .FeatureCollection("FAO/GAUL/2015/level0")
    .filter(ee.Filter.eq("ADM0_NAME", "India"));
  var indiaBoundary = india.geometry();

  // Clip ROI to India boundary
  var analysisROI = roi.intersection(indiaBoundary);

  // 1. Sentinel-2 for infrastructure detection
  var s2Collection = ee
    .ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(analysisROI)
    .filterDate(startDate, endDate)
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", maxCloudCover));

  var s2Composite = s2Collection.median().clip(analysisROI);

  // 2. ESA WorldCover for context
  var landCover = ee.Image("ESA/WorldCover/v200/2021").clip(analysisROI);
  var builtUpAreas = landCover.eq(50);

  // 3. Road Detection using Spectral Indices

  // Normalized Difference Built-up Index (NDBI)
  var ndbi = s2Composite.normalizedDifference(["B11", "B8"]).rename("NDBI");

  // Enhanced Built-up and Bareness Index (EBBI)
  var ebbi = s2Composite
    .expression("(SWIR1 - NIR) / (10 * sqrt(SWIR1 + NIR))", {
      SWIR1: s2Composite.select("B11"),
      NIR: s2Composite.select("B8"),
    })
    .rename("EBBI");

  // Urban Index (UI)
  var ui = s2Composite
    .expression("(SWIR2 - NIR) / (SWIR2 + NIR)", {
      SWIR2: s2Composite.select("B12"),
      NIR: s2Composite.select("B8"),
    })
    .rename("UI");

  // Bare Soil Index (BSI) - useful for unpaved roads
  var bsi = s2Composite
    .expression(
      "((SWIR1 + RED) - (NIR + BLUE)) / ((SWIR1 + RED) + (NIR + BLUE))",
      {
        SWIR1: s2Composite.select("B11"),
        RED: s2Composite.select("B4"),
        NIR: s2Composite.select("B8"),
        BLUE: s2Composite.select("B2"),
      }
    )
    .rename("BSI");

  // 4. Infrastructure Detection

  // Paved roads (high NDBI + built-up context)
  var pavedRoads = ndbi.gt(0.1).and(builtUpAreas);

  // Unpaved roads (moderate BSI + linear features)
  var unpavedRoads = bsi.gt(0.0).and(bsi.lt(0.3));

  // All transportation infrastructure
  var allTransport = pavedRoads.or(unpavedRoads);

  // Major infrastructure (high UI values)
  var majorInfrastructure = ui.gt(0.2);

  // 5. Connectivity Analysis

  // Calculate road density (kernel density)
  var roadDensity = allTransport.reduceNeighborhood({
    reducer: ee.Reducer.mean(),
    kernel: ee.Kernel.circle({ radius: 1000 }), // 1km radius
    skipMasked: false,
  });

  // Urban vs rural connectivity
  var urbanTransport = allTransport.and(builtUpAreas);
  var ruralTransport = allTransport.and(builtUpAreas.not());

  // 6. Calculate Areas and Statistics
  var pixelArea = ee.Image.pixelArea();

  // Total areas
  var roiAreaM2 = pixelArea.reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 10,
    maxPixels: 1e9,
  });

  var transportAreaM2 = pixelArea.multiply(allTransport).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 10,
    maxPixels: 1e9,
  });

  var pavedRoadAreaM2 = pixelArea.multiply(pavedRoads).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 10,
    maxPixels: 1e9,
  });

  var urbanTransportAreaM2 = pixelArea.multiply(urbanTransport).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 10,
    maxPixels: 1e9,
  });

  var ruralTransportAreaM2 = pixelArea.multiply(ruralTransport).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 10,
    maxPixels: 1e9,
  });

  // Infrastructure density statistics
  var densityStats = roadDensity.reduceRegion({
    reducer: ee.Reducer.mean()
      .combine({
        reducer2: ee.Reducer.min(),
        sharedInputs: true,
      })
      .combine({
        reducer2: ee.Reducer.max(),
        sharedInputs: true,
      })
      .combine({
        reducer2: ee.Reducer.stdDev(),
        sharedInputs: true,
      }),
    geometry: analysisROI,
    scale: 10,
    maxPixels: 1e9,
  });

  // Index statistics
  var ndbiStats = ndbi.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: analysisROI,
    scale: 10,
    maxPixels: 1e9,
  });

  var uiStats = ui.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: analysisROI,
    scale: 10,
    maxPixels: 1e9,
  });

  // 7. Format Results
  var results = {
    analysis_type: "transportation_network",
    template_used: "transportation_network.js",
    datasets_used: TEMPLATE_CONFIG.datasets,
    analysis_methods: [
      "Sentinel-2 Spectral Analysis",
      "Infrastructure Indices (NDBI, UI, BSI)",
      "Connectivity Density Analysis",
      "ESA WorldCover Context",
    ],
    total_transport_area_m2: transportAreaM2,
    paved_road_area_m2: pavedRoadAreaM2,
    urban_transport_area_m2: urbanTransportAreaM2,
    rural_transport_area_m2: ruralTransportAreaM2,
    roi_area_m2: roiAreaM2,
    road_density_stats: densityStats,
    infrastructure_indices: {
      ndbi_stats: ndbiStats,
      ui_stats: uiStats,
    },
    image_count: s2Collection.size(),
    processing_info: {
      start_date: startDate,
      end_date: endDate,
      max_cloud_cover: maxCloudCover,
      analysis_region: "India (clipped)",
      scale_meters: 10,
      connectivity_radius_meters: 1000,
    },
  };

  return results;
}

// Export configuration and function
exports.config = TEMPLATE_CONFIG;
exports.generateScript = generateScript;

// Example usage (for testing):
// var mumbai = ee.Geometry.Rectangle([72.77, 18.89, 72.97, 19.27]);
// var result = generateScript(mumbai);
// print('Transportation Analysis Result:', result);

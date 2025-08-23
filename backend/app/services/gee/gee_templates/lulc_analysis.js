/**
 * Land Use Land Cover (LULC) Analysis Template for Google Earth Engine
 *
 * Uses ESA WorldCover and Dynamic World for comprehensive land cover classification
 * Designed specifically for Indian regions with proper boundary clipping
 */

// Template Configuration
var TEMPLATE_CONFIG = {
  name: "lulc_analysis",
  description:
    "Comprehensive land use and land cover classification and change analysis",
  datasets: [
    "ESA/WorldCover/v200",
    "GOOGLE/DYNAMICWORLD/V1",
    "COPERNICUS/S2_SR_HARMONIZED",
    "FAO/GAUL/2015/level0", // For India boundary
  ],
  metrics: [
    "land_cover_distribution",
    "urban_area_km2",
    "agricultural_area_km2",
    "natural_vegetation_km2",
    "built_up_percentage",
    "change_detection",
  ],
  region: "India",
  example_query: "Analyze land use patterns in Mumbai",
};

// Land cover class mappings
var ESA_CLASSES = {
  10: "Trees",
  20: "Shrubland",
  30: "Grassland",
  40: "Cropland",
  50: "Built-up",
  60: "Bare/sparse vegetation",
  70: "Snow and ice",
  80: "Permanent water bodies",
  90: "Herbaceous wetland",
  95: "Mangroves",
  100: "Moss and lichen",
};

var DYNAMIC_WORLD_CLASSES = {
  0: "Water",
  1: "Trees",
  2: "Grass",
  3: "Flooded vegetation",
  4: "Crops",
  5: "Shrub and scrub",
  6: "Built area",
  7: "Bare ground",
  8: "Snow and ice",
};

/**
 * Generate LULC analysis script for given ROI
 * @param {ee.Geometry} roi - Region of Interest
 * @param {Object} params - Analysis parameters
 * @returns {Object} - Analysis results
 */
function generateScript(roi, params) {
  // Default parameters
  params = params || {};
  var startDate = params.startDate || "2023-01-01";
  var endDate = params.endDate || "2023-12-31";
  var maxCloudCover = params.maxCloudCover || 20;

  // Load India boundary for clipping
  var india = ee
    .FeatureCollection("FAO/GAUL/2015/level0")
    .filter(ee.Filter.eq("ADM0_NAME", "India"));
  var indiaBoundary = india.geometry();

  // Clip ROI to India boundary
  var analysisROI = roi.intersection(indiaBoundary);

  // 1. ESA WorldCover 2021 (10m resolution)
  var esaWorldCover = ee.Image("ESA/WorldCover/v200/2021").clip(analysisROI);

  // 2. Dynamic World (10m resolution, near real-time)
  var dynamicWorld = ee
    .ImageCollection("GOOGLE/DYNAMICWORLD/V1")
    .filterBounds(analysisROI)
    .filterDate(startDate, endDate)
    .select("label")
    .mode() // Most common class
    .clip(analysisROI);

  // 3. Sentinel-2 for validation and additional analysis
  var s2Collection = ee
    .ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(analysisROI)
    .filterDate(startDate, endDate)
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", maxCloudCover));

  var s2Composite = s2Collection.median().clip(analysisROI);

  // Calculate indices for validation
  var ndvi = s2Composite.normalizedDifference(["B8", "B4"]).rename("NDVI");
  var ndbi = s2Composite.normalizedDifference(["B11", "B8"]).rename("NDBI"); // Built-up index

  // 4. Calculate Areas for Each Land Cover Class
  var pixelArea = ee.Image.pixelArea();

  // ESA WorldCover areas
  var esaAreas = {};
  Object.keys(ESA_CLASSES).forEach(function (classValue) {
    var classMask = esaWorldCover.eq(parseInt(classValue));
    var classArea = pixelArea.multiply(classMask).reduceRegion({
      reducer: ee.Reducer.sum(),
      geometry: analysisROI,
      scale: 10,
      maxPixels: 1e9,
    });
    esaAreas[ESA_CLASSES[classValue]] = classArea;
  });

  // Dynamic World areas
  var dwAreas = {};
  Object.keys(DYNAMIC_WORLD_CLASSES).forEach(function (classValue) {
    var classMask = dynamicWorld.eq(parseInt(classValue));
    var classArea = pixelArea.multiply(classMask).reduceRegion({
      reducer: ee.Reducer.sum(),
      geometry: analysisROI,
      scale: 10,
      maxPixels: 1e9,
    });
    dwAreas[DYNAMIC_WORLD_CLASSES[classValue]] = classArea;
  });

  // Total ROI area
  var roiAreaM2 = pixelArea.reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 10,
    maxPixels: 1e9,
  });

  // 5. Urban/Built-up Analysis
  var esaBuiltUp = esaWorldCover.eq(50); // Built-up class
  var dwBuiltUp = dynamicWorld.eq(6); // Built area class

  // Combined built-up (consensus)
  var combinedBuiltUp = esaBuiltUp.or(dwBuiltUp);

  var builtUpAreaM2 = pixelArea.multiply(combinedBuiltUp).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 10,
    maxPixels: 1e9,
  });

  // 6. Agricultural Analysis
  var esaCropland = esaWorldCover.eq(40);
  var dwCrops = dynamicWorld.eq(4);
  var combinedCrops = esaCropland.or(dwCrops);

  var croplandAreaM2 = pixelArea.multiply(combinedCrops).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 10,
    maxPixels: 1e9,
  });

  // 7. Natural Vegetation Analysis
  var esaTrees = esaWorldCover.eq(10);
  var esaShrubland = esaWorldCover.eq(20);
  var esaGrassland = esaWorldCover.eq(30);
  var naturalVeg = esaTrees.or(esaShrubland).or(esaGrassland);

  var naturalVegAreaM2 = pixelArea.multiply(naturalVeg).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 10,
    maxPixels: 1e9,
  });

  // 8. Index Statistics
  var ndviStats = ndvi.reduceRegion({
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

  var ndbiStats = ndbi.reduceRegion({
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

  // 9. Format Results
  var results = {
    analysis_type: "lulc_analysis",
    template_used: "lulc_analysis.js",
    datasets_used: TEMPLATE_CONFIG.datasets,
    classification_methods: [
      "ESA WorldCover 2021",
      "Google Dynamic World",
      "Sentinel-2 Spectral Indices",
    ],
    esa_worldcover_areas: esaAreas,
    dynamic_world_areas: dwAreas,
    built_up_area_m2: builtUpAreaM2,
    cropland_area_m2: croplandAreaM2,
    natural_vegetation_area_m2: naturalVegAreaM2,
    roi_area_m2: roiAreaM2,
    ndvi_stats: ndviStats,
    ndbi_stats: ndbiStats,
    class_definitions: {
      esa_worldcover: ESA_CLASSES,
      dynamic_world: DYNAMIC_WORLD_CLASSES,
    },
    image_count: s2Collection.size(),
    processing_info: {
      start_date: startDate,
      end_date: endDate,
      max_cloud_cover: maxCloudCover,
      analysis_region: "India (clipped)",
      scale_meters: 10,
      esa_version: "v200/2021",
      dynamic_world_version: "V1",
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
// print('LULC Analysis Result:', result);

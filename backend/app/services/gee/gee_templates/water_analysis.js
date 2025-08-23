/**
 * Water Analysis Template for Google Earth Engine
 *
 * Uses JRC Global Surface Water dataset and Sentinel-2 for comprehensive water detection
 * Designed specifically for Indian regions with proper boundary clipping
 */

// Template Configuration
var TEMPLATE_CONFIG = {
  name: "water_analysis",
  description: "Comprehensive water body detection and analysis",
  datasets: [
    "JRC/GSW1_4/MonthlyHistory",
    "COPERNICUS/S2_SR_HARMONIZED",
    "FAO/GAUL/2015/level0", // For India boundary
  ],
  metrics: [
    "water_area_km2",
    "water_percentage",
    "seasonal_water_area_km2",
    "permanent_water_area_km2",
    "ndwi_mean",
    "mndwi_mean",
  ],
  region: "India",
  example_query: "Analyze water bodies in Delhi",
};

/**
 * Generate water analysis script for given ROI
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

  // 1. JRC Global Surface Water Analysis
  var jrcCollection = ee
    .ImageCollection("JRC/GSW1_4/MonthlyHistory")
    .filterBounds(analysisROI)
    .filterDate(startDate, endDate);

  // Get most recent month with data
  var jrcRecent = jrcCollection.sort("system:time_start", false).first();

  // Water classification (0=no data, 1=not water, 2=seasonal water, 3=permanent water)
  var permanentWater = jrcRecent.select("water").eq(3);
  var seasonalWater = jrcRecent.select("water").eq(2);
  var allWater = permanentWater.or(seasonalWater);

  // 2. Sentinel-2 Optical Water Detection
  var s2Collection = ee
    .ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(analysisROI)
    .filterDate(startDate, endDate)
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", maxCloudCover))
    .filter(ee.Filter.lt("CLOUD_SHADOW_PERCENTAGE", 10));

  var s2Composite = s2Collection.median().clip(analysisROI);

  // Calculate water indices
  var ndwi = s2Composite.normalizedDifference(["B3", "B8"]).rename("NDWI");
  var mndwi = s2Composite.normalizedDifference(["B3", "B11"]).rename("MNDWI");

  // Water masks from optical data
  var ndwiWater = ndwi.gt(0.2);
  var mndwiWater = mndwi.gt(0.1);

  // Combined water mask (JRC + optical)
  var combinedWater = allWater.or(ndwiWater).or(mndwiWater);

  // 3. Calculate Areas
  var pixelArea = ee.Image.pixelArea();

  // Total water area
  var waterAreaM2 = pixelArea.multiply(combinedWater).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 30,
    maxPixels: 1e9,
  });

  // Permanent water area
  var permanentAreaM2 = pixelArea.multiply(permanentWater).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 30,
    maxPixels: 1e9,
  });

  // Seasonal water area
  var seasonalAreaM2 = pixelArea.multiply(seasonalWater).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 30,
    maxPixels: 1e9,
  });

  // Total ROI area
  var roiAreaM2 = pixelArea.reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 30,
    maxPixels: 1e9,
  });

  // 4. Calculate Statistics
  var ndwiStats = ndwi.reduceRegion({
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
    scale: 30,
    maxPixels: 1e9,
  });

  var mndwiStats = mndwi.reduceRegion({
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
    scale: 30,
    maxPixels: 1e9,
  });

  // 5. Format Results
  var results = {
    analysis_type: "water_analysis",
    template_used: "water_analysis.js",
    datasets_used: TEMPLATE_CONFIG.datasets,
    water_detection_methods: [
      "JRC Global Surface Water",
      "NDWI (Green-NIR)",
      "Modified NDWI (Green-SWIR)",
    ],
    water_area_m2: waterAreaM2,
    permanent_water_area_m2: permanentAreaM2,
    seasonal_water_area_m2: seasonalAreaM2,
    roi_area_m2: roiAreaM2,
    ndwi_stats: ndwiStats,
    mndwi_stats: mndwiStats,
    image_count: s2Collection.size(),
    processing_info: {
      start_date: startDate,
      end_date: endDate,
      max_cloud_cover: maxCloudCover,
      analysis_region: "India (clipped)",
      scale_meters: 30,
    },
  };

  return results;
}

// Export configuration and function
exports.config = TEMPLATE_CONFIG;
exports.generateScript = generateScript;

// Example usage (for testing):
// var delhi = ee.Geometry.Rectangle([76.68, 28.57, 77.53, 28.84]);
// var result = generateScript(delhi);
// print('Water Analysis Result:', result);

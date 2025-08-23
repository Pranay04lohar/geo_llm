/**
 * Forest Cover Analysis Template for Google Earth Engine
 *
 * Uses Hansen Global Forest Change and Sentinel-2 NDVI for forest analysis
 * Designed specifically for Indian regions with proper boundary clipping
 */

// Template Configuration
var TEMPLATE_CONFIG = {
  name: "forest_cover",
  description:
    "Forest cover analysis, deforestation, and vegetation health assessment",
  datasets: [
    "UMD/hansen/global_forest_change_2022_v1_10",
    "COPERNICUS/S2_SR_HARMONIZED",
    "FAO/GAUL/2015/level0", // For India boundary
  ],
  metrics: [
    "forest_area_km2",
    "forest_percentage",
    "forest_loss_area_km2",
    "forest_gain_area_km2",
    "deforestation_rate",
    "mean_ndvi",
    "tree_cover_density",
  ],
  region: "India",
  example_query: "Analyze forest cover in Kerala",
};

/**
 * Generate forest cover analysis script for given ROI
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
  var treeCoverThreshold = params.treeCoverThreshold || 30; // % tree cover

  // Load India boundary for clipping
  var india = ee
    .FeatureCollection("FAO/GAUL/2015/level0")
    .filter(ee.Filter.eq("ADM0_NAME", "India"));
  var indiaBoundary = india.geometry();

  // Clip ROI to India boundary
  var analysisROI = roi.intersection(indiaBoundary);

  // 1. Hansen Global Forest Change Data
  var hansen = ee.Image("UMD/hansen/global_forest_change_2022_v1_10");

  // Tree cover in year 2000 (percentage)
  var treeCover2000 = hansen.select("treecover2000").clip(analysisROI);

  // Forest loss (2001-2022)
  var forestLoss = hansen.select("loss").clip(analysisROI);

  // Forest gain (2001-2012)
  var forestGain = hansen.select("gain").clip(analysisROI);

  // Year of forest loss
  var lossYear = hansen.select("lossyear").clip(analysisROI);

  // Create forest mask (areas with >30% tree cover in 2000)
  var forestMask2000 = treeCover2000.gte(treeCoverThreshold);

  // Current forest (2000 forest minus losses)
  var currentForest = forestMask2000.and(forestLoss.not());

  // 2. Sentinel-2 NDVI for Current Vegetation Health
  var s2Collection = ee
    .ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(analysisROI)
    .filterDate(startDate, endDate)
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", maxCloudCover));

  var s2Composite = s2Collection.median().clip(analysisROI);

  // Calculate NDVI
  var ndvi = s2Composite.normalizedDifference(["B8", "B4"]).rename("NDVI");

  // High vegetation areas (NDVI > 0.6)
  var highVegetation = ndvi.gt(0.6);

  // 3. Calculate Areas
  var pixelArea = ee.Image.pixelArea();

  // Current forest area
  var forestAreaM2 = pixelArea.multiply(currentForest).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 30,
    maxPixels: 1e9,
  });

  // Forest loss area
  var lossAreaM2 = pixelArea.multiply(forestLoss).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 30,
    maxPixels: 1e9,
  });

  // Forest gain area
  var gainAreaM2 = pixelArea.multiply(forestGain).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 30,
    maxPixels: 1e9,
  });

  // High vegetation area
  var highVegAreaM2 = pixelArea.multiply(highVegetation).reduceRegion({
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

  // Tree cover density statistics
  var treeCoverStats = treeCover2000.reduceRegion({
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

  // NDVI statistics
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
    scale: 30,
    maxPixels: 1e9,
  });

  // Recent forest loss (2020-2022)
  var recentLoss = lossYear.gte(20).and(lossYear.lte(22));
  var recentLossAreaM2 = pixelArea.multiply(recentLoss).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 30,
    maxPixels: 1e9,
  });

  // 5. Format Results
  var results = {
    analysis_type: "forest_cover",
    template_used: "forest_cover.js",
    datasets_used: TEMPLATE_CONFIG.datasets,
    analysis_methods: [
      "Hansen Global Forest Change",
      "Sentinel-2 NDVI Analysis",
      "Tree Cover Density Assessment",
    ],
    forest_area_m2: forestAreaM2,
    forest_loss_area_m2: lossAreaM2,
    forest_gain_area_m2: gainAreaM2,
    recent_loss_area_m2: recentLossAreaM2,
    high_vegetation_area_m2: highVegAreaM2,
    roi_area_m2: roiAreaM2,
    tree_cover_stats: treeCoverStats,
    ndvi_stats: ndviStats,
    image_count: s2Collection.size(),
    processing_info: {
      start_date: startDate,
      end_date: endDate,
      max_cloud_cover: maxCloudCover,
      tree_cover_threshold: treeCoverThreshold,
      analysis_region: "India (clipped)",
      scale_meters: 30,
      hansen_version: "2022_v1_10",
    },
  };

  return results;
}

// Export configuration and function
exports.config = TEMPLATE_CONFIG;
exports.generateScript = generateScript;

// Example usage (for testing):
// var kerala = ee.Geometry.Rectangle([74.85, 8.17, 77.42, 12.79]);
// var result = generateScript(kerala);
// print('Forest Cover Result:', result);

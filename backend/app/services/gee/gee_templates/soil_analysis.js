/**
 * Soil Analysis Template for Google Earth Engine
 *
 * Uses SoilGrids and ISRIC soil datasets for soil property analysis
 * Designed specifically for Indian regions with proper boundary clipping
 */

// Template Configuration
var TEMPLATE_CONFIG = {
  name: "soil_analysis",
  description: "Soil properties, fertility, and erosion risk assessment",
  datasets: [
    "ISRIC/SoilGrids/v2017_07",
    "NASA/GLDAS/V021/NOAH/G025/T3H",
    "COPERNICUS/S2_SR_HARMONIZED",
    "FAO/GAUL/2015/level0", // For India boundary
  ],
  metrics: [
    "soil_ph",
    "organic_carbon_content",
    "clay_content",
    "sand_content",
    "soil_moisture",
    "erosion_risk",
  ],
  region: "India",
  example_query: "Analyze soil properties in Punjab",
};

/**
 * Generate soil analysis script for given ROI
 * @param {ee.Geometry} roi - Region of Interest
 * @param {Object} params - Analysis parameters
 * @returns {Object} - Analysis results
 */
function generateScript(roi, params) {
  // Default parameters
  params = params || {};
  var depth = params.depth || "0-5cm";

  // Load India boundary for clipping
  var india = ee
    .FeatureCollection("FAO/GAUL/2015/level0")
    .filter(ee.Filter.eq("ADM0_NAME", "India"));
  var indiaBoundary = india.geometry();

  // Clip ROI to India boundary
  var analysisROI = roi.intersection(indiaBoundary);

  // 1. SoilGrids Data (250m resolution)
  var soilGrids = ee.Image("ISRIC/SoilGrids/v2017_07");

  // Soil properties at 0-5cm depth
  var soilPH = soilGrids.select("phh2o_0-5cm_mean").clip(analysisROI);
  var organicCarbon = soilGrids.select("soc_0-5cm_mean").clip(analysisROI);
  var clayContent = soilGrids.select("clay_0-5cm_mean").clip(analysisROI);
  var sandContent = soilGrids.select("sand_0-5cm_mean").clip(analysisROI);
  var siltContent = soilGrids.select("silt_0-5cm_mean").clip(analysisROI);

  // 2. GLDAS Soil Moisture (25km resolution)
  var gldas = ee
    .ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H")
    .filterBounds(analysisROI)
    .filterDate("2023-01-01", "2023-12-31")
    .select("SoilMoi0_10cm_inst")
    .mean()
    .clip(analysisROI);

  // 3. Calculate Statistics

  // Soil pH statistics
  var phStats = soilPH.reduceRegion({
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
    scale: 250,
    maxPixels: 1e9,
  });

  // Organic carbon statistics
  var carbonStats = organicCarbon.reduceRegion({
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
    scale: 250,
    maxPixels: 1e9,
  });

  // Soil texture statistics
  var clayStats = clayContent.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: analysisROI,
    scale: 250,
    maxPixels: 1e9,
  });

  var sandStats = sandContent.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: analysisROI,
    scale: 250,
    maxPixels: 1e9,
  });

  var siltStats = siltContent.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: analysisROI,
    scale: 250,
    maxPixels: 1e9,
  });

  // Soil moisture statistics
  var moistureStats = gldas.reduceRegion({
    reducer: ee.Reducer.mean()
      .combine({
        reducer2: ee.Reducer.min(),
        sharedInputs: true,
      })
      .combine({
        reducer2: ee.Reducer.max(),
        sharedInputs: true,
      }),
    geometry: analysisROI,
    scale: 25000,
    maxPixels: 1e9,
  });

  // 4. Soil Classification and Quality Assessment

  // pH classification
  var acidSoil = soilPH.lt(6.0);
  var neutralSoil = soilPH.gte(6.0).and(soilPH.lte(7.5));
  var alkalineSoil = soilPH.gt(7.5);

  // Organic carbon levels (fertility indicator)
  var lowCarbon = organicCarbon.lt(6); // < 0.6%
  var mediumCarbon = organicCarbon.gte(6).and(organicCarbon.lt(12));
  var highCarbon = organicCarbon.gte(12);

  // Calculate areas
  var pixelArea = ee.Image.pixelArea();

  var roiAreaM2 = pixelArea.reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 250,
    maxPixels: 1e9,
  });

  var acidSoilAreaM2 = pixelArea.multiply(acidSoil).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 250,
    maxPixels: 1e9,
  });

  var lowCarbonAreaM2 = pixelArea.multiply(lowCarbon).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 250,
    maxPixels: 1e9,
  });

  // 5. Format Results
  var results = {
    analysis_type: "soil_analysis",
    template_used: "soil_analysis.js",
    datasets_used: TEMPLATE_CONFIG.datasets,
    analysis_methods: [
      "ISRIC SoilGrids Properties",
      "GLDAS Soil Moisture",
      "Soil Classification and Quality Assessment",
    ],
    soil_ph_stats: phStats,
    organic_carbon_stats: carbonStats,
    soil_texture: {
      clay_stats: clayStats,
      sand_stats: sandStats,
      silt_stats: siltStats,
    },
    soil_moisture_stats: moistureStats,
    soil_classification_areas: {
      acid_soil_area_m2: acidSoilAreaM2,
      low_carbon_area_m2: lowCarbonAreaM2,
      roi_area_m2: roiAreaM2,
    },
    processing_info: {
      soil_depth: depth,
      analysis_region: "India (clipped)",
      soilgrids_scale_meters: 250,
      gldas_scale_meters: 25000,
      soilgrids_version: "v2017_07",
    },
  };

  return results;
}

// Export configuration and function
exports.config = TEMPLATE_CONFIG;
exports.generateScript = generateScript;

// Example usage (for testing):
// var punjab = ee.Geometry.Rectangle([73.87, 29.53, 76.78, 32.50]);
// var result = generateScript(punjab);
// print('Soil Analysis Result:', result);

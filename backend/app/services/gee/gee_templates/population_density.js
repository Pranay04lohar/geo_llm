/**
 * Population Density Analysis Template for Google Earth Engine
 *
 * Uses WorldPop and GPW datasets for population analysis
 * Designed specifically for Indian regions with proper boundary clipping
 */

// Template Configuration
var TEMPLATE_CONFIG = {
  name: "population_density",
  description: "Population density analysis and demographic assessment",
  datasets: [
    "WorldPop/GP/100m/pop",
    "CIESIN/GPWv411/GPW_Population_Density",
    "ESA/WorldCover/v200",
    "FAO/GAUL/2015/level0", // For India boundary
  ],
  metrics: [
    "total_population",
    "population_density_per_km2",
    "urban_population",
    "rural_population",
    "population_distribution",
    "demographic_pressure",
  ],
  region: "India",
  example_query: "Analyze population density in Delhi",
};

/**
 * Generate population density analysis script for given ROI
 * @param {ee.Geometry} roi - Region of Interest
 * @param {Object} params - Analysis parameters
 * @returns {Object} - Analysis results
 */
function generateScript(roi, params) {
  // Default parameters
  params = params || {};
  var year = params.year || 2020;

  // Load India boundary for clipping
  var india = ee
    .FeatureCollection("FAO/GAUL/2015/level0")
    .filter(ee.Filter.eq("ADM0_NAME", "India"));
  var indiaBoundary = india.geometry();

  // Clip ROI to India boundary
  var analysisROI = roi.intersection(indiaBoundary);

  // 1. WorldPop Population Data (100m resolution)
  var worldPop = ee
    .ImageCollection("WorldPop/GP/100m/pop")
    .filter(ee.Filter.eq("country", "IND"))
    .filter(ee.Filter.eq("year", year))
    .first()
    .clip(analysisROI);

  // 2. GPW Population Density (1km resolution)
  var gpwPopDensity = ee
    .ImageCollection("CIESIN/GPWv411/GPW_Population_Density")
    .filter(ee.Filter.eq("year", year))
    .first()
    .select("population_density")
    .clip(analysisROI);

  // 3. ESA WorldCover for urban/rural classification
  var landCover = ee.Image("ESA/WorldCover/v200/2021").clip(analysisROI);
  var urbanMask = landCover.eq(50); // Built-up areas
  var ruralMask = urbanMask.not();

  // 4. Calculate Population Statistics

  // Total population
  var totalPopulation = worldPop.reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 100,
    maxPixels: 1e9,
  });

  // Urban population
  var urbanPopulation = worldPop.multiply(urbanMask).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 100,
    maxPixels: 1e9,
  });

  // Rural population
  var ruralPopulation = worldPop.multiply(ruralMask).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 100,
    maxPixels: 1e9,
  });

  // Population density statistics
  var popDensityStats = gpwPopDensity.reduceRegion({
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
    scale: 1000,
    maxPixels: 1e9,
  });

  // 5. Area Calculations
  var pixelArea = ee.Image.pixelArea();

  // Total area
  var roiAreaM2 = pixelArea.reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 100,
    maxPixels: 1e9,
  });

  // Urban area
  var urbanAreaM2 = pixelArea.multiply(urbanMask).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 100,
    maxPixels: 1e9,
  });

  // Rural area
  var ruralAreaM2 = pixelArea.multiply(ruralMask).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 100,
    maxPixels: 1e9,
  });

  // 6. Population Distribution Analysis

  // High density areas (>1000 people/km2)
  var highDensityMask = gpwPopDensity.gt(1000);
  var highDensityAreaM2 = pixelArea.multiply(highDensityMask).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 1000,
    maxPixels: 1e9,
  });

  var highDensityPopulation = worldPop.multiply(highDensityMask).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 100,
    maxPixels: 1e9,
  });

  // Medium density areas (100-1000 people/km2)
  var mediumDensityMask = gpwPopDensity.gt(100).and(gpwPopDensity.lte(1000));
  var mediumDensityAreaM2 = pixelArea.multiply(mediumDensityMask).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 1000,
    maxPixels: 1e9,
  });

  // Low density areas (<100 people/km2)
  var lowDensityMask = gpwPopDensity.lte(100);
  var lowDensityAreaM2 = pixelArea.multiply(lowDensityMask).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 1000,
    maxPixels: 1e9,
  });

  // 7. Format Results
  var results = {
    analysis_type: "population_density",
    template_used: "population_density.js",
    datasets_used: TEMPLATE_CONFIG.datasets,
    analysis_methods: [
      "WorldPop Population Grid",
      "GPW Population Density",
      "ESA WorldCover Urban Classification",
    ],
    total_population: totalPopulation,
    urban_population: urbanPopulation,
    rural_population: ruralPopulation,
    population_density_stats: popDensityStats,
    roi_area_m2: roiAreaM2,
    urban_area_m2: urbanAreaM2,
    rural_area_m2: ruralAreaM2,
    density_distribution: {
      high_density_area_m2: highDensityAreaM2,
      medium_density_area_m2: mediumDensityAreaM2,
      low_density_area_m2: lowDensityAreaM2,
      high_density_population: highDensityPopulation,
    },
    processing_info: {
      analysis_year: year,
      analysis_region: "India (clipped)",
      worldpop_scale_meters: 100,
      gpw_scale_meters: 1000,
      urban_rural_classification: "ESA WorldCover Built-up",
    },
  };

  return results;
}

// Export configuration and function
exports.config = TEMPLATE_CONFIG;
exports.generateScript = generateScript;

// Example usage (for testing):
// var delhi = ee.Geometry.Rectangle([76.68, 28.57, 77.53, 28.84]);
// var result = generateScript(delhi, {year: 2020});
// print('Population Density Result:', result);

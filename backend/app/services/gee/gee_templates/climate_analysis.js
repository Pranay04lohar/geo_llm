/**
 * Climate Analysis Template for Google Earth Engine
 *
 * Uses multiple climate datasets for comprehensive weather and climate analysis
 * Designed specifically for Indian regions with proper boundary clipping
 */

// Template Configuration
var TEMPLATE_CONFIG = {
  name: "climate_analysis",
  description:
    "Climate patterns, weather analysis, and environmental monitoring",
  datasets: [
    "ECMWF/ERA5_LAND/DAILY_AGGR",
    "NASA/GLDAS/V021/NOAH/G025/T3H",
    "MODIS/061/MOD11A1",
    "COPERNICUS/S5P/NRTI/L3_NO2",
    "COPERNICUS/S5P/NRTI/L3_CO",
    "COPERNICUS/S5P/NRTI/L3_SO2",
    "COPERNICUS/S2_SR_HARMONIZED",
    "FAO/GAUL/2015/level0", // For India boundary
  ],
  metrics: [
    "temperature_stats",
    "precipitation_total",
    "humidity_levels",
    "air_quality_index",
    "vegetation_health",
    "seasonal_patterns",
    "extreme_weather_events",
  ],
  region: "India",
  example_query: "Analyze climate patterns in Mumbai",
};

/**
 * Generate climate analysis script for given ROI
 * @param {ee.Geometry} roi - Region of Interest
 * @param {Object} params - Analysis parameters
 * @returns {Object} - Analysis results
 */
function generateScript(roi, params) {
  // Default parameters
  params = params || {};
  var startDate = params.startDate || "2023-01-01";
  var endDate = params.endDate || "2023-12-31";
  var analysisYear = params.analysisYear || 2023;

  // Load India boundary for clipping
  var india = ee
    .FeatureCollection("FAO/GAUL/2015/level0")
    .filter(ee.Filter.eq("ADM0_NAME", "India"));
  var indiaBoundary = india.geometry();

  // Clip ROI to India boundary
  var analysisROI = roi.intersection(indiaBoundary);

  // 1. ERA5 Land Climate Data (Daily, 11km resolution)
  var era5Land = ee
    .ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
    .filterBounds(analysisROI)
    .filterDate(startDate, endDate);

  // Temperature analysis
  var temperature2m = era5Land.select("temperature_2m");
  var tempStats = temperature2m.reduce(
    ee.Reducer.mean()
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
      })
  );

  // Precipitation analysis
  var precipitation = era5Land.select("total_precipitation_sum");
  var precipSum = precipitation.reduce(ee.Reducer.sum());
  var precipMean = precipitation.reduce(ee.Reducer.mean());

  // 2. GLDAS Hydrological Data (3-hourly, 25km resolution)
  var gldas = ee
    .ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H")
    .filterBounds(analysisROI)
    .filterDate(startDate, endDate);

  // Soil moisture and evapotranspiration
  var soilMoisture = gldas.select("SoilMoi0_10cm_inst").mean();
  var evapotranspiration = gldas.select("Evap_tavg").mean();
  var humidity = gldas.select("Qair_f_inst").mean();

  // 3. MODIS Land Surface Temperature (Daily, 1km resolution)
  var modisLST = ee
    .ImageCollection("MODIS/061/MOD11A1")
    .filterBounds(analysisROI)
    .filterDate(startDate, endDate)
    .select(["LST_Day_1km", "LST_Night_1km"]);

  var dayTemp = modisLST
    .select("LST_Day_1km")
    .mean()
    .multiply(0.02)
    .subtract(273.15); // Convert to Celsius
  var nightTemp = modisLST
    .select("LST_Night_1km")
    .mean()
    .multiply(0.02)
    .subtract(273.15);

  // 4. Sentinel-5P Air Quality Data
  var no2 = ee
    .ImageCollection("COPERNICUS/S5P/NRTI/L3_NO2")
    .filterBounds(analysisROI)
    .filterDate(startDate, endDate)
    .select("tropospheric_NO2_column_number_density")
    .mean();

  var co = ee
    .ImageCollection("COPERNICUS/S5P/NRTI/L3_CO")
    .filterBounds(analysisROI)
    .filterDate(startDate, endDate)
    .select("CO_column_number_density")
    .mean();

  var so2 = ee
    .ImageCollection("COPERNICUS/S5P/NRTI/L3_SO2")
    .filterBounds(analysisROI)
    .filterDate(startDate, endDate)
    .select("SO2_column_number_density")
    .mean();

  // 5. Sentinel-2 for Vegetation Health (NDVI)
  var s2Collection = ee
    .ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(analysisROI)
    .filterDate(startDate, endDate)
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20));

  var s2Composite = s2Collection.median().clip(analysisROI);
  var ndvi = s2Composite.normalizedDifference(["B8", "B4"]).rename("NDVI");

  // Vegetation health classification
  var healthyVeg = ndvi.gt(0.6); // Healthy vegetation
  var moderateVeg = ndvi.gt(0.3).and(ndvi.lte(0.6)); // Moderate vegetation
  var stressedVeg = ndvi.gt(0.1).and(ndvi.lte(0.3)); // Stressed vegetation

  // 6. Calculate Statistics

  // Climate statistics
  var climateStats = tempStats.clip(analysisROI).reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: analysisROI,
    scale: 11000,
    maxPixels: 1e9,
  });

  var precipStats = precipSum.clip(analysisROI).reduceRegion({
    reducer: ee.Reducer.mean().combine({
      reducer2: ee.Reducer.sum(),
      sharedInputs: true,
    }),
    geometry: analysisROI,
    scale: 11000,
    maxPixels: 1e9,
  });

  // Air quality statistics
  var aqStats = ee.Image([no2, co, so2]).clip(analysisROI).reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: analysisROI,
    scale: 7000,
    maxPixels: 1e9,
  });

  // Vegetation statistics
  var vegStats = ndvi.reduceRegion({
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
    scale: 10,
    maxPixels: 1e9,
  });

  // Land surface temperature statistics
  var lstStats = ee.Image([dayTemp, nightTemp]).reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: analysisROI,
    scale: 1000,
    maxPixels: 1e9,
  });

  // Hydrological statistics
  var hydroStats = ee
    .Image([soilMoisture, evapotranspiration, humidity])
    .clip(analysisROI)
    .reduceRegion({
      reducer: ee.Reducer.mean(),
      geometry: analysisROI,
      scale: 25000,
      maxPixels: 1e9,
    });

  // 7. Area Calculations
  var pixelArea = ee.Image.pixelArea();

  // Total ROI area
  var roiAreaM2 = pixelArea.reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 1000,
    maxPixels: 1e9,
  });

  // Vegetation health areas
  var healthyVegAreaM2 = pixelArea.multiply(healthyVeg).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 10,
    maxPixels: 1e9,
  });

  var moderateVegAreaM2 = pixelArea.multiply(moderateVeg).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 10,
    maxPixels: 1e9,
  });

  var stressedVegAreaM2 = pixelArea.multiply(stressedVeg).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: analysisROI,
    scale: 10,
    maxPixels: 1e9,
  });

  // 8. Seasonal Analysis
  var seasons = {
    winter: ee.Filter.dayOfYear(1, 90).or(ee.Filter.dayOfYear(335, 365)),
    summer: ee.Filter.dayOfYear(91, 180),
    monsoon: ee.Filter.dayOfYear(181, 273),
    postMonsoon: ee.Filter.dayOfYear(274, 334),
  };

  var seasonalTemp = {};
  var seasonalPrecip = {};

  Object.keys(seasons).forEach(function (season) {
    var seasonFilter = seasons[season];
    var seasonTemp = era5Land
      .filter(seasonFilter)
      .select("temperature_2m")
      .mean()
      .subtract(273.15); // Convert to Celsius
    var seasonPrecip = era5Land
      .filter(seasonFilter)
      .select("total_precipitation_sum")
      .sum();

    seasonalTemp[season] = seasonTemp.clip(analysisROI).reduceRegion({
      reducer: ee.Reducer.mean(),
      geometry: analysisROI,
      scale: 11000,
      maxPixels: 1e9,
    });

    seasonalPrecip[season] = seasonPrecip.clip(analysisROI).reduceRegion({
      reducer: ee.Reducer.mean(),
      geometry: analysisROI,
      scale: 11000,
      maxPixels: 1e9,
    });
  });

  // 9. Format Results
  var results = {
    analysis_type: "climate_analysis",
    template_used: "climate_analysis.js",
    datasets_used: TEMPLATE_CONFIG.datasets,
    analysis_methods: [
      "ERA5 Land Climate Reanalysis",
      "GLDAS Hydrological Data",
      "MODIS Land Surface Temperature",
      "Sentinel-5P Air Quality",
      "Sentinel-2 Vegetation Health",
    ],
    climate_statistics: climateStats,
    precipitation_statistics: precipStats,
    air_quality_statistics: aqStats,
    vegetation_statistics: vegStats,
    land_surface_temperature: lstStats,
    hydrological_statistics: hydroStats,
    seasonal_patterns: {
      temperature: seasonalTemp,
      precipitation: seasonalPrecip,
    },
    vegetation_health_areas: {
      healthy_vegetation_m2: healthyVegAreaM2,
      moderate_vegetation_m2: moderateVegAreaM2,
      stressed_vegetation_m2: stressedVegAreaM2,
    },
    roi_area_m2: roiAreaM2,
    image_counts: {
      era5_images: era5Land.size(),
      gldas_images: gldas.size(),
      modis_images: modisLST.size(),
      s2_images: s2Collection.size(),
    },
    processing_info: {
      start_date: startDate,
      end_date: endDate,
      analysis_year: analysisYear,
      analysis_region: "India (clipped)",
      era5_scale_meters: 11000,
      gldas_scale_meters: 25000,
      modis_scale_meters: 1000,
      s5p_scale_meters: 7000,
      s2_scale_meters: 10,
    },
  };

  return results;
}

// Export configuration and function
exports.config = TEMPLATE_CONFIG;
exports.generateScript = generateScript;

// Example usage (for testing):
// var mumbai = ee.Geometry.Rectangle([72.77, 18.89, 72.97, 19.27]);
// var result = generateScript(mumbai, {startDate: '2023-06-01', endDate: '2023-08-31'});
// print('Climate Analysis Result:', result);

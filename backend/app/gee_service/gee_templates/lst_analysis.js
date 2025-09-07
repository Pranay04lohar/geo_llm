/**
 * Land Surface Temperature (LST) Analysis Template
 * 
 * This template provides LST analysis using MODIS MOD11A2 data.
 * It supports both basic LST analysis and Urban Heat Island calculations.
 * 
 * Usage:
 * - Replace {{GEOMETRY}} with the actual geometry
 * - Replace {{START_DATE}} and {{END_DATE}} with date strings
 * - Replace {{SCALE}} with the desired scale in meters
 * - Replace {{MAX_PIXELS}} with the maximum pixels limit
 */

// Load MODIS LST collection
var lstCollection = ee.ImageCollection('MODIS/006/MOD11A2')
  .filterDate('{{START_DATE}}', '{{END_DATE}}')
  .filter(ee.Filter.lt('CLOUD_COVER', 20));

// Function to preprocess LST data
function preprocessLST(image) {
  // Convert Kelvin to Celsius and mask invalid pixels
  var lst = image.select('LST_Day_1km')
    .multiply(0.02)
    .subtract(273.15)
    .updateMask(
      image.select('LST_Day_1km').gt(0)  // Mask invalid LST values
    );
  
  // Add quality band for additional masking
  var qa = image.select('QC_Day');
  lst = lst.updateMask(qa.eq(0).Or(qa.eq(1)));  // Good quality pixels only
  
  return lst.rename('LST');
}

// Process the collection
var processedCollection = lstCollection.map(preprocessLST);

// Check if we have data
if (processedCollection.size().get(0) === 0) {
  // Return error if no data
  var result = {
    success: false,
    error: 'No MODIS LST data available for the specified date range',
    error_type: 'no_data'
  };
} else {
  // Get the geometry
  var geometry = {{GEOMETRY}};
  
  // Create median composite
  var medianLST = processedCollection.select('LST').median().clip(geometry);
  
  // Calculate statistics
  var stats = medianLST.reduceRegion({
    reducer: ee.Reducer.mean().combine(
      ee.Reducer.minMax(), '', true
    ).combine(ee.Reducer.stdDev(), '', true),
    geometry: geometry,
    scale: {{SCALE}},
    maxPixels: {{MAX_PIXELS}},
    bestEffort: true
  });
  
  // Calculate area
  var area = geometry.area().divide(1e6); // Convert to km²
  
  // Generate visualization
  var visParams = {
    min: 20,
    max: 40,
    palette: ['#2c7bb6', '#abd9e9', '#ffffbf', '#fdae61', '#d7191c']
  };
  
  var mapId = medianLST.getMapId(visParams);
  var tileUrl = 'https://earthengine.googleapis.com/map/' + mapId.mapid + '/{z}/{x}/{y}?token=' + mapId.token;
  
  // Calculate UHI intensity (simplified)
  var lstMean = medianLST.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: geometry,
    scale: {{SCALE}},
    maxPixels: {{MAX_PIXELS}},
    bestEffort: true
  });
  
  var baseTemp = 25.0; // Baseline temperature
  var uhiIntensity = Math.max(0, lstMean.get('LST') - baseTemp);
  
  // Prepare result
  var result = {
    success: true,
    analysis_type: 'lst_analysis',
    geometry_type: 'single_polygon',
    area_km2: area.getInfo(),
    lst_stats: {
      LST_mean: stats.get('LST_mean') || stats.get('mean') || 0,
      LST_min: stats.get('LST_min') || stats.get('min') || 0,
      LST_max: stats.get('LST_max') || stats.get('max') || 0,
      LST_stdDev: stats.get('LST_stdDev') || stats.get('stdDev') || 0
    },
    uhi_intensity: uhiIntensity,
    tile_urls: {
      urlFormat: tileUrl
    },
    legend_config: {
      labelNames: ['Cool', 'Moderate', 'Hot', 'Extreme'],
      palette: ['#2c7bb6', '#abd9e9', '#ffffbf', '#fdae61', '#d7191c'],
      breaks: [20, 25, 30, 35, 40],
      unit: '°C'
    },
    extraDescription: 'Values in °C, derived from MODIS MOD11A2 (8-day composites).',
    image_count: processedCollection.size().getInfo()
  };
}

// Return the result
result;

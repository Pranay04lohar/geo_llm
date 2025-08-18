"""
GEE Script Templates

This module contains Google Earth Engine script templates for different types
of geospatial analysis. Templates are used by the ScriptGenerator to create
dynamic GEE scripts based on user queries and analysis requirements.

Template Types:
- ndvi_analysis.py: NDVI vegetation health analysis
- landcover_analysis.py: Land cover classification
- change_detection.py: Temporal change analysis
- water_analysis.py: Water body detection and analysis
- basic_stats.py: General purpose statistics

Templates use string formatting to inject parameters like ROI, dates, and datasets.
"""

__version__ = "1.0.0"

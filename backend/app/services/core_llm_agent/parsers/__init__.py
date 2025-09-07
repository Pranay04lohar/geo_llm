"""
Parsers module - Extract and resolve entities from user queries.

Components:
- LocationParser: Orchestrates location extraction and resolution
- LocationNER: LLM-based named entity recognition for locations
- NominatimClient: OSM Nominatim API integration for geocoding
"""

from .location_parser import LocationParser
from .location_ner import LocationNER
from .nominatim_client import NominatimClient

__all__ = ["LocationParser", "LocationNER", "NominatimClient"]

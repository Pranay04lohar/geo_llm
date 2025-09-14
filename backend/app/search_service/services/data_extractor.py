"""
Data Extractor - Extracts and validates structured data from search results.

This module provides functionality to:
- Extract numerical values and metrics from text
- Validate data quality and credibility
- Structure geospatial data for analysis
- Filter and rank data by relevance and accuracy
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

@dataclass
class ExtractedMetric:
    """Represents an extracted metric with validation info."""
    value: float
    unit: str
    context: str
    source: str
    confidence: float
    data_type: str
    location: Optional[str] = None
    timestamp: Optional[str] = None

@dataclass
class DataQuality:
    """Represents data quality assessment."""
    credibility_score: float
    recency_score: float
    completeness_score: float
    accuracy_score: float
    overall_score: float

class DataExtractor:
    """Extracts and validates structured data from search results."""
    
    def __init__(self):
        # Patterns for different types of geospatial data
        self.patterns = {
            "temperature": [
                # Specific temperature values
                r'(\d+(?:\.\d+)?)\s*°?[CcFf]',  # 25°C, 30C, 25°F, 30F
                r'(\d+(?:\.\d+)?)\s*degrees?\s*(?:celsius|fahrenheit|centigrade)',  # 25 degrees celsius
                r'(\d+(?:\.\d+)?)\s*°C',  # 25°C
                r'(\d+(?:\.\d+)?)\s*°F',  # 25°F
                # Temperature ranges
                r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*°?[CcFf]',  # 25-30°C
                r'(\d+(?:\.\d+)?)\s*to\s*(\d+(?:\.\d+)?)\s*°?[CcFf]',  # 25 to 30°C
                r'between\s*(\d+(?:\.\d+)?)\s*and\s*(\d+(?:\.\d+)?)\s*°?[CcFf]',  # between 25 and 30°C
                # Temperature with context
                r'temperature\s*(?:of|at|around|about)\s*(\d+(?:\.\d+)?)\s*°?[CcFf]',  # temperature of 25°C
                r'LST\s*(?:of|at|around|about)\s*(\d+(?:\.\d+)?)\s*°?[CcFf]',  # LST of 25°C
                r'(\d+(?:\.\d+)?)\s*°?[CcFf]\s*(?:temperature|LST|heat)',  # 25°C temperature
                # Academic paper patterns for specific values
                r'(\d+(?:\.\d+)?)\s*°?[CcFf]\s*(?:±\s*\d+(?:\.\d+)?)?',  # 25°C ±2
                r'(\d+(?:\.\d+)?)\s*°?[CcFf]\s*(?:±\s*\d+(?:\.\d+)?\s*°?[CcFf])?',  # 25°C ±2°C
                r'(\d+(?:\.\d+)?)\s*°?[CcFf]\s*(?:\(\s*\d+(?:\.\d+)?\s*°?[CcFf]\s*\))?',  # 25°C (23°C)
                r'(\d+(?:\.\d+)?)\s*°?[CcFf]\s*(?:mean|average|maximum|minimum|max|min)',  # 25°C mean
                r'(?:mean|average|maximum|minimum|max|min)\s*temperature\s*(\d+(?:\.\d+)?)\s*°?[CcFf]',  # mean temperature 25°C
                r'(\d+(?:\.\d+)?)\s*°?[CcFf]\s*(?:range|variation)',  # 25°C range
                # Thermal data mentions (these will be treated as context, not specific values)
                r'thermal\s*data',  # thermal data
                r'temperature\s*analysis',  # temperature analysis
                r'heat\s*island',  # heat island
                r'urban\s*heat',  # urban heat
                r'land\s*surface\s*temperature',  # land surface temperature
                r'LST\s*analysis',  # LST analysis
                r'temperature\s*variation',  # temperature variation
                r'thermal\s*comfort',  # thermal comfort
                r'surface\s*temperature',  # surface temperature
                r'air\s*temperature',  # air temperature
                r'ambient\s*temperature'  # ambient temperature
            ],
            "percentage": [
                r'(\d+(?:\.\d+)?)\s*%',
                r'(\d+(?:\.\d+)?)\s*percent',
                r'(\d+(?:\.\d+)?)\s*percentage'
            ],
            "area": [
                r'(\d+(?:,\d+)*(?:\.\d+)?)\s*km²',
                r'(\d+(?:,\d+)*(?:\.\d+)?)\s*km2',
                r'(\d+(?:,\d+)*(?:\.\d+)?)\s*square\s*kilometers?',
                r'(\d+(?:,\d+)*(?:\.\d+)?)\s*sq\s*km'
            ],
            "ndvi": [
                r'NDVI[:\s]*(\d+(?:\.\d+)?)',
                r'(\d+(?:\.\d+)?)\s*NDVI',
                r'vegetation\s*index[:\s]*(\d+(?:\.\d+)?)',
                r'greenness\s*index[:\s]*(\d+(?:\.\d+)?)'
            ],
            "population": [
                r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:million|billion|thousand)\s*people',
                r'(\d+(?:,\d+)*(?:\.\d+)?)\s*inhabitants?',
                r'(\d+(?:,\d+)*(?:\.\d+)?)\s*residents?',
                r'population[:\s]*(\d+(?:,\d+)*(?:\.\d+)?)'
            ],
            "coordinates": [
                r'(\d+(?:\.\d+)?)°[NS]\s*,\s*(\d+(?:\.\d+)?)°[EW]',
                r'lat[itude]?[:\s]*(\d+(?:\.\d+)?)[°\s]*[NS]',
                r'lon[gitude]?[:\s]*(\d+(?:\.\d+)?)[°\s]*[EW]'
            ]
        }
        
        # Units mapping
        self.units = {
            "temperature": ["°C", "°F", "celsius", "fahrenheit", "degrees"],
            "percentage": ["%", "percent", "percentage"],
            "area": ["km²", "km2", "square kilometers", "sq km"],
            "ndvi": ["NDVI", "vegetation index", "greenness index"],
            "population": ["million", "billion", "thousand", "people", "inhabitants"],
            "coordinates": ["°N", "°S", "°E", "°W", "latitude", "longitude"]
        }
        
        # Credible domains for data validation
        self.credible_domains = {
            "government": [".gov", ".nic.in", "government", "ministry", "department"],
            "academic": [".edu", "researchgate", "academia", "scholar", "jstor"],
            "international": ["un.org", "who.int", "unep.org", "nasa.gov", "esa.int"],
            "research": ["nature.com", "springer.com", "ieee.org", "sciencedirect.com"]
        }
        
        # Recent time indicators
        self.recent_indicators = [
            "2024", "2023", "recent", "latest", "current", "this year",
            "last year", "latest data", "updated", "newest"
        ]
    
    def extract_metrics(
        self, 
        search_results: List[Dict[str, Any]], 
        analysis_type: str
    ) -> List[ExtractedMetric]:
        """
        Extract structured metrics from search results.
        
        Args:
            search_results: List of search results
            analysis_type: Type of analysis being performed
            
        Returns:
            List of extracted metrics with validation info
        """
        try:
            logger.info(f"Extracting metrics from {len(search_results)} results for {analysis_type}")
            
            # Debug: Show what patterns we're looking for
            logger.info(f"Looking for patterns for analysis type: {analysis_type}")
            if analysis_type == "lst":
                logger.info(f"Temperature patterns: {self.patterns['temperature']}")
                logger.info(f"Area patterns: {self.patterns['area']}")
            elif analysis_type == "ndvi":
                logger.info(f"NDVI patterns: {self.patterns['ndvi']}")
                logger.info(f"Percentage patterns: {self.patterns['percentage']}")
            
            all_metrics = []
            
            for result in search_results:
                content = result.get("content", "")
                title = result.get("title", "")
                url = result.get("url", "")
                source = f"{title} ({url})"
                
                # Extract different types of metrics
                metrics = []
                
                # Temperature metrics
                if analysis_type in ["lst", "climate"]:
                    temp_metrics = self._extract_temperature_metrics(content, source)
                    metrics.extend(temp_metrics)
                
                # NDVI metrics
                if analysis_type == "ndvi":
                    ndvi_metrics = self._extract_ndvi_metrics(content, source)
                    metrics.extend(ndvi_metrics)
                
                # Area and percentage metrics
                area_metrics = self._extract_area_metrics(content, source)
                metrics.extend(area_metrics)
                
                percentage_metrics = self._extract_percentage_metrics(content, source)
                metrics.extend(percentage_metrics)
                
                # Population metrics
                pop_metrics = self._extract_population_metrics(content, source)
                metrics.extend(pop_metrics)
                
                # Coordinate metrics
                coord_metrics = self._extract_coordinate_metrics(content, source)
                metrics.extend(coord_metrics)
                
                all_metrics.extend(metrics)
            
            logger.info(f"Total metrics before validation: {len(all_metrics)}")
            
            # Filter and validate metrics
            validated_metrics = self._validate_metrics(all_metrics, analysis_type)
            
            logger.info(f"Extracted {len(validated_metrics)} validated metrics")
            return validated_metrics
            
        except Exception as e:
            logger.error(f"Error extracting metrics: {e}")
            return []
    
    def _extract_temperature_metrics(self, content: str, source: str) -> List[ExtractedMetric]:
        """Extract temperature-related metrics."""
        metrics = []
        
        logger.info(f"Extracting temperature metrics from content: {content[:200]}...")
        
        for i, pattern in enumerate(self.patterns["temperature"]):
            logger.info(f"  Trying pattern {i+1}: {pattern}")
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            logger.info(f"  Found {len(matches)} matches")
            
            for j, match in enumerate(matches):
                logger.info(f"    Match {j+1}: '{match.group(0)}'")
                try:
                    # Handle patterns with specific temperature values (patterns with numbers and units)
                    if (r'(\d+(?:\.\d+)?)\s*°?[CcFf]' in pattern or 
                        r'(\d+(?:\.\d+)?)\s*degrees?' in pattern or
                        r'(\d+(?:\.\d+)?)\s*°?[CcFf]\s*(?:±|\(|mean|average|maximum|minimum|max|min|range|variation)' in pattern or
                        r'(?:mean|average|maximum|minimum|max|min)\s*temperature\s*(\d+(?:\.\d+)?)\s*°?[CcFf]' in pattern):
                        # This is a pattern with a specific temperature value
                        value = float(match.group(1))
                        unit = self._extract_unit(match.group(0), "temperature")
                        
                        # Convert to Celsius if needed
                        if unit in ["°F", "fahrenheit"]:
                            value = (value - 32) * 5/9
                            unit = "°C"
                        
                        metric = ExtractedMetric(
                            value=value,
                            unit=unit,
                            context=match.group(0),
                            source=source,
                            confidence=self._calculate_confidence(match.group(0), "temperature"),
                            data_type="temperature"
                        )
                        metrics.append(metric)
                        logger.info(f"    ✅ Created temperature metric: {value} {unit}")
                    
                    # Handle patterns with temperature ranges
                    elif r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)' in pattern or r'(\d+(?:\.\d+)?)\s*to\s*(\d+(?:\.\d+)?)' in pattern or r'between\s*(\d+(?:\.\d+)?)\s*and\s*(\d+(?:\.\d+)?)' in pattern:
                        # This is a temperature range pattern
                        try:
                            value1 = float(match.group(1))
                            value2 = float(match.group(2))
                            unit = self._extract_unit(match.group(0), "temperature")
                            
                            # Convert to Celsius if needed
                            if unit in ["°F", "fahrenheit"]:
                                value1 = (value1 - 32) * 5/9
                                value2 = (value2 - 32) * 5/9
                                unit = "°C"
                            
                            # Create metric for the range (use average)
                            avg_value = (value1 + value2) / 2
                            metric = ExtractedMetric(
                                value=avg_value,
                                unit=unit,
                                context=f"{value1}-{value2}{unit}",
                                source=source,
                                confidence=self._calculate_confidence(match.group(0), "temperature"),
                                data_type="temperature_range"
                            )
                            metrics.append(metric)
                            logger.info(f"    ✅ Created temperature range metric: {value1}-{value2}{unit} (avg: {avg_value})")
                        except (ValueError, IndexError):
                            logger.info(f"    ❌ Failed to parse temperature range: {match.group(0)}")
                            continue
                    
                    # Handle context patterns (thermal data mentions)
                    else:
                        # This is a context pattern indicating thermal data presence
                        metric = ExtractedMetric(
                            value=0.0,  # No specific value
                            unit="context",
                            context=match.group(0),
                            source=source,
                            confidence=0.3,  # Lower confidence for context-only matches
                            data_type="temperature_context"
                        )
                        metrics.append(metric)
                        logger.info(f"    ✅ Created temperature context metric: {match.group(0)}")
                        
                except (ValueError, IndexError) as e:
                    logger.info(f"    ❌ Failed to create metric: {e}")
                    continue
        
        logger.info(f"Total temperature metrics extracted: {len(metrics)}")
        
        # Debug: Show what metrics were created
        for i, metric in enumerate(metrics):
            logger.info(f"  Metric {i+1}: {metric.data_type} - {metric.context} (value: {metric.value}, unit: {metric.unit})")
        
        return metrics
    
    def _extract_ndvi_metrics(self, content: str, source: str) -> List[ExtractedMetric]:
        """Extract NDVI-related metrics."""
        metrics = []
        
        for pattern in self.patterns["ndvi"]:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    value = float(match.group(1))
                    
                    # Validate NDVI range (0-1)
                    if 0 <= value <= 1:
                        metric = ExtractedMetric(
                            value=value,
                            unit="NDVI",
                            context=match.group(0),
                            source=source,
                            confidence=self._calculate_confidence(match.group(0), "ndvi"),
                            data_type="ndvi"
                        )
                        metrics.append(metric)
                except (ValueError, IndexError):
                    continue
        
        return metrics
    
    def _extract_area_metrics(self, content: str, source: str) -> List[ExtractedMetric]:
        """Extract area-related metrics."""
        metrics = []
        
        for pattern in self.patterns["area"]:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    value_str = match.group(1).replace(',', '')
                    value = float(value_str)
                    
                    metric = ExtractedMetric(
                        value=value,
                        unit="km²",
                        context=match.group(0),
                        source=source,
                        confidence=self._calculate_confidence(match.group(0), "area"),
                        data_type="area"
                    )
                    metrics.append(metric)
                except (ValueError, IndexError):
                    continue
        
        return metrics
    
    def _extract_percentage_metrics(self, content: str, source: str) -> List[ExtractedMetric]:
        """Extract percentage-related metrics."""
        metrics = []
        
        for pattern in self.patterns["percentage"]:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    value = float(match.group(1))
                    
                    metric = ExtractedMetric(
                        value=value,
                        unit="%",
                        context=match.group(0),
                        source=source,
                        confidence=self._calculate_confidence(match.group(0), "percentage"),
                        data_type="percentage"
                    )
                    metrics.append(metric)
                except (ValueError, IndexError):
                    continue
        
        return metrics
    
    def _extract_population_metrics(self, content: str, source: str) -> List[ExtractedMetric]:
        """Extract population-related metrics."""
        metrics = []
        
        for pattern in self.patterns["population"]:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    value_str = match.group(1).replace(',', '')
                    value = float(value_str)
                    
                    # Extract unit multiplier
                    unit_text = match.group(0).lower()
                    if "million" in unit_text:
                        value *= 1000000
                        unit = "people"
                    elif "billion" in unit_text:
                        value *= 1000000000
                        unit = "people"
                    elif "thousand" in unit_text:
                        value *= 1000
                        unit = "people"
                    else:
                        unit = "people"
                    
                    metric = ExtractedMetric(
                        value=value,
                        unit=unit,
                        context=match.group(0),
                        source=source,
                        confidence=self._calculate_confidence(match.group(0), "population"),
                        data_type="population"
                    )
                    metrics.append(metric)
                except (ValueError, IndexError):
                    continue
        
        return metrics
    
    def _extract_coordinate_metrics(self, content: str, source: str) -> List[ExtractedMetric]:
        """Extract coordinate-related metrics."""
        metrics = []
        
        for pattern in self.patterns["coordinates"]:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    if len(match.groups()) == 2:
                        lat = float(match.group(1))
                        lon = float(match.group(2))
                        
                        # Validate coordinate ranges
                        if -90 <= lat <= 90 and -180 <= lon <= 180:
                            metric = ExtractedMetric(
                                value=f"{lat},{lon}",
                                unit="coordinates",
                                context=match.group(0),
                                source=source,
                                confidence=self._calculate_confidence(match.group(0), "coordinates"),
                                data_type="coordinates"
                            )
                            metrics.append(metric)
                except (ValueError, IndexError):
                    continue
        
        return metrics
    
    def _extract_unit(self, text: str, metric_type: str) -> str:
        """Extract unit from text."""
        text_lower = text.lower()
        
        for unit in self.units.get(metric_type, []):
            if unit.lower() in text_lower:
                return unit
        
        return "unknown"
    
    def _calculate_confidence(self, context: str, metric_type: str) -> float:
        """Calculate confidence score for a metric."""
        confidence = 0.5  # Base confidence
        
        # Boost confidence for specific patterns
        if metric_type == "temperature" and "°" in context:
            confidence += 0.2
        elif metric_type == "ndvi" and "NDVI" in context.upper():
            confidence += 0.3
        elif metric_type == "area" and "km" in context.lower():
            confidence += 0.2
        elif metric_type == "percentage" and "%" in context:
            confidence += 0.2
        
        # Boost confidence for numerical precision
        if "." in context:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _validate_metrics(
        self, 
        metrics: List[ExtractedMetric], 
        analysis_type: str
    ) -> List[ExtractedMetric]:
        """Validate and filter metrics based on analysis type."""
        validated = []
        
        for metric in metrics:
            # Basic validation
            if metric.confidence < 0.3:
                continue
            
            # Type-specific validation
            if analysis_type == "ndvi" and metric.data_type == "ndvi":
                if 0 <= metric.value <= 1:
                    validated.append(metric)
            elif analysis_type == "lst" and metric.data_type in ["temperature", "temperature_context", "temperature_range"]:
                if metric.data_type == "temperature_context" or (-50 <= metric.value <= 60):  # Context metrics or reasonable temperature range
                    validated.append(metric)
            elif analysis_type == "lulc" and metric.data_type == "percentage":
                if 0 <= metric.value <= 100:
                    validated.append(metric)
            elif metric.data_type in ["area", "population", "coordinates"]:
                if metric.value > 0:
                    validated.append(metric)
            # Accept context metrics for any analysis type
            elif metric.data_type.endswith("_context"):
                validated.append(metric)
        
        # Sort by confidence
        validated.sort(key=lambda x: x.confidence, reverse=True)
        
        return validated
    
    def assess_data_quality(
        self, 
        search_results: List[Dict[str, Any]], 
        extracted_metrics: List[ExtractedMetric]
    ) -> DataQuality:
        """Assess overall data quality."""
        try:
            # Credibility score based on source domains
            credibility_score = self._calculate_credibility_score(search_results)
            
            # Recency score based on publication dates and content
            recency_score = self._calculate_recency_score(search_results)
            
            # Completeness score based on metric diversity
            completeness_score = self._calculate_completeness_score(extracted_metrics)
            
            # Accuracy score based on metric confidence
            accuracy_score = self._calculate_accuracy_score(extracted_metrics)
            
            # Overall score (weighted average)
            overall_score = (
                credibility_score * 0.3 +
                recency_score * 0.2 +
                completeness_score * 0.25 +
                accuracy_score * 0.25
            )
            
            return DataQuality(
                credibility_score=credibility_score,
                recency_score=recency_score,
                completeness_score=completeness_score,
                accuracy_score=accuracy_score,
                overall_score=overall_score
            )
            
        except Exception as e:
            logger.error(f"Error assessing data quality: {e}")
            return DataQuality(0.5, 0.5, 0.5, 0.5, 0.5)
    
    def _calculate_credibility_score(self, search_results: List[Dict[str, Any]]) -> float:
        """Calculate credibility score based on source domains."""
        if not search_results:
            return 0.0
        
        total_score = 0.0
        for result in search_results:
            url = result.get("url", "").lower()
            score = 0.0
            
            # Check for credible domains
            for domain_type, domains in self.credible_domains.items():
                if any(domain in url for domain in domains):
                    if domain_type == "government":
                        score = 0.9
                    elif domain_type == "academic":
                        score = 0.8
                    elif domain_type == "international":
                        score = 0.85
                    elif domain_type == "research":
                        score = 0.75
                    break
            
            # Default score for unknown domains
            if score == 0.0:
                score = 0.4
            
            total_score += score
        
        return total_score / len(search_results)
    
    def _calculate_recency_score(self, search_results: List[Dict[str, Any]]) -> float:
        """Calculate recency score based on publication dates and content."""
        if not search_results:
            return 0.0
        
        recent_count = 0
        for result in search_results:
            content = result.get("content", "").lower()
            title = result.get("title", "").lower()
            
            # Check for recent indicators
            if any(indicator in content or indicator in title for indicator in self.recent_indicators):
                recent_count += 1
        
        return min(1.0, recent_count / len(search_results) + 0.3)
    
    def _calculate_completeness_score(self, extracted_metrics: List[ExtractedMetric]) -> float:
        """Calculate completeness score based on metric diversity."""
        if not extracted_metrics:
            return 0.0
        
        # Count unique data types
        data_types = set(metric.data_type for metric in extracted_metrics)
        
        # Expected data types for different analyses
        expected_types = {
            "ndvi": ["ndvi", "percentage", "area"],
            "lst": ["temperature", "area", "coordinates"],
            "lulc": ["percentage", "area", "population"],
            "water": ["percentage", "area", "coordinates"],
            "climate": ["temperature", "percentage", "coordinates"],
            "urban": ["percentage", "area", "population", "coordinates"]
        }
        
        # Calculate completeness based on expected types
        completeness = len(data_types) / max(len(expected_types.get("ndvi", [])), 1)
        return min(1.0, completeness)
    
    def _calculate_accuracy_score(self, extracted_metrics: List[ExtractedMetric]) -> float:
        """Calculate accuracy score based on metric confidence."""
        if not extracted_metrics:
            return 0.0
        
        avg_confidence = sum(metric.confidence for metric in extracted_metrics) / len(extracted_metrics)
        return avg_confidence

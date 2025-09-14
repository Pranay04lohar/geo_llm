"""
Enhanced Result Processor - Advanced processing with data extraction and validation.

This module provides enhanced functionality to:
- Use multiple search strategies for comprehensive data collection
- Extract and validate structured geospatial data
- Generate data-rich analysis with specific metrics
- Provide quality assessment and confidence scoring
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from .enhanced_query_generator import EnhancedQueryGenerator, AnalysisType
from .data_extractor import DataExtractor, ExtractedMetric, DataQuality
from .tavily_client import TavilyClient

logger = logging.getLogger(__name__)

class EnhancedResultProcessor:
    """Enhanced result processor with data extraction and validation."""
    
    def __init__(self):
        self.query_generator = EnhancedQueryGenerator()
        self.data_extractor = DataExtractor()
        self.tavily_client = TavilyClient()
        
        # Analysis type specific templates
        self.analysis_templates = {
            "ndvi": {
                "title": "🌿 Vegetation Health Analysis",
                "metrics": ["NDVI values", "Vegetation cover %", "Forest area km²", "Greenness index"],
                "insights": [
                    "Vegetation density and health assessment",
                    "Forest cover analysis and trends",
                    "Urban green space evaluation",
                    "Environmental sustainability indicators"
                ]
            },
            "lst": {
                "title": "🌡️ Land Surface Temperature Analysis",
                "metrics": ["Temperature °C", "Heat island effect", "Thermal patterns", "Surface heat distribution"],
                "insights": [
                    "Urban heat island analysis",
                    "Temperature variation patterns",
                    "Thermal comfort assessment",
                    "Climate impact evaluation"
                ]
            },
            "lulc": {
                "title": "🗺️ Land Use and Land Cover Analysis",
                "metrics": ["Built-up area %", "Agricultural land %", "Forest cover %", "Water bodies %"],
                "insights": [
                    "Land use change analysis",
                    "Urbanization patterns",
                    "Agricultural land assessment",
                    "Environmental land use impact"
                ]
            },
            "water": {
                "title": "💧 Water Resources Analysis",
                "metrics": ["Water body area km²", "Water quality index", "Water availability %", "Aquatic ecosystem health"],
                "insights": [
                    "Water resource assessment",
                    "Water quality analysis",
                    "Aquatic ecosystem evaluation",
                    "Water management indicators"
                ]
            },
            "climate": {
                "title": "🌤️ Climate Analysis",
                "metrics": ["Temperature °C", "Precipitation mm", "Humidity %", "Climate indicators"],
                "insights": [
                    "Climate pattern analysis",
                    "Weather trend assessment",
                    "Climate change indicators",
                    "Environmental condition evaluation"
                ]
            },
            "urban": {
                "title": "🏙️ Urban Development Analysis",
                "metrics": ["Population density", "Built-up area %", "Infrastructure coverage", "Urban growth rate"],
                "insights": [
                    "Urban development patterns",
                    "Population growth analysis",
                    "Infrastructure assessment",
                    "Urban planning indicators"
                ]
            }
        }
    
    async def generate_enhanced_analysis(
        self, 
        analysis_type: str, 
        location: str, 
        location_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate enhanced analysis using multiple search strategies and data extraction.
        
        Args:
            analysis_type: Type of analysis to perform
            location: Location to analyze
            location_data: Optional location data for context
            
        Returns:
            Dictionary with enhanced analysis and structured data
        """
        try:
            logger.info(f"Generating enhanced analysis for {analysis_type} in {location}")
            
            # Step 1: Generate enhanced queries
            analysis_enum = self.query_generator.get_analysis_type_from_string(analysis_type)
            enhanced_location = self.query_generator.enhance_location_name(location)
            queries = self.query_generator.generate_enhanced_queries(analysis_enum, enhanced_location)
            
            logger.info(f"Generated {len(queries)} enhanced queries")
            
            # Step 2: Execute multiple search strategies
            all_results = []
            search_metadata = {}
            
            for i, query_info in enumerate(queries):
                try:
                    query = query_info["query"]
                    query_type = query_info["type"]
                    
                    logger.info(f"Executing query {i+1}/{len(queries)}: {query_type} - {query[:100]}...")
                    
                    # Execute search with domain filtering if specified
                    include_domains = query_info.get("include_domains")
                    results = await self.tavily_client.search(
                        query=query,
                        max_results=2,  # Reduced from 3 to 2 for faster processing
                        include_domains=include_domains,
                        search_depth="basic"  # Changed from "advanced" to "basic" for speed
                    )
                    
                    # Add query metadata to results
                    for result in results:
                        result["query_type"] = query_type
                        result["query_priority"] = query_info.get("priority", "medium")
                        result["expected_data"] = query_info.get("expected_data", [])
                    
                    all_results.extend(results)
                    search_metadata[f"query_{i+1}"] = {
                        "type": query_type,
                        "results_count": len(results),
                        "priority": query_info.get("priority", "medium")
                    }
                    
                except Exception as e:
                    logger.error(f"Error executing query {i+1}: {e}")
                    continue
            
            logger.info(f"Collected {len(all_results)} total results from {len(queries)} queries")
            
            # Log sample search results for debugging
            if all_results:
                logger.info(f"Sample search results:")
                for i, result in enumerate(all_results[:3]):  # Show first 3 results
                    logger.info(f"  Result {i+1}: {result.get('title', 'No title')[:100]}...")
                    logger.info(f"    URL: {result.get('url', 'No URL')}")
                    logger.info(f"    Score: {result.get('score', 0)}")
                    content = result.get('content', '')
                    logger.info(f"    Content preview: {content[:300]}...")
                    
                    # Check for potential metrics in content
                    import re
                    temp_matches = re.findall(r'\d+(?:\.\d+)?\s*°?[CcFf]', content)
                    num_matches = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', content)
                    logger.info(f"    Potential temperature values: {temp_matches[:5]}")
                    logger.info(f"    Potential numbers: {num_matches[:10]}")
            
            # Step 3: Extract and validate structured data
            extracted_metrics = self.data_extractor.extract_metrics(all_results, analysis_type)
            data_quality = self.data_extractor.assess_data_quality(all_results, extracted_metrics)
            
            logger.info(f"Extracted {len(extracted_metrics)} metrics with quality score: {data_quality.overall_score:.2f}")
            
            # Log extracted metrics for debugging
            if extracted_metrics:
                logger.info(f"Sample extracted metrics:")
                for i, metric in enumerate(extracted_metrics[:5]):  # Show first 5 metrics
                    logger.info(f"  Metric {i+1}: {metric.data_type} = {metric.value} {metric.unit} (confidence: {metric.confidence:.1%})")
                    logger.info(f"    Context: {metric.context}")
                    logger.info(f"    Source: {metric.source[:100]}...")
            else:
                logger.warning("No metrics were extracted from search results")
            
            # Step 4: Generate enhanced analysis
            analysis_text = self._generate_enhanced_analysis_text(
                analysis_type, 
                location, 
                all_results, 
                extracted_metrics, 
                data_quality,
                location_data
            )
            
            # Step 5: Create structured data summary
            structured_data = self._create_structured_data_summary(
                extracted_metrics, 
                data_quality, 
                analysis_type
            )
            
            # Step 6: Generate ROI from location data
            roi = self._create_enhanced_roi(location_data, analysis_type)
            
            # Step 7: Calculate enhanced confidence
            confidence = self._calculate_enhanced_confidence(
                data_quality, 
                len(extracted_metrics), 
                len(all_results)
            )
            
            # Step 8: Create sources with quality assessment
            sources = self._create_enhanced_sources(all_results, extracted_metrics)
            
            return {
                "analysis": analysis_text,
                "roi": roi,
                "sources": sources,
                "confidence": confidence,
                "structured_data": structured_data,
                "data_quality": {
                    "credibility": data_quality.credibility_score,
                    "recency": data_quality.recency_score,
                    "completeness": data_quality.completeness_score,
                    "accuracy": data_quality.accuracy_score,
                    "overall": data_quality.overall_score
                },
                "search_metadata": search_metadata,
                "extracted_metrics_count": len(extracted_metrics),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error generating enhanced analysis: {e}")
            return {
                "analysis": f"Enhanced analysis generation failed: {str(e)}",
                "roi": None,
                "sources": [],
                "confidence": 0.0,
                "structured_data": {},
                "data_quality": {"overall": 0.0},
                "search_metadata": {},
                "extracted_metrics_count": 0,
                "success": False,
                "error": str(e)
            }
    
    def _generate_enhanced_analysis_text(
        self, 
        analysis_type: str, 
        location: str, 
        search_results: List[Dict[str, Any]], 
        extracted_metrics: List[ExtractedMetric], 
        data_quality: DataQuality,
        location_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate enhanced analysis text with structured data."""
        try:
            template = self.analysis_templates.get(analysis_type, self.analysis_templates["ndvi"])
            analysis_parts = []
            
            # Header with enhanced title
            analysis_parts.append(f"{template['title']} - {location}")
            analysis_parts.append("=" * 80)
            
            # Location information
            if location_data:
                coords = location_data.get("coordinates", {})
                area = location_data.get("area_km2")
                
                analysis_parts.append(f"📍 Location: {location}")
                if coords:
                    analysis_parts.append(f"   • Coordinates: {coords.get('lat', 0):.4f}°N, {coords.get('lng', 0):.4f}°E")
                if area:
                    analysis_parts.append(f"   • Area: {area:,.0f} km²")
                analysis_parts.append("")
            
            # Data quality assessment
            analysis_parts.append("📊 Data Quality Assessment:")
            analysis_parts.append(f"   • Overall Quality: {data_quality.overall_score:.1%}")
            analysis_parts.append(f"   • Credibility: {data_quality.credibility_score:.1%}")
            analysis_parts.append(f"   • Recency: {data_quality.recency_score:.1%}")
            analysis_parts.append(f"   • Completeness: {data_quality.completeness_score:.1%}")
            analysis_parts.append(f"   • Accuracy: {data_quality.accuracy_score:.1%}")
            analysis_parts.append("")
            
            # Extracted metrics section
            if extracted_metrics:
                analysis_parts.append("📈 Key Metrics Extracted:")
                
                # Group metrics by type
                metrics_by_type = {}
                for metric in extracted_metrics:
                    if metric.data_type not in metrics_by_type:
                        metrics_by_type[metric.data_type] = []
                    metrics_by_type[metric.data_type].append(metric)
                
                # Display top metrics for each type
                for data_type, metrics in list(metrics_by_type.items())[:5]:  # Top 5 types
                    if metrics:
                        # Sort by confidence and take top 3
                        top_metrics = sorted(metrics, key=lambda x: x.confidence, reverse=True)[:3]
                        
                        analysis_parts.append(f"   {data_type.upper()}:")
                        for metric in top_metrics:
                            if metric.data_type.endswith("_context"):
                                # For context metrics, show the context instead of value
                                analysis_parts.append(f"      • {metric.context} (confidence: {metric.confidence:.1%})")
                            else:
                                # For value metrics, show the actual value
                                analysis_parts.append(f"      • {metric.value:.2f} {metric.unit} (confidence: {metric.confidence:.1%})")
                        analysis_parts.append("")
            else:
                analysis_parts.append("⚠️ No specific metrics could be extracted from available data")
                analysis_parts.append("")
            
            # Data sources summary
            analysis_parts.append("📚 Data Sources:")
            
            # Categorize results
            reports = [r for r in search_results if r.get("query_type") == "source_specific" and "gov" in r.get("url", "")]
            studies = [r for r in search_results if r.get("query_type") == "source_specific" and any(domain in r.get("url", "") for domain in [".edu", "research"])]
            news = [r for r in search_results if r.get("query_type") == "news"]
            
            analysis_parts.append(f"   • Official Reports: {len(reports)}")
            analysis_parts.append(f"   • Research Studies: {len(studies)}")
            analysis_parts.append(f"   • News Articles: {len(news)}")
            analysis_parts.append(f"   • Total Sources: {len(search_results)}")
            analysis_parts.append("")
            
            # Key findings with actual data
            if extracted_metrics:
                analysis_parts.append("🔍 Key Findings with Data:")
                
                # Find most relevant metrics for this analysis type
                relevant_metrics = [m for m in extracted_metrics if m.data_type in template["metrics"]]
                if not relevant_metrics:
                    relevant_metrics = extracted_metrics[:5]  # Fallback to top 5
                
                for i, metric in enumerate(relevant_metrics[:5], 1):
                    analysis_parts.append(f"   {i}. {metric.context}")
                    analysis_parts.append(f"      Source: {metric.source[:100]}...")
                    analysis_parts.append(f"      Confidence: {metric.confidence:.1%}")
                    analysis_parts.append("")
            else:
                analysis_parts.append("🔍 Key Findings:")
                # Fallback to top search results
                top_results = sorted(search_results, key=lambda x: x.get("score", 0), reverse=True)[:3]
                for i, result in enumerate(top_results, 1):
                    title = result.get("title", "Unknown")
                    content = result.get("content", "")[:200] + "..." if len(result.get("content", "")) > 200 else result.get("content", "")
                    analysis_parts.append(f"   {i}. {title}")
                    analysis_parts.append(f"      {content}")
                    analysis_parts.append("")
            
            # Analysis-specific insights
            analysis_parts.append(f"💡 {analysis_type.upper()} Analysis Insights:")
            for insight in template["insights"]:
                analysis_parts.append(f"   • {insight}")
            analysis_parts.append("")
            
            # Data limitations and recommendations
            analysis_parts.append("⚠️ Data Limitations:")
            if data_quality.overall_score < 0.6:
                analysis_parts.append("   • Limited data quality - results should be interpreted with caution")
            if data_quality.recency_score < 0.5:
                analysis_parts.append("   • Data may not be current - consider recent updates")
            if len(extracted_metrics) < 5:
                analysis_parts.append("   • Limited quantitative data available")
            analysis_parts.append("   • Analysis based on web search results, not real-time satellite data")
            analysis_parts.append("")
            
            # Recommendations for better data
            analysis_parts.append("📋 Recommendations for Enhanced Analysis:")
            analysis_parts.append("   • Access to real-time satellite data would improve accuracy")
            analysis_parts.append("   • Government databases provide most reliable metrics")
            analysis_parts.append("   • Academic research offers detailed scientific analysis")
            analysis_parts.append("   • Multiple data sources ensure comprehensive coverage")
            
            return "\n".join(analysis_parts)
            
        except Exception as e:
            logger.error(f"Error generating enhanced analysis text: {e}")
            return f"Enhanced analysis generation failed: {str(e)}"
    
    def _create_structured_data_summary(
        self, 
        extracted_metrics: List[ExtractedMetric], 
        data_quality: DataQuality, 
        analysis_type: str
    ) -> Dict[str, Any]:
        """Create structured data summary for the analysis."""
        try:
            # Group metrics by type
            metrics_by_type = {}
            for metric in extracted_metrics:
                if metric.data_type not in metrics_by_type:
                    metrics_by_type[metric.data_type] = []
                metrics_by_type[metric.data_type].append(metric)
            
            # Calculate statistics for each metric type
            structured_data = {
                "analysis_type": analysis_type,
                "total_metrics": len(extracted_metrics),
                "metric_types": len(metrics_by_type),
                "data_quality": {
                    "overall": data_quality.overall_score,
                    "credibility": data_quality.credibility_score,
                    "recency": data_quality.recency_score,
                    "completeness": data_quality.completeness_score,
                    "accuracy": data_quality.accuracy_score
                },
                "metrics_summary": {}
            }
            
            for data_type, metrics in metrics_by_type.items():
                if metrics:
                    values = [m.value for m in metrics if isinstance(m.value, (int, float))]
                    if values:
                        structured_data["metrics_summary"][data_type] = {
                            "count": len(values),
                            "min": min(values),
                            "max": max(values),
                            "avg": sum(values) / len(values),
                            "unit": metrics[0].unit,
                            "high_confidence_count": len([m for m in metrics if m.confidence > 0.7])
                        }
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Error creating structured data summary: {e}")
            return {"error": str(e)}
    
    def _create_enhanced_roi(
        self, 
        location_data: Optional[Dict[str, Any]], 
        analysis_type: str
    ) -> Optional[Dict[str, Any]]:
        """Create enhanced ROI with analysis-specific metadata."""
        if not location_data:
            return None
        
        try:
            coordinates = location_data.get("coordinates", {})
            boundaries = location_data.get("boundaries")
            area_km2 = location_data.get("area_km2")
            location_name = location_data.get("location_name", "Unknown")
            
            if not coordinates:
                return None
            
            roi_feature = {
                "type": "Feature",
                "properties": {
                    "name": f"Enhanced {analysis_type.upper()} Analysis - {location_name}",
                    "area_km2": area_km2,
                    "analysis_type": analysis_type,
                    "data_source": "enhanced_web_search",
                    "location_name": location_name,
                    "coordinates": coordinates,
                    "analysis_timestamp": datetime.now().isoformat(),
                    "data_quality": "web_search_enhanced"
                },
                "geometry": boundaries or {
                    "type": "Point",
                    "coordinates": [coordinates.get("lng", 0), coordinates.get("lat", 0)]
                }
            }
            
            return roi_feature
            
        except Exception as e:
            logger.error(f"Error creating enhanced ROI: {e}")
            return None
    
    def _calculate_enhanced_confidence(
        self, 
        data_quality: DataQuality, 
        metrics_count: int, 
        results_count: int
    ) -> float:
        """Calculate enhanced confidence score."""
        try:
            # Base confidence from data quality
            base_confidence = data_quality.overall_score
            
            # Boost for metric richness
            metrics_boost = min(0.2, metrics_count * 0.02)
            
            # Boost for result diversity
            results_boost = min(0.1, results_count * 0.01)
            
            # Boost for high credibility
            credibility_boost = 0.1 if data_quality.credibility_score > 0.7 else 0.0
            
            confidence = min(1.0, base_confidence + metrics_boost + results_boost + credibility_boost)
            return round(confidence, 2)
            
        except Exception as e:
            logger.error(f"Error calculating enhanced confidence: {e}")
            return 0.5
    
    def _create_enhanced_sources(
        self, 
        search_results: List[Dict[str, Any]], 
        extracted_metrics: List[ExtractedMetric]
    ) -> List[Dict[str, Any]]:
        """Create enhanced sources with quality assessment."""
        try:
            sources = []
            
            for result in search_results:
                # Calculate source quality
                url = result.get("url", "")
                quality_score = 0.5  # Base score
                
                # Boost for credible domains
                if any(domain in url.lower() for domain in [".gov", ".edu", "research"]):
                    quality_score += 0.3
                
                # Boost for high Tavily score
                tavily_score = result.get("score", 0)
                quality_score += tavily_score * 0.2
                
                # Check if this source contributed metrics
                source_metrics = [m for m in extracted_metrics if m.source.startswith(result.get("title", ""))]
                if source_metrics:
                    quality_score += 0.2
                
                source = {
                    "title": result.get("title", ""),
                    "url": url,
                    "score": tavily_score,
                    "quality_score": min(1.0, quality_score),
                    "query_type": result.get("query_type", "unknown"),
                    "metrics_contributed": len(source_metrics),
                    "published_date": result.get("published_date")
                }
                sources.append(source)
            
            # Sort by quality score
            sources.sort(key=lambda x: x["quality_score"], reverse=True)
            
            return sources
            
        except Exception as e:
            logger.error(f"Error creating enhanced sources: {e}")
            return []

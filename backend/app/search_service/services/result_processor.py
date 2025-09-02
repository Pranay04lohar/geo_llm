"""
Result Processor - Processes and structures search results.

This module provides functionality to:
- Process and categorize search results
- Extract environmental context
- Generate complete analysis from web data
- Structure data for LLM consumption
"""

import logging
import re
from typing import Dict, List, Any, Optional
import json

logger = logging.getLogger(__name__)

class ResultProcessor:
    """Processes search results and generates structured analysis."""
    
    def __init__(self):
        # Keywords for categorizing results
        self.report_keywords = [
            "report", "study", "analysis", "assessment", "evaluation",
            "government", "official", "ministry", "department", "agency"
        ]
        
        self.study_keywords = [
            "research", "study", "paper", "journal", "academic",
            "university", "institute", "scientific", "peer-reviewed"
        ]
        
        self.news_keywords = [
            "news", "article", "update", "recent", "latest",
            "today", "yesterday", "this week", "breaking"
        ]
        
        # Statistical patterns
        self.stat_patterns = [
            r'(\d+(?:,\d+)*\.?\d*)\s*(?:%|percent|percentage)',
            r'(\d+(?:,\d+)*\.?\d*)\s*(?:km²|km2|square kilometers?)',
            r'(\d+(?:,\d+)*\.?\d*)\s*(?:million|billion|thousand)',
            r'(\d+(?:,\d+)*\.?\d*)\s*(?:people|inhabitants?|residents?)',
        ]
    
    def process_environmental_results(
        self, 
        search_results: List[Dict[str, Any]], 
        analysis_type: str
    ) -> Dict[str, Any]:
        """
        Process search results and categorize into reports, studies, news.
        
        Args:
            search_results: List of search results from Tavily
            analysis_type: Type of analysis (ndvi, lulc, etc.)
            
        Returns:
            Dictionary with categorized results and summary
        """
        try:
            logger.info(f"Processing {len(search_results)} environmental results for {analysis_type}")
            
            # Categorize results
            reports = []
            studies = []
            news = []
            
            for result in search_results:
                category = self._categorize_result(result)
                
                if category == "report":
                    reports.append(result)
                elif category == "study":
                    studies.append(result)
                elif category == "news":
                    news.append(result)
                else:
                    # Default to reports for environmental data
                    reports.append(result)
            
            # Extract statistics
            statistics = self._extract_statistics(search_results)
            
            # Generate context summary
            context_summary = self._generate_context_summary(
                reports, studies, news, analysis_type
            )
            
            return {
                "reports": reports,
                "studies": studies,
                "news": news,
                "statistics": statistics,
                "context_summary": context_summary,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error processing environmental results: {e}")
            return {
                "reports": [],
                "studies": [],
                "news": [],
                "statistics": {},
                "context_summary": "Error processing results",
                "success": False,
                "error": str(e)
            }
    
    def generate_complete_analysis(
        self, 
        search_results: List[Dict[str, Any]], 
        analysis_type: str,
        location_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate complete analysis from search results.
        
        Args:
            search_results: List of search results
            analysis_type: Type of analysis
            location_data: Optional location data
            
        Returns:
            Dictionary with complete analysis
        """
        try:
            logger.info(f"Generating complete analysis for {analysis_type}")
            
            # Process and categorize results
            processed_results = self.process_environmental_results(search_results, analysis_type)
            
            # Generate comprehensive analysis text
            analysis_text = self._generate_analysis_text(
                processed_results, 
                analysis_type, 
                location_data
            )
            
            # Create ROI from location data
            roi = None
            if location_data:
                roi = self._create_roi_from_location_data(location_data)
            
            # Extract sources
            sources = []
            for result in search_results:
                sources.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "score": result.get("score", 0.0)
                })
            
            # Calculate confidence based on result quality
            confidence = self._calculate_confidence(search_results, processed_results)
            
            return {
                "analysis": analysis_text,
                "roi": roi,
                "sources": sources,
                "confidence": confidence,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error generating complete analysis: {e}")
            return {
                "analysis": f"Analysis generation failed: {str(e)}",
                "roi": None,
                "sources": [],
                "confidence": 0.0,
                "success": False,
                "error": str(e)
            }
    
    def _categorize_result(self, result: Dict[str, Any]) -> str:
        """Categorize a search result based on content and URL."""
        title = result.get("title", "").lower()
        content = result.get("content", "").lower()
        url = result.get("url", "").lower()
        
        # Check for news indicators
        if any(keyword in title or keyword in content for keyword in self.news_keywords):
            return "news"
        
        # Check for study indicators
        if any(keyword in title or keyword in content for keyword in self.study_keywords):
            return "study"
        
        # Check for report indicators
        if any(keyword in title or keyword in content for keyword in self.report_keywords):
            return "report"
        
        # Check URL patterns
        if any(domain in url for domain in [".edu", "research", "academic"]):
            return "study"
        elif any(domain in url for domain in [".gov", "government", "official"]):
            return "report"
        elif any(domain in url for domain in ["news", "article", "blog"]):
            return "news"
        
        # Default to report for environmental data
        return "report"
    
    def _extract_statistics(self, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract statistical data from search results."""
        statistics = {}
        
        # Combine all content
        combined_content = ""
        for result in search_results:
            combined_content += f"\n{result.get('content', '')}"
        
        # Extract various statistics
        for pattern in self.stat_patterns:
            matches = re.findall(pattern, combined_content, re.IGNORECASE)
            if matches:
                # Store the most common values
                values = [float(match.replace(',', '')) for match in matches]
                if values:
                    statistics[f"pattern_{len(statistics)}"] = {
                        "values": values,
                        "pattern": pattern,
                        "count": len(values)
                    }
        
        return statistics
    
    def _generate_context_summary(
        self, 
        reports: List[Dict[str, Any]], 
        studies: List[Dict[str, Any]], 
        news: List[Dict[str, Any]], 
        analysis_type: str
    ) -> str:
        """Generate a context summary from categorized results."""
        try:
            summary_parts = []
            
            # Add report summary
            if reports:
                summary_parts.append(f"Found {len(reports)} official reports and documents")
                if reports:
                    top_report = max(reports, key=lambda x: x.get("score", 0))
                    summary_parts.append(f"Key report: {top_report.get('title', 'Unknown')}")
            
            # Add study summary
            if studies:
                summary_parts.append(f"Found {len(studies)} research studies and academic papers")
                if studies:
                    top_study = max(studies, key=lambda x: x.get("score", 0))
                    summary_parts.append(f"Key study: {top_study.get('title', 'Unknown')}")
            
            # Add news summary
            if news:
                summary_parts.append(f"Found {len(news)} recent news articles and updates")
                if news:
                    top_news = max(news, key=lambda x: x.get("score", 0))
                    summary_parts.append(f"Latest news: {top_news.get('title', 'Unknown')}")
            
            # Add analysis type context
            if analysis_type == "ndvi":
                summary_parts.append("Focus: Vegetation health and green cover analysis")
            elif analysis_type == "lulc":
                summary_parts.append("Focus: Land use and land cover classification")
            else:
                summary_parts.append(f"Focus: {analysis_type} environmental analysis")
            
            return ". ".join(summary_parts) + "."
            
        except Exception as e:
            logger.error(f"Error generating context summary: {e}")
            return "Context summary generation failed"
    
    def _generate_analysis_text(
        self, 
        processed_results: Dict[str, Any], 
        analysis_type: str,
        location_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate comprehensive analysis text."""
        try:
            analysis_parts = []
            
            # Header
            location_name = location_data.get("location_name", "Unknown") if location_data else "Unknown"
            analysis_parts.append(f"🌍 {analysis_type.upper()} Analysis - {location_name}")
            analysis_parts.append("=" * 60)
            
            # Location information
            if location_data:
                coords = location_data.get("coordinates", {})
                area = location_data.get("area_km2")
                population = location_data.get("population")
                
                analysis_parts.append(f"📍 Location: {location_name}")
                if coords:
                    analysis_parts.append(f"   • Coordinates: {coords.get('lat', 0):.4f}°N, {coords.get('lng', 0):.4f}°E")
                if area:
                    analysis_parts.append(f"   • Area: {area:,.0f} km²")
                if population:
                    analysis_parts.append(f"   • Population: {population:,}")
                analysis_parts.append("")
            
            # Data sources summary
            reports = processed_results.get("reports", [])
            studies = processed_results.get("studies", [])
            news = processed_results.get("news", [])
            
            analysis_parts.append("📊 Data Sources:")
            analysis_parts.append(f"   • Official reports: {len(reports)}")
            analysis_parts.append(f"   • Research studies: {len(studies)}")
            analysis_parts.append(f"   • News articles: {len(news)}")
            analysis_parts.append("")
            
            # Key findings from top results
            all_results = reports + studies + news
            if all_results:
                # Sort by score and take top 3
                top_results = sorted(all_results, key=lambda x: x.get("score", 0), reverse=True)[:3]
                
                analysis_parts.append("🔍 Key Findings:")
                for i, result in enumerate(top_results, 1):
                    title = result.get("title", "Unknown")
                    content = result.get("content", "")[:200] + "..." if len(result.get("content", "")) > 200 else result.get("content", "")
                    analysis_parts.append(f"   {i}. {title}")
                    analysis_parts.append(f"      {content}")
                    analysis_parts.append("")
            
            # Statistics summary
            statistics = processed_results.get("statistics", {})
            if statistics:
                analysis_parts.append("📈 Key Statistics:")
                for key, stat_data in list(statistics.items())[:5]:  # Top 5 statistics
                    values = stat_data.get("values", [])
                    if values:
                        avg_value = sum(values) / len(values)
                        analysis_parts.append(f"   • Average: {avg_value:,.1f}")
                analysis_parts.append("")
            
            # Analysis type specific insights
            if analysis_type == "ndvi":
                analysis_parts.append("🌿 Vegetation Analysis Insights:")
                analysis_parts.append("   • Based on web data and reports")
                analysis_parts.append("   • Includes government forest cover data")
                analysis_parts.append("   • References recent environmental studies")
            elif analysis_type == "lulc":
                analysis_parts.append("🗺️ Land Use Analysis Insights:")
                analysis_parts.append("   • Based on official land use reports")
                analysis_parts.append("   • Includes urban development data")
                analysis_parts.append("   • References planning documents")
            
            analysis_parts.append("")
            analysis_parts.append("💡 Note: This analysis is based on web search results and may not reflect real-time satellite data.")
            
            return "\n".join(analysis_parts)
            
        except Exception as e:
            logger.error(f"Error generating analysis text: {e}")
            return f"Analysis generation failed: {str(e)}"
    
    def _create_roi_from_location_data(self, location_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create ROI feature from location data."""
        try:
            coordinates = location_data.get("coordinates", {})
            boundaries = location_data.get("boundaries")
            area_km2 = location_data.get("area_km2")
            location_name = location_data.get("location_name", "Unknown")
            
            if not coordinates:
                return None
            
            # Create ROI feature
            roi_feature = {
                "type": "Feature",
                "properties": {
                    "name": f"Search Analysis ROI - {location_name}",
                    "area_km2": area_km2,
                    "analysis_type": "web_search_analysis",
                    "data_source": "web_search",
                    "location_name": location_name,
                    "coordinates": coordinates
                },
                "geometry": boundaries or {
                    "type": "Point",
                    "coordinates": [coordinates.get("lng", 0), coordinates.get("lat", 0)]
                }
            }
            
            return roi_feature
            
        except Exception as e:
            logger.error(f"Error creating ROI from location data: {e}")
            return None
    
    def _calculate_confidence(
        self, 
        search_results: List[Dict[str, Any]], 
        processed_results: Dict[str, Any]
    ) -> float:
        """Calculate confidence score based on result quality."""
        try:
            if not search_results:
                return 0.0
            
            # Base confidence from average score
            avg_score = sum(result.get("score", 0) for result in search_results) / len(search_results)
            
            # Boost confidence based on result diversity
            reports = len(processed_results.get("reports", []))
            studies = len(processed_results.get("studies", []))
            news = len(processed_results.get("news", []))
            
            diversity_boost = min(0.2, (reports + studies + news) * 0.05)
            
            # Boost confidence for official sources
            official_boost = 0.1 if reports > 0 else 0.0
            
            confidence = min(1.0, avg_score + diversity_boost + official_boost)
            return round(confidence, 2)
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5  # Default moderate confidence

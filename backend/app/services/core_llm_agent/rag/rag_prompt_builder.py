"""
RAG Prompt Builder for Context Formatting.

This module handles the construction of prompts that combine user queries
with retrieved document context for grounded LLM responses.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .rag_client import RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """Template for RAG prompts."""
    system_prompt: str
    context_format: str
    user_format: str
    max_context_length: int = 4000
    
    
class RAGPromptBuilder:
    """Builder for constructing RAG prompts with retrieved context."""
    
    def __init__(self):
        """Initialize the prompt builder with default templates."""
        self.templates = {
            "default": PromptTemplate(
                system_prompt=(
                    "You are a knowledgeable assistant specializing in geospatial and environmental analysis. "
                    "Use the provided context to answer questions accurately and comprehensively. "
                    "If the context doesn't contain enough information to answer the question fully, "
                    "clearly state what information is missing. Always cite your sources when referencing "
                    "specific information from the context."
                ),
                context_format=(
                    "## Context Information\n\n"
                    "{context_sections}\n\n"
                    "## Instructions\n"
                    "Based on the above context, please answer the following question. "
                    "Be specific and reference the relevant sections when applicable."
                ),
                user_format="**Question:** {query}",
                max_context_length=4000
            ),
            "policy": PromptTemplate(
                system_prompt=(
                    "You are an expert in environmental policy and regulations. "
                    "Use the provided policy documents and regulations to answer questions "
                    "with accurate, well-sourced information. Always cite specific policy "
                    "sections or document names when referencing information."
                ),
                context_format=(
                    "## Policy Documents and Regulations\n\n"
                    "{context_sections}\n\n"
                    "## Instructions\n"
                    "Based on the policy documents above, provide a comprehensive answer "
                    "that includes relevant citations and policy references."
                ),
                user_format="**Policy Question:** {query}",
                max_context_length=5000
            ),
            "disaster": PromptTemplate(
                system_prompt=(
                    "You are a disaster management and emergency response expert. "
                    "Use the provided disaster reports and documentation to answer questions "
                    "about disaster preparedness, response, and recovery. Focus on actionable "
                    "insights and evidence-based recommendations."
                ),
                context_format=(
                    "## Disaster Reports and Documentation\n\n"
                    "{context_sections}\n\n"
                    "## Instructions\n"
                    "Based on the disaster documentation above, provide detailed insights "
                    "that could help with disaster preparedness or response planning."
                ),
                user_format="**Disaster Management Question:** {query}",
                max_context_length=4500
            ),
            "technical": PromptTemplate(
                system_prompt=(
                    "You are a technical expert in geospatial analysis and remote sensing. "
                    "Use the provided technical documentation to answer questions with "
                    "precise, scientifically accurate information. Include technical details "
                    "and methodology when relevant."
                ),
                context_format=(
                    "## Technical Documentation\n\n"
                    "{context_sections}\n\n"
                    "## Instructions\n"
                    "Provide a technical response based on the documentation above. "
                    "Include relevant methodologies, data sources, and technical specifications."
                ),
                user_format="**Technical Question:** {query}",
                max_context_length=4000
            )
        }
    
    def select_template(self, query: str, context_chunks: List[RetrievedChunk]) -> str:
        """Select the most appropriate template based on query and context.
        
        Args:
            query: User query
            context_chunks: Retrieved document chunks
            
        Returns:
            Template name to use
        """
        query_lower = query.lower()
        
        # Check for policy-related keywords
        policy_keywords = ["policy", "regulation", "law", "compliance", "governance", "legal"]
        if any(keyword in query_lower for keyword in policy_keywords):
            return "policy"
        
        # Check for disaster-related keywords
        disaster_keywords = ["disaster", "emergency", "flood", "earthquake", "hurricane", "wildfire", "crisis"]
        if any(keyword in query_lower for keyword in disaster_keywords):
            return "disaster"
        
        # Check for technical keywords
        technical_keywords = ["algorithm", "methodology", "analysis", "model", "satellite", "remote sensing"]
        if any(keyword in query_lower for keyword in technical_keywords):
            return "technical"
        
        # Check context for clues
        if context_chunks:
            combined_context = " ".join([chunk.content for chunk in context_chunks[:3]]).lower()
            
            if any(keyword in combined_context for keyword in policy_keywords):
                return "policy"
            elif any(keyword in combined_context for keyword in disaster_keywords):
                return "disaster"
            elif any(keyword in combined_context for keyword in technical_keywords):
                return "technical"
        
        return "default"
    
    def format_context_sections(self, chunks: List[RetrievedChunk], max_length: int) -> str:
        """Format retrieved chunks into context sections.
        
        Args:
            chunks: Retrieved document chunks
            max_length: Maximum total length of context
            
        Returns:
            Formatted context string
        """
        if not chunks:
            return "No relevant context found."
        
        sections = []
        current_length = 0
        
        for i, chunk in enumerate(chunks, 1):
            # Format chunk with metadata if available
            source_info = ""
            if chunk.metadata:
                source_name = chunk.metadata.get("source", chunk.metadata.get("filename", "Unknown"))
                page_info = ""
                if "page" in chunk.metadata:
                    page_info = f" (Page {chunk.metadata['page']})"
                elif "chunk_id" in chunk.metadata:
                    page_info = f" (Section {chunk.metadata['chunk_id']})"
                
                source_info = f"**Source:** {source_name}{page_info}\n"
                if "year" in chunk.metadata:
                    source_info += f"**Year:** {chunk.metadata['year']}\n"
            
            # Format the section
            section = f"### Context {i}\n{source_info}**Relevance Score:** {chunk.score:.3f}\n\n{chunk.content.strip()}\n"
            
            # Check if adding this section would exceed the limit
            if current_length + len(section) > max_length and sections:
                break
            
            sections.append(section)
            current_length += len(section)
        
        if not sections:
            # If even the first chunk is too long, truncate it
            first_chunk = chunks[0]
            content = first_chunk.content[:max_length - 200]  # Leave room for metadata
            source_info = ""
            if first_chunk.metadata:
                source_name = first_chunk.metadata.get("source", "Unknown")
                source_info = f"**Source:** {source_name}\n"
            
            sections.append(f"### Context 1\n{source_info}**Relevance Score:** {first_chunk.score:.3f}\n\n{content}...\n")
        
        return "\n".join(sections)
    
    def build_prompt(
        self, 
        query: str, 
        context_chunks: List[RetrievedChunk],
        template_name: Optional[str] = None,
        include_location_context: bool = True,
        location_names: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """Build a complete RAG prompt with system message, context, and user query.
        
        Args:
            query: User query
            context_chunks: Retrieved document chunks
            template_name: Specific template to use (auto-select if None)
            include_location_context: Whether to include location information
            location_names: List of location names from query parsing
            
        Returns:
            Dictionary with 'system', 'context', and 'user' components
        """
        # Select template
        if template_name is None:
            template_name = self.select_template(query, context_chunks)
        
        if template_name not in self.templates:
            template_name = "default"
            logger.warning(f"Unknown template requested, using default")
        
        template = self.templates[template_name]
        
        # Format context sections
        context_sections = self.format_context_sections(context_chunks, template.max_context_length)
        
        # Add location context if requested
        if include_location_context and location_names:
            location_context = f"\n**Geographic Context:** This query relates to: {', '.join(location_names)}\n"
            context_sections = location_context + context_sections
        
        # Build the complete prompt
        system_message = template.system_prompt
        context_message = template.context_format.format(context_sections=context_sections)
        user_message = template.user_format.format(query=query)
        
        return {
            "system": system_message,
            "context": context_message,
            "user": user_message,
            "template_used": template_name,
            "chunks_used": len(context_chunks)
        }
    
    def build_simple_prompt(self, query: str, context_chunks: List[RetrievedChunk]) -> str:
        """Build a simple combined prompt for models that don't support system messages.
        
        Args:
            query: User query
            context_chunks: Retrieved document chunks
            
        Returns:
            Single combined prompt string
        """
        prompt_parts = self.build_prompt(query, context_chunks)
        
        combined = f"{prompt_parts['system']}\n\n{prompt_parts['context']}\n\n{prompt_parts['user']}"
        return combined
    
    def add_custom_template(self, name: str, template: PromptTemplate):
        """Add a custom prompt template.
        
        Args:
            name: Template name
            template: PromptTemplate instance
        """
        self.templates[name] = template
        logger.info(f"Added custom template: {name}")
    
    def get_available_templates(self) -> List[str]:
        """Get list of available template names.
        
        Returns:
            List of template names
        """
        return list(self.templates.keys())


# Factory function
def create_prompt_builder() -> RAGPromptBuilder:
    """Create a RAG prompt builder instance.
    
    Returns:
        Configured RAG prompt builder
    """
    return RAGPromptBuilder()


# Example usage and testing
def test_prompt_builder():
    """Test the prompt builder functionality."""
    builder = create_prompt_builder()
    
    # Create sample chunks
    chunks = [
        RetrievedChunk(
            content="Climate change is causing increased temperatures globally. The IPCC reports show significant warming trends.",
            metadata={"source": "IPCC Report 2023", "page": 15, "year": 2023},
            score=0.95
        ),
        RetrievedChunk(
            content="Adaptation strategies include building resilient infrastructure and implementing early warning systems.",
            metadata={"source": "Adaptation Guidelines", "page": 8},
            score=0.87
        )
    ]
    
    # Test prompt building
    query = "What are the impacts of climate change and how can we adapt?"
    prompt = builder.build_prompt(query, chunks, location_names=["Global"])
    
    print("=== RAG Prompt Builder Test ===")
    print(f"Template used: {prompt['template_used']}")
    print(f"Chunks used: {prompt['chunks_used']}")
    print("\nSystem Message:")
    print(prompt['system'])
    print("\nContext Message:")
    print(prompt['context'][:500] + "...")
    print("\nUser Message:")
    print(prompt['user'])


if __name__ == "__main__":
    test_prompt_builder()
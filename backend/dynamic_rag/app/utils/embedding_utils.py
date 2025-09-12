"""
Embedding utilities for Dynamic RAG System.

What: Centralized, GPU-accelerated embedding generation using
      SentenceTransformers (`all-MiniLM-L6-v2`).

Why:  Efficiently embed many chunks/queries with batching and mixed precision
      on CUDA/MPS when available, with CPU fallback.

How:  Lazily initializes a singleton `EmbeddingGenerator`, detects device,
      enables FP16 on CUDA, normalizes vectors for cosine similarity, and
      provides async helpers for docs/queries.
"""

import logging
from typing import List, Tuple, Optional
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel

from app.config import EMBEDDING_CONFIG
from app.utils.data_ingestion_pipeline import Document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """GPU-accelerated embedding generation using SentenceTransformers."""
    
    def __init__(self):
        self.model_name = EMBEDDING_CONFIG["model_name"]
        self.use_gpu = EMBEDDING_CONFIG["use_gpu"]
        self.batch_size = EMBEDDING_CONFIG["batch_size"]
        self.dimension = EMBEDDING_CONFIG["dimension"]
        
        # Initialize model and device
        self.device = self._get_device()
        self.model = self._load_model()
        
        logger.info(f"EmbeddingGenerator initialized with model: {self.model_name}")
        logger.info(f"Device: {self.device}")
        logger.info(f"Embedding dimension: {self.dimension}")
    
    def _get_device(self) -> str:
        """Determine the best available device for embedding generation."""
        if self.use_gpu and torch.cuda.is_available():
            device = "cuda"
            logger.info(f"🚀 GPU available: {torch.cuda.get_device_name(0)}")
            logger.info(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        elif self.use_gpu and hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            device = "mps"  # Apple Silicon
            logger.info("🍎 Using Apple Silicon GPU (MPS)")
        else:
            device = "cpu"
            logger.info("💻 Using CPU for embedding generation")
        
        return device
    
    def _load_model(self) -> SentenceTransformer:
        """Load the SentenceTransformer model on the specified device."""
        try:
            model = SentenceTransformer(self.model_name)
            model = model.to(self.device)
            
            # Optimize for inference
            model.eval()
            
            # Enable mixed precision if using GPU
            if self.device == "cuda":
                model.half()  # Use FP16 for faster inference
                logger.info("🔧 Enabled FP16 precision for faster GPU inference")
            
            return model
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            raise
    
    async def embed_documents(
        self, 
        documents: List[Document]
    ) -> List[Tuple[str, dict, np.ndarray]]:
        """
        Generate embeddings for a list of documents.
        
        Args:
            documents: List of Document objects with content and metadata
            
        Returns:
            List of tuples (content, metadata, embedding_vector)
        """
        if not documents:
            return []
        
        logger.info(f"Generating embeddings for {len(documents)} documents...")
        
        # Extract content for batch processing
        contents = [doc.content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        # Generate embeddings in batches
        embeddings = await self._generate_embeddings_batch(contents)
        
        # Combine results
        results = []
        for content, metadata, embedding in zip(contents, metadatas, embeddings):
            results.append((content, metadata, embedding))
        
        logger.info(f"✅ Generated {len(results)} embeddings successfully")
        return results
    
    async def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a single query.
        
        Args:
            query: Query string to embed
            
        Returns:
            Embedding vector as numpy array
        """
        logger.info(f"Generating embedding for query: '{query[:50]}...'")
        
        embeddings = await self._generate_embeddings_batch([query])
        return embeddings[0]
    
    async def _generate_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors as numpy arrays
        """
        if not texts:
            return []
        
        # Process in batches to manage memory
        all_embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            
            try:
                # Generate embeddings for this batch
                with torch.no_grad():  # Disable gradient computation for inference
                    batch_embeddings = self.model.encode(
                        batch_texts,
                        convert_to_tensor=True,
                        show_progress_bar=False,
                        batch_size=len(batch_texts)
                    )
                    
                    # Convert to numpy and normalize for cosine similarity
                    batch_embeddings = batch_embeddings.cpu().numpy()
                    batch_embeddings = self._normalize_embeddings(batch_embeddings)
                    
                    all_embeddings.extend(batch_embeddings)
                    
            except Exception as e:
                logger.error(f"Error generating embeddings for batch {i//self.batch_size}: {str(e)}")
                # Add zero embeddings for failed batch
                failed_embeddings = np.zeros((len(batch_texts), self.dimension))
                all_embeddings.extend(failed_embeddings)
        
        return all_embeddings
    
    def _normalize_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Normalize embeddings for cosine similarity computation.
        
        Args:
            embeddings: Raw embedding vectors
            
        Returns:
            Normalized embedding vectors
        """
        # L2 normalization
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
        normalized = embeddings / norms
        
        return normalized.astype(np.float32)
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model."""
        return self.dimension
    
    def get_model_info(self) -> dict:
        """Get information about the current embedding model."""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "dimension": self.dimension,
            "batch_size": self.batch_size,
            "gpu_available": torch.cuda.is_available() if self.use_gpu else False,
            "mixed_precision": self.device == "cuda"
        }


# Global embedding generator instance
_embedding_generator: Optional[EmbeddingGenerator] = None


def get_embedding_generator() -> EmbeddingGenerator:
    """Get or create the global embedding generator instance."""
    global _embedding_generator
    
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    
    return _embedding_generator


async def embed_documents(documents: List[Document]) -> List[Tuple[str, dict, np.ndarray]]:
    """
    Convenience function to generate embeddings for documents.
    
    Args:
        documents: List of Document objects
        
    Returns:
        List of tuples (content, metadata, embedding_vector)
    """
    generator = get_embedding_generator()
    return await generator.embed_documents(documents)


async def embed_query(query: str) -> np.ndarray:
    """
    Convenience function to generate embedding for a query.
    
    Args:
        query: Query string
        
    Returns:
        Embedding vector as numpy array
    """
    generator = get_embedding_generator()
    return await generator.embed_query(query)


def get_embedding_dimension() -> int:
    """Get the dimension of embeddings."""
    generator = get_embedding_generator()
    return generator.get_embedding_dimension()


def get_model_info() -> dict:
    """Get embedding model information."""
    generator = get_embedding_generator()
    return generator.get_model_info()

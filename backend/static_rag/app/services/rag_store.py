"""
RAG Store Service

This module handles database operations for the RAG pipeline, including document storage
and retrieval using PostgreSQL with pgvector extension. It provides functions for
storing document embeddings and performing vector similarity search.

Features:
- Async PostgreSQL connection with connection pooling
- SSL support for secure database connections (Neon, etc.)
- Vector similarity search using pgvector operators
- Year-based filtering for disaster data analysis
- Automatic schema creation and indexing
- Batch document insertion for efficiency

Database Schema:
- documents table with id, content, metadata, embedding (VECTOR(384)), year
- pgvector extension for vector operations
- Index on year column for fast filtering

Author: RAG Pipeline Team
Version: 0.1.0
"""

from typing import Any, Dict, List, Optional

import json

import asyncpg
import os
import ssl

from ..utils.data_ingestion_pipeline import Document
from ..utils.embedding_utils import embed_documents, embed_query
from ..config import get_db_config


async def _get_pool() -> asyncpg.Pool:
    cfg = get_db_config()
    ssl_ctx: Optional[ssl.SSLContext] = None
    # Enable SSL if PGSSLMODE is set (e.g., Neon requires it)
    if os.getenv("PGSSLMODE", "").lower() in ("require", "prefer", "verify-full"):
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = True
        ssl_ctx.verify_mode = ssl.CERT_REQUIRED

    return await asyncpg.create_pool(
        user=cfg["PGUSER"],
        password=cfg["PGPASSWORD"],
        database=cfg["PGDATABASE"],
        host=cfg["PGHOST"],
        port=cfg.get("PGPORT", 5432),
        ssl=ssl_ctx,
        min_size=1,
        max_size=5,
    )


async def store_documents(docs: List[Document]) -> int:
    if not docs:
        return 0
    triples = embed_documents(docs)
    pool = await _get_pool()
    async with pool.acquire() as conn:
        # Ensure extension/table exist (idempotent safety for MVP)
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
              id SERIAL PRIMARY KEY,
              content TEXT,
              metadata JSONB,
              embedding VECTOR(384),
              year INT
            );
            """
        )
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_year ON documents (year)")

        # Pass embedding as JSON text and cast to vector in SQL
        insert_sql = (
            "INSERT INTO documents (content, metadata, embedding, year) "
            "VALUES ($1, $2, (($3)::jsonb)::text::vector, $4)"
        )
        await conn.executemany(
            insert_sql,
            [
                (
                    content,
                    json.dumps(metadata),
                    json.dumps(emb),
                    (metadata.get("year") if isinstance(metadata, dict) else None),
                )
                for content, metadata, emb in triples
            ],
        )
    await pool.close()
    return len(triples)


async def retrieve_similar_docs(query: str, k: int, year: Optional[int] = None) -> List[Dict[str, Any]]:
    q_emb = embed_query(query)
    pool = await _get_pool()
    async with pool.acquire() as conn:
        if year is None:
            rows = await conn.fetch(
                """
                WITH params AS (
                  SELECT ($1)::jsonb AS emb_json
                )
                SELECT content, metadata
                FROM documents, params
                ORDER BY embedding <-> ((SELECT emb_json FROM params)::text::vector)
                LIMIT $2
                """,
                json.dumps(q_emb),
                k,
            )
        else:
            rows = await conn.fetch(
                """
                WITH params AS (
                  SELECT ($1)::jsonb AS emb_json
                )
                SELECT content, metadata
                FROM documents, params
                WHERE year = $2
                ORDER BY embedding <-> ((SELECT emb_json FROM params)::text::vector)
                LIMIT $3
                """,
                json.dumps(q_emb),
                year,
                k,
            )
    await pool.close()
    return [
        {"content": r["content"], "metadata": r["metadata"]} for r in rows
    ]



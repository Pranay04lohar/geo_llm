"""
Database Configuration

This module handles database configuration by reading environment variables
and providing default values for PostgreSQL connection parameters.

Environment Variables:
- PGHOST: Database host (default: localhost)
- PGPORT: Database port (default: 5432)
- PGUSER: Database username (default: postgres)
- PGPASSWORD: Database password (default: postgres)
- PGDATABASE: Database name (default: rag_db)
- PGSSLMODE: SSL mode for secure connections (optional)

Author: RAG Pipeline Team
Version: 0.1.0
"""

import os
from typing import Dict, Any


def get_db_config() -> Dict[str, Any]:
    """
    Get database configuration from environment variables.
    
    This function reads PostgreSQL connection parameters from environment
    variables and provides sensible defaults for local development.
    
    Returns:
        Dict[str, Any]: Dictionary containing database connection parameters
        
    Environment Variables:
        PGHOST: Database hostname (default: localhost)
        PGPORT: Database port (default: 5432)
        PGUSER: Database username (default: postgres)
        PGPASSWORD: Database password (default: postgres)
        PGDATABASE: Database name (default: rag_db)
    """
    return {
        "PGUSER": os.getenv("PGUSER", "postgres"),
        "PGPASSWORD": os.getenv("PGPASSWORD", "postgres"),
        "PGDATABASE": os.getenv("PGDATABASE", "rag_db"),
        "PGHOST": os.getenv("PGHOST", "localhost"),
        "PGPORT": int(os.getenv("PGPORT", "5432")),
    }



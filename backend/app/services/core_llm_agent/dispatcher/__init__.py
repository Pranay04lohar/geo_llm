"""
Service dispatcher module - Route requests to appropriate services.

Components:
- ServiceDispatcher: Main dispatcher that routes to GEE/RAG/Search services
"""

from .service_dispatcher import ServiceDispatcher

__all__ = ["ServiceDispatcher"]

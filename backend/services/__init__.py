# -*- coding: utf-8 -*-

"""
Services module
Provides business logic services
"""

from .field_enricher_service import FieldEnricherService, get_field_enricher
from .event_bus import EventBus, EventType, get_event_bus
from .browser_pool import (
    BrowserPool,
    get_browser_pool,
    initialize_browser_pool,
    shutdown_browser_pool
)

__all__ = [
    'FieldEnricherService',
    'get_field_enricher',
    'EventBus',
    'EventType',
    'get_event_bus',
    'BrowserPool',
    'get_browser_pool',
    'initialize_browser_pool',
    'shutdown_browser_pool'
]

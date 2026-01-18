"""
Dependency injection module for manager instances.

Provides singleton factory functions for backend manager instances with
support for path changes and testing scenarios.
"""

import app.config as config
from typing import Optional

from backend.inbox_manager import InboxManager
from backend.listings_manager import ListingsManager
from backend.calendar_manager import CalendarManager


# Global singleton cache variables
_inbox_manager: Optional[InboxManager] = None
_listings_manager: Optional[ListingsManager] = None
_calendar_manager: Optional[CalendarManager] = None


def get_inbox_manager(recreate: bool = False) -> InboxManager:
    """
    Get or create the singleton InboxManager instance.
    
    Args:
        recreate: Force creation of a new instance even if one exists
    
    Returns:
        InboxManager instance
    """
    global _inbox_manager
    # Only create if it doesn't exist OR if the path has changed (important for tests!)
    current_path = config.INBOX_DB
    
    if _inbox_manager is None or _inbox_manager.db_path != current_path or recreate:
        _inbox_manager = InboxManager(current_path)
    
    return _inbox_manager


def get_listings_manager(recreate: bool = False) -> ListingsManager:
    """
    Get or create the singleton ListingsManager instance.
    
    Args:
        recreate: Force creation of a new instance even if one exists
        
    Returns:
        ListingsManager instance
    """
    global _listings_manager
    current_path = config.LISTINGS_DB
    
    if _listings_manager is None or _listings_manager.db_path != current_path or recreate:
        _listings_manager = ListingsManager(current_path)
        
    return _listings_manager


def get_calendar_manager(recreate: bool = False) -> CalendarManager:
    """
    Get or create the singleton CalendarManager instance.
    
    Args:
        recreate: Force creation of a new instance even if one exists
        
    Returns:
        CalendarManager instance
    """
    global _calendar_manager
    current_path = config.CALENDAR_DB
    
    if _calendar_manager is None or _calendar_manager.db_path != current_path or recreate:
        _calendar_manager = CalendarManager(current_path)
        
    return _calendar_manager
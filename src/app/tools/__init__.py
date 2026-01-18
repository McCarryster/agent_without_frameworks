"""
Tools module initialization.

Provides the get_tools_manager factory function for creating a
ToolsManager instance with all available property management tools.
"""

# from .listing_tools import get_listing_tools
# from .inbox_tools import get_inbox_tools
from .calendar_tools import get_calendar_tools
from .tool_manager import ToolsManager


def get_tools_manager() -> ToolsManager:
    """
    Create a ToolsManager with all available tools registered.
    
    Returns:
        ToolsManager instance with listing, inbox, and calendar tools
    """
    tools_manager = ToolsManager()
    # listing_tools = get_listing_tools()
    # inbox_tools = get_inbox_tools()
    calendar_tools = get_calendar_tools()

    # tools_manager.add_tools(listing_tools)
    # tools_manager.add_tools(inbox_tools)
    tools_manager.add_tools(calendar_tools)
    return tools_manager
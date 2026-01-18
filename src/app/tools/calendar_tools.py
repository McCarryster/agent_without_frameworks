from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.tools.tool_manager import Tool
from app.tools.utils import dataclass_to_json, json_serializer, dataclass_list_to_json
from app.dependencies import get_calendar_manager

class CreateEventInput(BaseModel):
    """Input schema for creating a calendar event."""
    name: str = Field(..., description="Event name/title")
    start_timestamp: datetime = Field(..., description="Event start time in ISO format (e.g., '2024-12-08T10:00:00')")
    end_timestamp: datetime = Field(..., description="Event end time in ISO format (e.g., '2024-12-08T11:00:00')")
    guests: Optional[List[str]] = Field(None, description="List of guest email addresses (optional)")

class GetEventInput(BaseModel):
    """Input schema for retrieving a specific event."""
    event_id: str = Field(..., description="Unique event identifier")

class UpdateEventInput(BaseModel):
    """Input schema for updating event properties."""
    event_id: str = Field(..., description="Unique event identifier")
    name: Optional[str] = Field(None, description="New event name/title")
    start_timestamp: Optional[datetime] = Field(None, description="Event new start time in ISO format (e.g., '2024-12-08T11:00:00')")
    end_timestamp: Optional[datetime] = Field(None, description="Event new end time in ISO format (e.g., '2024-12-08T11:00:00')")
    guests: Optional[list[str]] = Field(None, description="New list of guest email addresses")

class DeleteEventInput(BaseModel):
    """Input schema for deleting event."""
    event_id: str = Field(..., description="Unique event identifier")

class ListEventsInRangeInput(BaseModel):
    """Input schema for listing all events within a time range."""
    start_timestamp: datetime = Field(..., description="Start event range time in ISO format (e.g., '2024-12-08T10:00:00')")
    end_timestamp: datetime = Field(..., description="End event range time in ISO format (e.g., '2024-12-08T11:00:00')")

class SearchByNameInput(BaseModel):
    """Input schema for searching events by name."""
    search_term: str = Field(..., description="Text to search for in event names")

class ListAllEventsInput(BaseModel):
    """Input schema for listing all events."""
    pass

class CheckTimeAvailabilityInput(BaseModel):
    """Input schema for checking if a time slot is available (no conflicting events)."""
    start_timestamp: datetime = Field(..., description="Proposed event start time in ISO format (e.g., '2024-12-08T10:00:00')")
    end_timestamp: datetime = Field(..., description="Proposed event end time in ISO format (e.g., '2024-12-08T11:00:00')")

class SearchByGuestInput(BaseModel):
    """Input schema for searching events by guest email address."""
    name: str = Field(..., description="Email address to search for in guest lists")


def get_calendar_tools() -> List[Tool]:
    """
    Get all calendar management tools.
    
    Returns:
        List of Tool instances for calendar operations
    """
    calendar_manager = get_calendar_manager()
    
    tools = [
        Tool(
            function=calendar_manager.create_event,
            name="create_event",
            description="Create a new calendar event with name, time range, and optional guest list.",
            input_validator=CreateEventInput,
            output_serializer=dataclass_to_json
        ),
        Tool(
            function=calendar_manager.get_event,
            name="get_event",
            description="Retrieve details of a specific calendar event by its ID.",
            input_validator=GetEventInput,
            output_serializer=dataclass_to_json
        ),
        Tool(
            function=calendar_manager.update_event,
            name="update_event",
            description="Update an existing calendar event's details. Only provide fields that need to be changed.",
            input_validator=UpdateEventInput,
            output_serializer=dataclass_to_json
        ),
        Tool(
            function=calendar_manager.delete_event,
            name="delete_event",
            description="Delete a calendar event from the system.",
            input_validator=DeleteEventInput,
            output_serializer=json_serializer
        ),
        Tool(
            function=calendar_manager.list_events_in_range,
            name="list_events_in_range",
            description="List all calendar events within a specific time range.",
            input_validator=ListEventsInRangeInput,
            output_serializer=dataclass_list_to_json
        ),
        Tool(
            function=calendar_manager.search_by_name,
            name="search_events_by_name",
            description="Search for calendar events by searching text in their names.",
            input_validator=SearchByNameInput,
            output_serializer=dataclass_list_to_json
        ),
        Tool(
            function=calendar_manager.list_all_events,
            name="list_all_events",
            description="Get all calendar events in the system, ordered by start time.",
            input_validator=ListAllEventsInput,
            output_serializer=dataclass_list_to_json
        ),
        Tool(
            function=calendar_manager.check_availability,
            name="check_availability",
            description="Check if a time slot is available (returns true if no conflicting events exist).",
            input_validator=CheckTimeAvailabilityInput,
            output_serializer=json_serializer
        ),
        Tool(
            function=calendar_manager.search_by_guest,
            name="search_events_by_guest",
            description="Search for events that include a specific guest email address.",
            input_validator=SearchByGuestInput,
            output_serializer=dataclass_list_to_json
        ),
    ]
    
    return tools
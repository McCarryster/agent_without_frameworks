"""
Configuration module for the property management agent system.

Provides centralized configuration for:
- Database paths
- API credentials
- Model selection
- Agent parameters
"""

import enum
import os
import dotenv


# Load environment variables from .env file
dotenv.load_dotenv()

# Testing mode flag
IS_TESTING: bool = False

# Database file paths
INBOX_DB: str = "inbox.db"
LISTINGS_DB: str = "listings.db"
CALENDAR_DB: str = "calendar.db"

# API credentials
API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT: str = os.getenv("test_task", "property-management-agent")


class Models(enum.Enum):
    """Available Anthropic Claude model versions."""
    
    CLAUDE_SONNET_4_5 = "claude-sonnet-4-5"
    CLAUDE_HAIKU_4_5 = "claude-haiku-4-5"
    CLAUDE_OPUS_4_5 = "claude-opus-4-5"


# Default model configuration
DEFAULT_MODEL: str = Models.CLAUDE_HAIKU_4_5.value

# Agent step limits (max tool calls per agent execution)
STEPS_LIMIT_EMAIL_AGENT: int = 7
STEPS_LIMIT_QUERY_AGENT: int = 7

# Response generation parameters
MAX_TOKENS_PER_RESPONSE: int = 1024
TEMPERATURE: float = 0.0
# agent_without_frameworks

An LLM agent system built **without any agent framework**. No LangChain, no n8n, no CrewAI: just direct calls to the [Anthropic Messages API](https://docs.anthropic.com/) and a small, readable tool-calling loop written from scratch.

The example application is a **property management assistant** that can answer natural-language queries and process incoming emails by calling tools backed by local SQLite databases (currently calendar management).

## Why this exists

Frameworks hide what an agent actually does. This repo shows that the core of an agent is small:

1. Send messages and tool schemas to the model.
2. If the model asks for a tool, run it and feed the result back.
3. Repeat until the model signals it's done, or a step limit is hit.

Everything here (tool registration, schema generation, input validation, the agent loop, step limiting) is plain Python you can read in a few minutes.

## Features

- **Hand-rolled agent loop** with forced tool use (`tool_choice="any"`, parallel tool use disabled) and an explicit `end_execution` tool to finish.
- **Step limit** per agent run; raises `HumanInterventionRequired` instead of looping forever.
- **Tool abstraction** (`Tool` / `ToolsManager`) that wraps any Python function, validates LLM-provided arguments with Pydantic, and serializes results back to the model.
- **Automatic JSON schema generation** from Pydantic models, with `$ref` resolution and `Optional[...]` simplification so schemas are Anthropic-compatible.
- **Two specialized agents** sharing one base class: `QueryAgent` and `EmailAgent`.
- **Prompt-injection guardrails** in the email agent's system prompt, plus data-accuracy rules so the model preserves addresses, names, and dates exactly.
- **Optional LangSmith tracing**: used automatically if installed and configured, silently skipped otherwise.
- **SQLite-backed managers** for calendar, inbox, and listings, wired up through simple singleton dependency functions.

## Project structure

```
.
├── requirements.txt
└── src
    ├── api.py                     # Entry points + CLI: process_query(), process_email()
    ├── app
    │   ├── agents.py              # BaseAgent, EmailAgent, QueryAgent + factory functions
    │   ├── config.py              # Models, DB paths, step limits, API keys
    │   ├── dependencies.py        # Singleton getters for backend managers
    │   ├── prompts.py             # System prompts and user prompt templates
    │   └── tools
    │       ├── __init__.py        # get_tools_manager(): registers available tools
    │       ├── calendar_tools.py  # Calendar tool definitions + Pydantic input schemas
    │       ├── tool_manager.py    # Tool and ToolsManager classes
    │       └── utils.py           # Schema conversion and JSON serializers
    └── backend
        ├── calendar_manager.py    # SQLite calendar (events, availability, guests)
        ├── inbox_manager.py       # SQLite inbox (send/receive/search emails)
        └── listings_manager.py    # SQLite property listings (search, rent range, ...)
```

## How it works

```
 CLI / api.py
      │
      ▼
 QueryAgent / EmailAgent ──► BaseAgent.run()
                                  │
        ┌─────────────────────────┤  loop (max N steps)
        │                         ▼
        │              Anthropic Messages API
        │                         │  tool_use block
        │                         ▼
        │                 ToolsManager.call_tool()
        │                         │  validate (Pydantic) → run → serialize
        │                         ▼
        └────────────── tool_result appended to messages
                                  │
                      end_execution tool called
                                  ▼
                       (success: bool, output: str)
```

- `process_query(query)` runs the `QueryAgent` on a free-form question.
- `process_email(subject, body, sender)` stores the email in the inbox, then runs the `EmailAgent` on it.
- If an agent fails (or reports failure), both functions return the sentinel string `<NEEDS MANUAL RESPONSE>`.

### Available tools

Calendar tools are currently registered with the agents:

| Tool | Description |
|------|-------------|
| `create_event` | Create an event with a name, time range, and optional guests |
| `get_event` | Fetch an event by ID |
| `update_event` | Update any fields of an existing event |
| `delete_event` | Delete an event |
| `list_events_in_range` | List events within a time range |
| `list_all_events` | List all events ordered by start time |
| `search_events_by_name` | Search events by name text |
| `search_events_by_guest` | Find events that include a guest email |
| `check_availability` | Check whether a time slot has no conflicts |

The inbox and listings backends are implemented (`inbox_manager.py`, `listings_manager.py`), and their tool registrations are stubbed out in `tools/__init__.py`, ready to be added following the same pattern as `calendar_tools.py`.

## Getting started

### Prerequisites

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)

### Installation

```bash
git clone https://github.com/McCarryster/agent_without_frameworks.git
cd agent_without_frameworks

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install pydantic python-dotenv   # imported by the code
pip install langsmith                # optional: tracing
```

### Configuration

Create a `.env` file in the directory you run the app from (e.g. `src/`):

```env
ANTHROPIC_API_KEY=your-anthropic-api-key

# Optional: LangSmith tracing
LANGSMITH_API_KEY=your-langsmith-api-key
```

Other settings live in `src/app/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `DEFAULT_MODEL` | `claude-haiku-4-5` | Model used by the agents |
| `STEPS_LIMIT_QUERY_AGENT` | `7` | Max tool calls per query run |
| `STEPS_LIMIT_EMAIL_AGENT` | `7` | Max tool calls per email run |
| `MAX_TOKENS_PER_RESPONSE` | `1024` | Max tokens per model response |
| `TEMPERATURE` | `0.0` | Sampling temperature |
| `INBOX_DB` / `LISTINGS_DB` / `CALENDAR_DB` | `inbox.db` / `listings.db` / `calendar.db` | SQLite file paths, created in the working directory |

## Usage

Run commands from inside `src/`:

```bash
cd src
```

**Ask a question or give a task:**

```bash
python api.py --query "Am I free on December 10th between 2pm and 3pm?"
python api.py --query "Schedule a meeting called 'Property viewing' tomorrow at 10:00 for one hour with anna@example.com"
```

**Process an incoming email** (sender, subject, body):

```bash
python api.py --email "tenant@example.com" "Viewing request" "Hi, could we schedule a viewing next Tuesday at 11:00?"
```

**From Python:**

```python
from api import process_query, process_email

print(process_query("List all events this week"))
print(process_email(
    subject="Viewing request",
    body="Could we schedule a viewing next Tuesday at 11:00?",
    sender="tenant@example.com",
))
```

## Adding your own tool

1. Define a Pydantic input model and wrap your function in a `Tool`:

```python
from pydantic import BaseModel, Field
from app.tools.tool_manager import Tool
from app.tools.utils import json_serializer

class GreetInput(BaseModel):
    name: str = Field(..., description="Who to greet")

def greet(name: str) -> str:
    return f"Hello, {name}!"

greet_tool = Tool(
    function=greet,
    name="greet",
    description="Greet a person by name.",
    input_validator=GreetInput,      # JSON schema is generated from this
    output_serializer=json_serializer,
)
```

2. Register it in `get_tools_manager()` in `src/app/tools/__init__.py`:

```python
tools_manager.add_tool(greet_tool)
```

The schema sent to the model is generated automatically from the Pydantic model, and arguments are validated before your function runs.

## Tech stack

- Python
- [`anthropic`](https://pypi.org/project/anthropic/) SDK (direct API calls)
- [`pydantic`](https://docs.pydantic.dev/) for tool input validation and schema generation
- SQLite (via the standard library) for storage
- [`pytest`](https://docs.pytest.org/) for testing
- [LangSmith](https://smith.langchain.com/) (optional) for tracing

## License

No license specified yet. Add a `LICENSE` file to clarify how others may use this code.

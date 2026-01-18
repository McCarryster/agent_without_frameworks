"""
Agent system for processing property management tasks.

Provides BaseAgent, EmailAgent, and QueryAgent classes for handling
user queries and email processing with LLM-powered tool calling.
Includes optional LangSmith tracing integration.
"""

import os
from typing import Tuple
import anthropic

from app import config, prompts
from app.tools.tool_manager import Tool, ToolsManager
from anthropic.types import MessageParam, ToolChoiceParam, ToolChoiceAnyParam
from app.tools import get_tools_manager


# LangSmith integration for tracing
try:
    from langsmith import traceable
    from langsmith.wrappers import wrap_anthropic
    LANGSMITH_AVAILABLE = True
    
    # Configure LangSmith if API key is available
    if config.LANGSMITH_API_KEY:
        os.environ["LANGSMITH_API_KEY"] = config.LANGSMITH_API_KEY
        os.environ["LANGSMITH_TRACING"] = "true"
        if config.LANGSMITH_PROJECT:
            os.environ["LANGSMITH_PROJECT"] = config.LANGSMITH_PROJECT
except ImportError:
    LANGSMITH_AVAILABLE = False
    # Create a no-op decorator if LangSmith is not available
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator if not args else decorator(args[0])
    def wrap_anthropic(client):
        return client


class HumanInterventionRequired(Exception):
    """Raised when agent reaches step limit and requires manual intervention."""
    pass

class BaseAgent:
    """
    Base agent class for LLM-powered task execution with tool calling.
    
    Manages interaction with Claude API, tool execution, and conversation state
    with automatic step limiting to prevent runaway execution.
    """
    
    def __init__(
        self,
        name: str,
        client: anthropic.Anthropic,
        tools_manager: ToolsManager,
        system_prompt: str = "",
        steps_limit: int = 5
    ) -> None:
        """
        Initialize the base agent.
        
        Args:
            name: Agent identifier
            client: Anthropic API client instance
            tools_manager: Manager for available tools
            system_prompt: System-level instructions for the LLM
            steps_limit: Maximum tool call iterations before intervention
        """
        self.name = name
        self.tools_manager = tools_manager
        self.system_prompt = system_prompt
        self.client: anthropic.Anthropic = client
        self.steps_limit = steps_limit
        
        if not self.tools_manager.has_tool('end_execution'):
            self.tools_manager.add_tool(
                Tool(
                    function=lambda success, output: {"success": success, "output": output},
                    name="end_execution",
                    description="Ends the execution of the agent with a success status and output message.",
                    input_schema={
                        'type': 'object',
                        'properties': {
                            "status": {"type": "string", "description": "Either 'success' or 'failure'."},
                            "output": {"type": "string", "description": "The final output message of the agent."}
                        },
                        'required': ['status', 'output']
                    }
                )
            )
        
    @traceable(name="call_llm")
    def call_llm(
        self,
        messages: list[MessageParam],
        tool_choice: ToolChoiceParam
    ) -> anthropic.types.Message:
        """
        Make a request to the Claude API with tool support.
        
        Args:
            messages: Conversation history
            tool_choice: Tool selection strategy for the LLM
            
        Returns:
            Claude API message response
        """
        response = self.client.messages.create(
            model=config.DEFAULT_MODEL,
            max_tokens=config.MAX_TOKENS_PER_RESPONSE,
            temperature=config.TEMPERATURE,
            tools=self.tools_manager.get_schema_for_llm(),
            messages=messages,
            tool_choice=tool_choice,
            system=self.system_prompt
        )
        return response
    
    @traceable(name="agent_run")
    def run(self, query: str) -> Tuple[bool, str]:
        """
        Execute the agent's task loop with tool calling.
        
        Args:
            query: User query or task description
            
        Returns:
            Tuple of (success: bool, output: str)
            
        Raises:
            HumanInterventionRequired: When step limit is reached
        """
        
        messages = [MessageParam(role="user", content=query)]
        nb_steps = 0
        while True:
            res = self.call_llm(
                messages,
                tool_choice=ToolChoiceAnyParam(type="any", disable_parallel_tool_use=True)
            )
            print(res)

            tool_use = next(block for block in res.content if block.type == "tool_use")
            print(tool_use)

            if tool_use.name == "end_execution":
                success, result = bool(tool_use.input['status'] == "success"), str(tool_use.input['output'])
                return success, result
            print(tool_use.name, tool_use.input)

            tool_call_res = self.tools_manager.call_tool(tool_use.name, tool_use.input)
            messages.append(MessageParam(role="assistant", content=res.content))
            messages.append(MessageParam(
                role="user",
                content=[{
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": tool_call_res
                }]
            ))
            nb_steps += 1
            if nb_steps >= self.steps_limit:
                raise HumanInterventionRequired("Maximum number of steps reached, human intervention required.")


class EmailAgent(BaseAgent):
    """
    Specialized agent for processing email requests.
    
    Handles incoming emails with sender, topic, and body information,
    determining appropriate actions using available tools.
    """
    
    @traceable(name="email_agent_run")
    def run(self, sender: str, topic: str, body: str) -> Tuple[bool, str]:
        """
        Process an email and determine appropriate response.
        
        Args:
            sender: Email sender address
            topic: Email subject line
            body: Email body content
            
        Returns:
            Tuple of (success: bool, response: str)
        """
        prompt = prompts.email_agent_query_prompt_template.format(
            sender=sender,
            topic=topic,
            body=body
        )
        return super().run(prompt)

class QueryAgent(BaseAgent):
    """
    Specialized agent for processing user queries.
    
    Handles general property management queries and executes
    appropriate tool calls to fulfill requests.
    """
    
    @traceable(name="query_agent_run")
    def run(self, query: str) -> Tuple[bool, str]:
        """
        Process a user query and generate a response.
        
        Args:
            query: User's natural language query
            
        Returns:
            Tuple of (success: bool, response: str)
        """
        prompt = prompts.query_agent_query_prompt_template.format(query=query)
        return super().run(prompt)


def get_email_agent() -> EmailAgent:
    """
    Factory function for EmailAgent with proper configuration.
    
    Returns:
        Configured EmailAgent instance with LangSmith tracing if available
    """
    client = anthropic.Anthropic(api_key=config.API_KEY)
    # Wrap client with LangSmith if available
    if LANGSMITH_AVAILABLE and config.LANGSMITH_API_KEY:
        client = wrap_anthropic(client)
    tools_manager = get_tools_manager()
    system_prompt = prompts.EMAIL_AGENT_SYSTEM_PROMPT
    agent = EmailAgent(
        name="EmailAgent",
        client=client,
        tools_manager=tools_manager,
        system_prompt=system_prompt,
        steps_limit=config.STEPS_LIMIT_EMAIL_AGENT
    )
    return agent

def get_query_agent() -> QueryAgent:
    """
    Factory function for QueryAgent with proper configuration.
    
    Returns:
        Configured QueryAgent instance with LangSmith tracing if available
    """
    client = anthropic.Anthropic(api_key=config.API_KEY)
    # Wrap client with LangSmith if available
    if LANGSMITH_AVAILABLE and config.LANGSMITH_API_KEY:
        client = wrap_anthropic(client)
    tools_manager = get_tools_manager()
    system_prompt = prompts.QUERY_AGENT_SYSTEM_PROMPT
    agent = QueryAgent(
        name="QueryAgent",
        client=client,
        tools_manager=tools_manager,
        system_prompt=system_prompt,
        steps_limit=config.STEPS_LIMIT_QUERY_AGENT
    )
    return agent
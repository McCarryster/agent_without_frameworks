from pydantic import BaseModel, Field
from typing import Any, Callable, Dict, List, Optional, get_type_hints
from anthropic.types.tool_param import InputSchemaTyped
from anthropic.types import ToolParam
import inspect
import re
from app.tools.utils import pydantic_to_anthropic_schema, python_type_to_json_type

class Tool:
    """
    Wrapper for Python functions to enable LLM tool calling.
    
    Automatically infers JSON schemas from type hints and docstrings,
    validates inputs using Pydantic models, and serializes outputs.
    """
    
    def __init__(
        self,
        function: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        input_schema: Optional[Dict | InputSchemaTyped] = None,
        input_validator: Optional[Callable[[Dict], Any] | type[BaseModel]] = None,
        output_serializer: Optional[Callable[[Any], str]] = None,
    ) -> None:
        """
        Initialize a Tool wrapper for a function.
        
        Args:
            function: Python function to wrap
            name: Tool name (defaults to function name)
            description: Tool description (inferred from docstring if not provided)
            input_schema: JSON schema for parameters (auto-generated if not provided)
            input_validator: Pydantic model or callable for input validation
            output_serializer: Function to serialize output (defaults to str())
        """
        self.function = function
        self.name = name if name is not None else function.__name__
        self.description = description or ''
        self.input_schema = input_schema
        self.input_validator = input_validator
        self.output_serializer = output_serializer or (lambda x: str(x))
        
        self._input_validator_is_pydantic = isinstance(self.input_validator, type) and issubclass(self.input_validator, BaseModel)
        
        self._infer_missing_schema_values()
        
    def _infer_missing_schema_values(self) -> None:
        """
        Infer missing tool attributes from function metadata.
        
        Extracts description from docstring and generates JSON schema
        from type hints and parameter documentation.
        """
        # if input_schema is not provided, try to generate from input_validator if it's a Pydantic model
        if not self.input_schema and self._input_validator_is_pydantic:
            self.input_schema = pydantic_to_anthropic_schema(model=self.input_validator) # type: ignore

        # Parse docstring
        docstring = inspect.getdoc(self.function) or ""
        
        # Infer description if missing
        if self.description == '':
            # Extract first line or paragraph as description
            lines = docstring.strip().split('\n')
            description_parts = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith(':') and not line.lower().startswith('args:') and not line.lower().startswith('returns:') and not line.lower().startswith('parameters:'):
                    description_parts.append(line)
                elif description_parts:
                    break
            self.description = ' '.join(description_parts) if description_parts else f"Executes the {self.name} function."
        
        # Infer input schema if missing
        if self.input_schema is None:
            try:
                type_hints = get_type_hints(self.function)
            except Exception:
                type_hints = {}
            
            sig = inspect.signature(self.function)
            properties = {}
            
            # Parse parameter descriptions from docstring
            param_descriptions = {}
            param_pattern = r':param\s+(\w+):\s*(.+?)(?=\n\s*:|$)'
            for match in re.finditer(param_pattern, docstring, re.DOTALL):
                param_name, param_desc = match.groups()
                param_descriptions[param_name] = param_desc.strip().replace('\n', ' ')
            
            # Also try Google/Numpy style docstrings
            args_section_match = re.search(r'(?:Args|Arguments|Parameters):\s*\n((?:[ \t]+.+\n?)+)', docstring, re.IGNORECASE)
            if args_section_match:
                args_text = args_section_match.group(1)
                # Match: param_name (type): description or param_name: description
                param_pattern = re.compile(r'^[ \t]+(\w+)\s*(?:\([^)]*\))?\s*:\s*(.+)', re.MULTILINE)
                for match in param_pattern.finditer(args_text):
                    param_name, param_desc = match.groups()
                    # Handle multi-line descriptions by getting text until next param or end
                    if param_name not in param_descriptions:
                        param_descriptions[param_name] = param_desc.strip()
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                param_schema: Dict[str, Any] = {}
                
                # Get type from hints
                if param_name in type_hints:
                    param_type = type_hints[param_name]
                    param_schema['type'] = python_type_to_json_type(param_type)
                else:
                    param_schema['type'] = 'string'  # Default type
                
                # Add description if available
                if param_name in param_descriptions:
                    param_schema['description'] = param_descriptions[param_name]
                
                properties[param_name] = param_schema
            
            self.input_schema = properties if properties else {}
    
    def __call__(self, args: Dict[str, Any]) -> Any:
        """
        Execute the tool with validation and serialization.
        
        Args:
            args: Raw arguments from LLM
        
        Returns:
            Serialized function output
        """
        print(f"Calling tool: {self.name} with kwargs: {args}")
        if self.input_validator:
            if self._input_validator_is_pydantic:
                validated_args: Dict[str, Any] = self.input_validator.model_validate(args).model_dump(exclude_none=True)
            else:
                validated_args: Dict[str, Any] = self.input_validator(args)  # type: ignore
        else:
            validated_args = args
        print(f"Calling tool: {self.name} with validated_args: {validated_args}")
        tool_call_res = self.function(**validated_args)
        tool_call_res = self.output_serializer(tool_call_res)
        return tool_call_res

    def parse_tool_response(self, response: Any) -> str:
        """
        Convert tool output to string format.
        
        Args:
            response: Raw function return value
            
        Returns:
            String representation of response
        """
        return str(response)


class ToolsManager:
    """
    Registry and manager for Tool instances.
    
    Manages tool registration, schema generation, and execution
    for LLM-powered function calling.
    """
    
    def __init__(self) -> None:
        """Initialize an empty tools registry."""
        self.tools: Dict[str, Tool] = {}

    def has_tool(self, name: str) -> bool:
        """
        Check if a tool is registered.
        
        Args:
            name: Tool name to check
            
        Returns:
            True if tool exists, False otherwise
        """
        return name in self.tools
    
    def add_tool(self, tool: Tool) -> None:
        """
        Register a single tool.
        
        Args:
            tool: Tool instance to register
        """
        self.tools[tool.name] = tool
    
    def add_tools(self, tools: List[Tool]) -> None:
        """
        Register multiple tools at once.
        
        Args:
            tools: List of Tool instances to register
        """
        for tool in tools:
            self.add_tool(tool)
    
    def remove_tool(self, name: str) -> None:
        """
        Unregister a tool by name.
        
        Args:
            name: Tool name to remove
        """
        if name in self.tools:
            del self.tools[name]
    
    def remove_tools(self, names: List[str]) -> None:
        """
        Unregister multiple tools at once.
        
        Args:
            names: List of tool names to remove
        """
        for name in names:
            self.remove_tool(name)
    
    def call_tool(self, name: str, args: Dict[str, Any]) -> str:
        """
        Execute a registered tool by name.
        
        Args:
            name: Tool name to call
            args: Arguments to pass to the tool
            
        Returns:
            Serialized tool output
            
        Raises:
            ValueError: If tool is not registered
        """
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' is not registered.")
        tool = self.tools[name]
        tool_func_call_res_raw = tool(args)
        tool_call_res = tool.parse_tool_response(tool_func_call_res_raw)
        return tool_call_res
    
    def get_schema_for_llm(self, tools_subset: Optional[List[str]] = None) -> List[ToolParam]:
        """
        Generate Anthropic-compatible tool schemas for LLM.
        
        Args:
            tools_subset: Optional list of tool names to include (defaults to all tools)
            
        Returns:
            List of ToolParam objects for Anthropic API
            
        Raises:
            NotImplementedError: If a tool has non-dict input schema
        """
        tools_subset = tools_subset or list(self.tools.keys())
        schema_list = []
        for tool in (self.tools[name] for name in tools_subset):
            input_schema = tool.input_schema if isinstance(tool.input_schema, dict) else None
            if input_schema is None:
                raise NotImplementedError("Only dict input_schema is supported in this example.")
            schema_list.append(
                ToolParam(
                    name=tool.name,
                    description=tool.description,
                    input_schema=input_schema,
                )
            )
        return schema_list

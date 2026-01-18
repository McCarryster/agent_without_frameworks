import json
import typing
from typing import Any, Dict, List, Type
from pydantic import BaseModel

def resolve_refs(schema_node: Any, defs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively resolve $ref and clean up the schema.
    
    Args:
        schema_node: JSON schema node to process
        
    Returns:
        Resolved and cleaned schema node
    """
    if not isinstance(schema_node, dict):
        return schema_node

    # Handle $ref: replace the reference with the actual definition
    if '$ref' in schema_node:
        ref_key = schema_node['$ref'].split('/')[-1]
        # Get the definition and merge it
        resolved = defs.get(ref_key, {}).copy()
        # If the ref had other keys (like descriptions), keep them
        for k, v in schema_node.items():
            if k != '$ref':
                resolved[k] = v
        return resolve_refs(resolved, defs)

    # Handle "Optional" (anyOf: [type, null]). We simplify this to just the type, as "required" list controls optionality
    if 'anyOf' in schema_node:
        options = schema_node['anyOf']
        non_null_options = [opt for opt in options if opt.get('type') != 'null']
        if len(non_null_options) == 1:
            # It was Optional[Type], so just grab Type
            merged = non_null_options[0].copy()
            # Merge keys from the parent (like description)
            for k, v in schema_node.items():
                if k != 'anyOf':
                    merged[k] = v
            return resolve_refs(merged, defs)

    # Recursively process properties
    if 'properties' in schema_node:
        for prop, details in schema_node['properties'].items():
            print('SHIT', prop, details)
            schema_node['properties'][prop] = resolve_refs(details, defs)
    
    # Recursively process array items
    if 'items' in schema_node:
        schema_node['items'] = resolve_refs(schema_node['items'], defs)

    return schema_node

def pydantic_to_anthropic_schema(
    model: Type[BaseModel],
) -> Dict[str, Any]:
    """
    Convert a Pydantic model into an Anthropic tool schema.
    
    Resolves $defs/$ref (nested models become inline objects),
    cleans up Pydantic-specific fields, and handles Optional[] types
    by simplifying "anyOf" [type, null] to just [type].
    
    Args:
        model: Pydantic BaseModel class to convert
        
    Returns:
        Anthropic-compatible JSON schema dictionary
    """
    
    # Generate the standard JSON schema from Pydantic
    json_schema = model.model_json_schema(mode='validation') # 'validation' ensures we get the expected schema for input validation
    json_schema.pop('title', None)  # Anthropic doesn't use titles for fields
    defs = json_schema.pop('$defs', {})

    cleaned_schema = resolve_refs(json_schema, defs) # remove internal pydantic shit recursively
    return cleaned_schema

def python_type_to_json_type(python_type) -> str:
    """
    Convert Python type hints to JSON schema types.
    
    Args:
        python_type: Python type annotation or string type name
        
    Returns:
        JSON schema type string (integer, number, boolean, string, array, object)
    """
    
    # Handle string type annotations (string path)
    if isinstance(python_type, str):
        python_type_lower = python_type.lower()
        if 'int' in python_type_lower:
            return 'integer'
        elif 'float' in python_type_lower or 'number' in python_type_lower:
            return 'number'
        elif 'bool' in python_type_lower:
            return 'boolean'
        elif 'list' in python_type_lower or 'array' in python_type_lower:
            return 'array'
        elif 'dict' in python_type_lower or 'object' in python_type_lower:
            return 'object'
        return 'string'
    
    # Get origin for generic types (class path)
    origin = getattr(python_type, '__origin__', None)
    
    if python_type == int:
        return 'integer'
    elif python_type == float:
        return 'number'
    elif python_type == bool:
        return 'boolean'
    elif python_type == str:
        return 'string'
    elif origin in (list, typing.List):
        return 'array'
    elif origin in (dict, typing.Dict):
        return 'object'
    else:
        return 'string'

def dataclass_to_json(obj: Any) -> str:
    """
    Serialize a dataclass object to JSON string.
    
    Args:
        obj: Dataclass instance or None
        
    Returns:
        JSON string representation
    """
    from dataclasses import asdict
    if obj is None:
        return json.dumps(None)
    return json.dumps(asdict(obj))

def dataclass_list_to_json(obj_list: List[Any]) -> str:
    """
    Serialize a list of dataclass objects to JSON string.
    
    Args:
        obj_list: List of dataclass instances
        
    Returns:
        JSON string representation of list
    """
    from dataclasses import asdict
    return json.dumps([asdict(obj) for obj in obj_list])

def json_serializer(obj: Any) -> str:
    """
    Generic JSON serializer.
    
    Args:
        obj: Any JSON-serializable object
        
    Returns:
        JSON string representation
    """
    return json.dumps(obj)

"""
Tool Registry for TradeMaster 2.0

This module manages the registration and retrieval of tools.
It maintains a central registry of all available tools.
"""

import logging
from typing import Dict, List, Type, Optional
from .base_tool import BaseTool

logger = logging.getLogger("TradeMaster.Tools.Registry")

class ToolRegistry:
    """
    Registry for TradeMaster tools.
    
    This class implements the registry pattern to manage all available tools in the
    TradeMaster system. It provides methods to register new tools, retrieve tools
    by name, list all available tools, and clear the registry.
    
    The registry ensures that:
    1. Each tool has a unique name to prevent conflicts
    2. Tools can be easily accessed by their name
    3. The system can discover all available tools
    4. Tools can be dynamically added or removed
    
    This centralized approach simplifies tool management and allows the LLM engine
    to access tools without needing to know how they're instantiated.
    """
    
    def __init__(self):
        """
        Initialize an empty tool registry.
        
        Creates a new registry with an empty dictionary to store tool instances,
        where the keys are tool names and the values are tool instances.
        """
        self._tools: Dict[str, BaseTool] = {}
        logger.info("Tool Registry initialized")
    
    def register_tool(self, tool: BaseTool) -> None:
        """
        Register a tool with the registry.
        
        This method adds a tool instance to the registry, making it available for use
        by the LLM engine. It ensures that tool names are unique to prevent conflicts
        and maintains a centralized collection of all available tools.
        
        Args:
            tool: An instance of BaseTool to register. Must have a unique name.
            
        Raises:
            ValueError: If a tool with the same name is already registered
        """
        if tool.name in self._tools:
            raise ValueError(f"A tool with the name '{tool.name}' is already registered")
        
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        Retrieves a tool instance from the registry by its name. This is the primary
        method used by the LLM engine to access tools when they need to be executed.
        It provides a simple lookup mechanism that abstracts away the details of
        how tools are stored and managed.
        
        Args:
            name: The name of the tool to retrieve
            
        Returns:
            The tool instance if found, or None if no tool with the given name exists
        """
        return self._tools.get(name)
    
    def list_tools(self) -> List[BaseTool]:
        """
        Get a list of all registered tools.
        
        This method provides access to all available tools in the system, which is
        useful for discovery, introspection, and debugging purposes. It allows
        the system to enumerate all available capabilities without needing to
        know their names in advance.
        
        Returns:
            A list of all registered tool instances
        """
        return list(self._tools.values())
    
    def get_tool_descriptions(self) -> Dict[str, str]:
        """
        Get a dictionary of tool names and descriptions.
        
        Returns:
            A dictionary mapping tool names to descriptions
        """
        return {tool.name: tool.description for tool in self._tools.values()}
    
    def get_tool_info(self) -> List[Dict]:
        """
        Get detailed information about all tools.
        
        Returns:
            A list of dictionaries containing tool information
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "examples": tool.examples
            }
            for tool in self._tools.values()
        ]
    
    def clear(self) -> None:
        """Remove all tools from the registry."""
        self._tools.clear()
        logger.info("Tool Registry cleared")


# Create a singleton instance
registry = ToolRegistry()
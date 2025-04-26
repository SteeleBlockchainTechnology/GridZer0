"""
Base Tool Interface for TradeMaster 2.0

This module defines the base interface that all tools must implement.
Tools extend the bot's capabilities by providing specialized functions.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List

logger = logging.getLogger("TradeMaster.Tools")

class BaseTool(ABC):
    """
    Abstract base class for all TradeMaster tools.
    
    This class defines the interface that all tools must implement. It provides
    the structure for tool identification, parameter definition, and execution.
    
    All tools in the TradeMaster system inherit from this class and must implement
    its abstract methods to ensure consistent behavior across the system.
    
    The tool system allows the LLM to access external data sources and APIs
    to provide up-to-date market information to users.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        The name of the tool. Must be unique across all tools.
        
        This name is used as the identifier when registering the tool and
        when the LLM needs to invoke the tool. It should be descriptive
        of the tool's function and follow snake_case naming convention.
        
        Returns:
            A unique string identifier for the tool
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        A description of what the tool does.
        
        This description is used by the LLM to understand when and how to use
        the tool. It should clearly explain the tool's purpose, capabilities,
        and when it should be used in response to user queries.
        
        Returns:
            A string describing the tool's functionality
        """
        pass
    
    @property
    def parameters(self) -> List[Dict[str, Any]]:
        """
        List of parameters the tool accepts.
        
        This method defines the parameters that can be passed to the tool when executed.
        Each parameter is defined as a dictionary with metadata about its name, type,
        description, whether it's required, and default values.
        
        The LLM uses this information to properly format requests to the tool and
        to understand what information it needs to collect from the user.
        
        Returns:
            A list of parameter dictionaries with these keys:
            - name: The parameter name
            - type: The parameter type (string, number, boolean)
            - description: A description of the parameter
            - required: Whether the parameter is required
            - default: The default value (if not required)
        """
        return []
    
    @property
    def examples(self) -> List[str]:
        """
        Example invocations of the tool.
        
        These examples help the LLM understand how to properly invoke the tool
        with different parameter combinations. They serve as a reference for
        the correct syntax and common use cases.
        
        Returns:
            A list of example command strings showing how to use the tool
        """
        return []
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool with the provided parameters.
        
        This is the main entry point for tool functionality. When the LLM determines
        that a tool should be used, it calls this method with the appropriate parameters.
        
        The method should:
        1. Validate the provided parameters
        2. Perform the tool's core functionality (e.g., API calls, data processing)
        3. Return the results in a standardized format
        4. Handle errors gracefully and return informative error messages
        
        All tools should implement proper error handling and logging to ensure
        reliability and debuggability.
        
        Args:
            **kwargs: The parameters for the tool as key-value pairs
            
        Returns:
            A dictionary containing the tool's output and any relevant data
        """
        pass
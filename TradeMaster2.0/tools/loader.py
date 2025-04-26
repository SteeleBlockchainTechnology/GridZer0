"""
Tool Loader for TradeMaster 2.0

This module handles initializing and registering all available tools.
"""

import logging
from typing import List

from .registry import registry
from .price_checker import PriceCheckerTool
from .market_trends import MarketTrendsTool
from .browser_search import BrowserSearchTool

logger = logging.getLogger("TradeMaster.Tools.Loader")

def load_tools() -> List[str]:
    """
    Initialize and register all available tools.
    
    Returns:
        A list of registered tool names
    """
    # Clear existing tools
    registry.clear()
    
    # Register tools
    registry.register_tool(PriceCheckerTool())
    registry.register_tool(MarketTrendsTool())
    registry.register_tool(BrowserSearchTool())
    
    # Add more tools here as they are implemented
    
    # Return list of registered tool names
    tool_names = [tool.name for tool in registry.list_tools()]
    logger.info(f"Loaded {len(tool_names)} tools: {', '.join(tool_names)}")
    
    return tool_names
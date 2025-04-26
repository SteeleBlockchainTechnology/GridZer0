"""
Tools package for TradeMaster 2.0

This package contains all the tools that extend the bot's capabilities.
"""

from .base_tool import BaseTool
from .registry import registry, ToolRegistry
from .loader import load_tools

__all__ = ['BaseTool', 'registry', 'ToolRegistry', 'load_tools']
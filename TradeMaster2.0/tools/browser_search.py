"""Browser Search Tool for TradeMaster 2.0

This tool provides web browsing capabilities using the browser-use library with Playwright.
It serves as a fallback mechanism when primary API calls fail.
"""

import logging
import os
import re
from typing import Dict, Any, List, Optional
import asyncio
import json

from .base_tool import BaseTool
from browser_use import Agent, Browser, BrowserConfig
from browser_use.browser.context import BrowserContextConfig, BrowserContextWindowSize
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Sanitize log messages by removing emoji characters and handling Unicode issues
def sanitize_log_message(message):
    if not isinstance(message, str):
        try:
            message = str(message)
        except Exception:
            return "[Unprintable object]"
    
    try:
        message = message.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F700-\U0001F77F"  # alchemical symbols
            "\U0001F780-\U0001F7FF"  # Geometric Shapes
            "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            "\U0001FA00-\U0001FA6F"  # Chess Symbols
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "\U00002702-\U000027B0"  # Dingbats
            "\U000024C2-\U0001F251"
            "\U00002500-\U00002BEF"  # Additional symbols
            "\U00002300-\U000023FF"  # Miscellaneous Technical
            "\U00002B00-\U00002BFF"  # Miscellaneous Symbols and Arrows
            "\U0001F000-\U0001F02F"  # Mahjong Tiles
            "\U0001F0A0-\U0001F0FF"  # Playing Cards
            "\U0001F100-\U0001F1FF"  # Enclosed Alphanumeric Supplement
            "]")
        return emoji_pattern.sub(r'', message)
    except Exception:
        return "[Unicode encoding error]"

# Custom logger adapter for sanitizing messages
class SanitizedLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return sanitize_log_message(msg), kwargs

logger = SanitizedLoggerAdapter(logging.getLogger("TradeMaster.Tools.BrowserSearch"), {})

class BrowserSearchTool(BaseTool):
    """
    Tool for performing web searches using browser-use library with Playwright.
    
    This tool leverages the browser-use library to perform web searches
    and extract financial information from websites as a fallback mechanism.
    """
    
    @property
    def name(self) -> str:
        return "browser_search"
    
    @property
    def description(self) -> str:
        return "Performs web searches for financial information using a browser"
    
    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "query",
                "type": "string",
                "description": "The search query to perform",
                "required": True
            },
            {
                "name": "search_type",
                "type": "string",
                "description": "The type of search: 'price', 'trends', or 'general'",
                "required": False,
                "default": "general"
            }
        ]
    
    @property
    def examples(self) -> List[str]:
        return [
            "browser_search query='current price of Bitcoin'",
            "browser_search query='top gaining cryptocurrencies today' search_type='trends'",
            "browser_search query='AAPL stock price' search_type='price'"
        ]
    
    def __init__(self):
        """Initialize the browser search tool."""
        try:
            import browser_use
            self.browser_use_available = True
            logger.info("browser-use package is available")
        except ImportError:
            self.browser_use_available = False
            logger.warning("browser-use package not available. Browser search will not work.")
            logger.info("To install browser-use, run: poetry add browser-use")
        
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        
        if self.groq_api_key:
            self.llm = ChatOpenAI(
                openai_api_key=self.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
                model="llama3-70b-8192",
                temperature=0.7
            )
            logger.info("BrowserSearch tool initialized with Groq provider")
        else:
            self.llm = None
            logger.warning("BrowserSearch tool initialized but no Groq API key is available")
            logger.info("Set GROQ_API_KEY environment variable to enable browser search")
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the browser search tool."""
        query = kwargs.get("query")
        if not query:
            return {"error": "Query parameter is required"}
        
        search_type = kwargs.get("search_type", "general")
        
        if not self.browser_use_available:
            return {"error": "browser-use package not available. Please install it with 'poetry add browser-use'"}
        
        if not self.groq_api_key or not self.llm:
            return {"error": "No Groq API key available. Please set GROQ_API_KEY environment variable"}
        
        try:
            # Customize task based on search type
            task = query
            if search_type == "price":
                task = f"Find the current price of {query}. Return only the current price, the percentage change in the last 24 hours, and the source of this information as a string."
            elif search_type == "trends":
                task = f"Find information about {query}. Return a list of the top 5 items with their percentage changes and a brief summary as a string."
            
            # Configure browser
            browser = Browser(
                config=BrowserConfig(
                    headless=True,
                    disable_security=True
                )
            )
            
            # Create browser context
            async with await browser.new_context(
                config=BrowserContextConfig(
                    browser_window_size=BrowserContextWindowSize(width=1280, height=1024)
                )
            ) as browser_context:
                # Initialize agent
                agent = Agent(
                    task=task,
                    llm=self.llm,
                    browser_context=browser_context,
                    use_vision=True  # Enable vision for financial data extraction
                )
                
                # Run the agent with timeout
                try:
                    history = await asyncio.wait_for(agent.run(max_steps=10), timeout=120)
                except asyncio.TimeoutError:
                    logger.warning("Browser search timed out after 120 seconds")
                    return {"error": "Browser search timed out. Please try a more specific query."}
                
                # Process results
                final_result = history.final_result()
                if final_result is None:
                    logger.warning(f"No results found for query: {query}")
                    return {"error": "No results found for the query"}
                
                # Ensure result is a string for Groq compatibility
                if not isinstance(final_result, str):
                    final_result = json.dumps(final_result) if isinstance(final_result, (dict, list)) else str(final_result)
                final_result = sanitize_log_message(final_result)
                
                logger.info(f"Successfully completed browser search for query: {query}")
                return {
                    "success": True,
                    "query": query,
                    "search_type": search_type,
                    "result": final_result,
                    "source": "browser-use web search"
                }
        
        except Exception as e:
            error_msg = sanitize_log_message(str(e))
            logger.error(f"Error in browser search: {error_msg}")
            return {"error": f"Browser search failed: {error_msg}"}
        finally:
            try:
                await browser.close()
            except Exception as e:
                logger.error(f"Error closing browser: {sanitize_log_message(str(e))}")

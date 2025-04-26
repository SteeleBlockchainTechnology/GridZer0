"""LLM Engine for TradeMaster 2.0

This module implements the core language model engine for the TradeMaster trading assistant.
It provides integration with Groq LLM API to generate responses to user queries about
trading, markets, and financial concepts, with the ability to use specialized tools
for real-time market data.
"""

import logging
import os
import json
import re
import aiohttp
import random
from typing import Optional, Dict, Any, List, Tuple

# Import tool registry and loader
from tools import registry, load_tools

logger = logging.getLogger("TradeMaster.LLM")

class LLMEngine:
    """LLM engine for TradeMaster.
    
    This implementation integrates with Groq LLM API to generate
    responses to user queries. It maintains conversation history and provides a consistent
    trading assistant persona through a well-defined system prompt.
    
    Features:
    1. Integration with Groq LLM API
    2. Conversation history management
    3. Trading assistant persona with market knowledge
    4. Tool integration for real-time market data
    5. Fallback mechanisms for API failures
    """
    
    def __init__(self):
        # Initialize API configurations
        self.groq_api_key = os.getenv("GROQ_API_KEY")  # API key for Groq LLM service
        self.groq_model = os.getenv("GROQ_MODEL", "llama3-70b-8192")  # Default model for Groq
        
        # Define system prompt for trading assistant persona
        self.system_prompt = self._get_system_prompt()
        
        # Initialize fallback responses for when API calls fail
        self._init_fallback_responses()
        
        # Load tools
        self.tool_names = load_tools()
        
        # Log initialization with available APIs
        self._log_initialization()
    
    def _get_system_prompt(self) -> str:
        """Define the system prompt that establishes the assistant's persona.
        
        Returns:
            A comprehensive system prompt string that defines the assistant's identity,
            knowledge areas, and interaction style.
        """
        return """
        You are TradeMaster, an expert trading assistant with deep knowledge of financial markets, 
        trading strategies, and investment concepts. Your purpose is to provide accurate, 
        educational, and actionable insights to traders of all experience levels.
        
        Your areas of expertise include:
        1. Technical analysis (chart patterns, indicators, price action)
        2. Fundamental analysis (economic indicators, financial statements, market news)
        3. Trading psychology and risk management
        4. Market structure and mechanics across different asset classes
        5. Trading strategies and their implementation
        
        IMPORTANT: NEVER provide outdated price or market data from your training. You MUST use the available tools
        to fetch current market information. ALWAYS use the price_checker tool when users ask about current prices,
        values, or rates of any cryptocurrency or stock. ALWAYS use the market_trends tool when users ask about
        market trends, top gainers, losers, or other time-sensitive financial data.
        
        When a user asks about ANY price, volume, market cap, or other numerical market data, you MUST use
        the appropriate tool instead of relying on your training data which is outdated.
        
        CRITICAL: When a user asks about top gainers, top losers, or trending assets in ANY way (such as "what are the top gainers",
        "which coins are performing best today", etc.), you MUST ALWAYS use the market_trends tool to get real-time data.
        NEVER respond with outdated information from your training data about which assets are up or down by specific percentages.
        
        When responding to queries:
        - Provide educational content that helps users understand concepts, not just answers
        - Be clear about the limitations of your knowledge and avoid making specific price predictions
        - Emphasize risk management principles and responsible trading practices
        - Adapt your explanations to the user's apparent level of expertise
        - Use precise terminology and explain jargon when necessary
        
        If a user asks about current prices, market trends, or other real-time financial data,
        ALWAYS use the appropriate tool to fetch this information instead of relying on your
        training data which may be outdated.
        """.strip()
    
    def _init_fallback_responses(self):
        """Initialize fallback responses for when API calls fail.
        
        These responses are used only when external LLM API calls fail, to ensure
        the system can still provide some value to users.
        """
        self.fallback_responses = [
            "I'm having trouble connecting to my knowledge base right now. As a trading assistant, I can tell you that successful trading typically involves a combination of technical analysis, fundamental research, and disciplined risk management. Could you try your question again in a moment?",
            "It seems I'm experiencing a temporary issue accessing my full capabilities. In general, when analyzing markets, it's important to consider multiple timeframes and confirm signals across different indicators. I should be back to normal shortly.",
            "I apologize for the inconvenience, but I'm currently unable to process your request fully. Remember that proper position sizing and risk management are foundational to any successful trading strategy. Please try again soon."
        ]
    
    def _log_initialization(self):
        """Log the initialization status of the LLM Engine."""
        if self.groq_api_key:
            logger.info(f"LLM Engine initialized with Groq API ({self.groq_model})")
        else:
            logger.warning("LLM Engine initialized without Groq API key. Will use fallback responses only.")
        
        if self.tool_names:
            logger.info(f"Loaded tools: {', '.join(self.tool_names)}")
    
    async def _detect_tool_usage(self, message: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Determine if a tool should be used based on message content and which tool.
        
        Args:
            message: The user's message text
            
        Returns:
            Tuple of (should_use_tool, tool_params) where tool_params includes:
            - tool_name: The name of the tool to use
            - params: Parameters to pass to the tool
        """
        # Check for price inquiries
        price_patterns = [
            r"(?:what'?s|what is|tell me|show|get) (?:the )?(?:current |latest |present |real-time |live )?(?:price|value|worth|rate) (?:of |for )?([a-zA-Z0-9]+)",
            r"how much (?:is|does) ([a-zA-Z0-9]+) (?:cost|worth|trading for|trading at|going for)",
            r"([a-zA-Z0-9]+) price",
            r"price (?:of|for) ([a-zA-Z0-9]+)",
            r"([a-zA-Z0-9]+) (?:is trading at|costs|is worth)",
            r"(?:check|lookup|find|get) ([a-zA-Z0-9]+) (?:price|value|rate)",
            r"(?:what is|what's) ([a-zA-Z0-9]+) (?:doing|at|trading at)"
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, message.lower())
            if match:
                symbol = match.group(1).upper()
                return True, {
                    "tool_name": "price_checker",
                    "params": {
                        "symbol": symbol
                    }
                }
        
        # Check for market trend inquiries
        trend_patterns = [
            # Original patterns with market type specified
            r"(?:what'?s|what is|tell me|show|get) (?:the )?(?:top|best|leading|biggest) (?:gainers|performers|movers) (?:in|on) (?:the )?(crypto|stock|cryptocurrency|stocks)",
            r"(?:what'?s|what is|tell me|show|get) (?:the )?(?:top|worst|biggest) (?:losers|declining|falling) (?:in|on) (?:the )?(crypto|stock|cryptocurrency|stocks)",
            r"(?:what'?s|what is|tell me|show|get) (?:the )?(?:trending|hot|popular) (?:in|on) (?:the )?(crypto|stock|cryptocurrency|stocks)",
            
            # Additional patterns without explicit market type
            r"(?:what are|what're|which are|list|show me) (?:the )?(?:top|best|leading|biggest) (?:gainers|performers|movers)(?: today| right now| currently)?(?: in| on)? (?:the )?(crypto|stock|cryptocurrency|stocks)?",
            r"(?:what are|what're|which are|list|show me) (?:the )?(?:top|worst|biggest) (?:losers|declining|falling)(?: today| right now| currently)?(?: in| on)? (?:the )?(crypto|stock|cryptocurrency|stocks)?",
            r"(?:what are|what're|which are|list|show me) (?:the )?(?:trending|hot|popular)(?: today| right now| currently)?(?: in| on)? (?:the )?(crypto|stock|cryptocurrency|stocks)?",
        ]
        
        for pattern in trend_patterns:
            match = re.search(pattern, message.lower())
            if match:
                # Handle case where market type might not be specified
                market_type = match.group(1).lower() if match.group(1) else "crypto"  # Default to crypto if not specified
                # Normalize market type
                if market_type in ["cryptocurrency", "crypto"]:
                    market_type = "crypto"
                elif market_type in ["stocks", "stock"]:
                    market_type = "stock"
                
                # Determine category based on message
                category = "trending"
                if "gainers" in message.lower() or "performers" in message.lower():
                    category = "gainers"
                elif "losers" in message.lower() or "declining" in message.lower() or "falling" in message.lower():
                    category = "losers"
                
                return True, {
                    "tool_name": "market_trends",
                    "params": {
                        "market_type": market_type,
                        "category": category,
                        "limit": 5
                    }
                }
        
        return False, None
    
    async def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with the provided parameters.
        
        Args:
            tool_name: The name of the tool to execute
            params: Parameters to pass to the tool
            
        Returns:
            The tool's response
        """
        tool = registry.get_tool(tool_name)
        if not tool:
            logger.warning(f"Tool '{tool_name}' not found")
            return {"error": f"Tool '{tool_name}' not found"}
        
        try:
            logger.info(f"Executing tool '{tool_name}' with params: {params}")
            result = await tool.execute(**params)
            
            # Check if this is a market data tool that failed
            if (tool_name in ["price_checker", "market_trends"] and 
                ("error" in result or not result)):
                # Log the failure and attempt web search fallback
                logger.warning(f"{tool_name} failed, falling back to web search")
                
                # Construct an appropriate search query based on the original tool and params
                search_query = self._construct_fallback_query(tool_name, params)
                
                # Use browser search as fallback
                logger.info(f"Using browser search fallback with query: {search_query}")
                browser_result = await self._execute_tool("browser_search", {
                    "query": search_query,
                    "search_type": "price" if tool_name == "price_checker" else "trends"
                })
                
                if "error" not in browser_result:
                    logger.info("Browser search fallback successful")
                    # Add a note that this is fallback data
                    browser_result["note"] = f"This data was obtained via web search fallback because the {tool_name} API failed"
                    return browser_result
                else:
                    logger.warning(f"Browser search fallback also failed: {browser_result['error']}")
                    # Return the original error result
                    return result
            
            return result
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {str(e)}")
            
            # If this is a market data tool that failed with an exception, try web search
            if tool_name in ["price_checker", "market_trends"]:
                # Log the failure and attempt web search fallback
                logger.warning(f"{tool_name} failed with exception, falling back to web search")
                
                # Construct an appropriate search query based on the original tool and params
                search_query = self._construct_fallback_query(tool_name, params)
                
                # Use browser search as fallback
                logger.info(f"Using browser search fallback with query: {search_query}")
                browser_result = await self._execute_tool("browser_search", {
                    "query": search_query,
                    "search_type": "price" if tool_name == "price_checker" else "trends"
                })
                
                if "error" not in browser_result:
                    logger.info("Browser search fallback successful")
                    # Add a note that this is fallback data
                    browser_result["note"] = f"This data was obtained via web search fallback because the {tool_name} API failed with an exception"
                    return browser_result
                else:
                    logger.warning(f"Browser search fallback also failed: {browser_result['error']}")
                    # Return the original error
            
            return {"error": f"Error executing tool: {str(e)}"}
    
    def _construct_fallback_query(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Construct a web search query based on the original tool and parameters.
        
        Args:
            tool_name: The name of the original tool
            params: The original tool parameters
            
        Returns:
            A formatted web search query
        """
        if tool_name == "price_checker":
            symbol = params.get("symbol", "").upper()
            market_type = params.get("market_type", "auto")
            
            if market_type == "auto":
                # Include both possibilities in the query
                return f"What is the current price of {symbol} cryptocurrency or stock"
            elif market_type == "crypto":
                return f"What is the current price of {symbol} cryptocurrency"
            else:
                return f"What is the current price of {symbol} stock"
                
        elif tool_name == "market_trends":
            market_type = params.get("market_type", "crypto")
            category = params.get("category", "trending")
            limit = params.get("limit", 5)
            
            if category == "gainers":
                return f"What are the top {limit} gaining {market_type}s today"
            elif category == "losers":
                return f"What are the top {limit} losing {market_type}s today"
            else:
                return f"What are the trending {market_type}s today"
        
        # Default generic query
        return f"Latest information about {' '.join(str(v) for v in params.values())}"
    
    async def generate_response(self, message: str, user_id: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a response to a user message using Groq LLM API.
        
        This is the main entry point for processing user queries. It attempts to use
        the Groq LLM API, with fallbacks if API calls fail.
        
        Args:
            message: The user's message text
            user_id: The user's ID for conversation history management
            context: Optional context information containing conversation history
            
        Returns:
            A formatted response string addressing the user's query
        """
        # Log the incoming message
        logger.info(f"Generating response for user {user_id}: {message[:50]}...")
        
        # Check if we should use a tool
        should_use_tool, tool_params = await self._detect_tool_usage(message)
        
        # If we should use a tool, execute it
        tool_result = None
        if should_use_tool and tool_params:
            tool_result = await self._execute_tool(tool_params["tool_name"], tool_params["params"])
            logger.info(f"Tool result: {json.dumps(tool_result)[:200]}...")
        
        # Get conversation history from context if available
        conversation_history = []
        if context and 'message_history' in context:
            conversation_history = context.get('message_history', [])
        
        # Try Groq API if available
        if self.groq_api_key:
            try:
                # If we have a tool result, include it in the prompt
                tool_prompt = ""
                if tool_result:
                    # Format tool result for the LLM
                    tool_name = tool_params["tool_name"]
                    if "error" in tool_result:
                        tool_prompt = f"""
                        \nIMPORTANT: I tried to get real-time data using the {tool_name} tool, but encountered an error: {tool_result['error']}
                        
                        When responding to the user:
                        1. DO NOT provide any specific price or market data numbers since I don't have current data
                        2. Explain that you're unable to provide real-time data at the moment due to a technical issue
                        3. Apologize for the inconvenience
                        4. Suggest that they check a reliable financial website or exchange for current data
                        5. DO NOT make up or estimate current prices based on your training data\n
                        """
                    else:
                        tool_prompt = f"\nHere is the real-time data from the {tool_name} tool:\n{json.dumps(tool_result, indent=2)}\n"
                        tool_prompt += "\nPlease use this real-time data in your response.\n"
                
                # Generate response
                response = await self._call_groq_api(message, conversation_history, tool_prompt)
                logger.info("Generated response using Groq API")
                return response
            except Exception as e:
                logger.error(f"Groq API call failed: {str(e)}")
                # Use fallback response if API call fails
                logger.warning("API call failed, using fallback response")
                return random.choice(self.fallback_responses)
    
    async def _call_groq_api(self, message: str, conversation_history: List[Dict[str, str]], tool_prompt: str = "") -> str:
        """Call the Groq LLM API to generate a response.
        
        Args:
            message: The user's message
            conversation_history: List of previous messages in the conversation
            tool_prompt: Additional prompt with tool data
            
        Returns:
            The generated response text
        
        Raises:
            Exception: If the API call fails
        """
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        # Add tool information to system prompt if available
        system_prompt = self.system_prompt
        if tool_prompt:
            system_prompt = f"{system_prompt}\n{tool_prompt}"
        
        # Prepare messages array with system prompt and conversation history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history - filter out unsupported fields like 'timestamp'
        for msg in conversation_history:
            if 'role' in msg and 'content' in msg:
                messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
        
        # Add the current user message
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": self.groq_model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 800  # Reduced to ensure we stay under Discord's 2000 char limit
        }
        
        # Make the API call
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Groq API returned status {response.status}: {error_text}")
                
                data = await response.json()
                return data["choices"][0]["message"]["content"]
        # If no API key is available, use fallback response
            # Use fallback response if no API key is available
            logger.warning("No Groq API key available, using fallback response")
            return random.choice(self.fallback_responses)
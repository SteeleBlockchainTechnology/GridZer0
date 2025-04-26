"""
Market Trends Tool for TradeMaster 2.0

This tool retrieves market trend data and top movers for both
stock and cryptocurrency markets.
"""

import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_tool import BaseTool
import aiohttp
import json
import os
from typing import Tuple

logger = logging.getLogger("TradeMaster.Tools.MarketTrends")

class MarketTrendsTool(BaseTool):
    """
    Tool for getting market trends, top gainers, and top losers.
    
    This tool provides access to real-time market trend data, including:
    - Top gaining assets (biggest price increases)
    - Top losing assets (biggest price decreases)
    - Currently trending assets (most popular/discussed)
    
    It supports both cryptocurrency and stock markets through integration with:
    - CoinGecko API for cryptocurrency trends, gainers, and losers
    - Alpha Vantage API for stock market trends, gainers, and losers
    
    The tool implements fallback mechanisms similar to the PriceCheckerTool:
    - Attempts Pro API access first when API keys are available
    - Falls back to public/free endpoints when Pro calls fail
    
    This tool is particularly useful for providing users with current market
    sentiment and highlighting notable market movements, which is essential
    for traders making decisions based on market momentum.
    """
    
    @property
    def name(self) -> str:
        return "market_trends"
    
    @property
    def description(self) -> str:
        return "Gets market trends, top gainers, and top losers for crypto or stocks"
    
    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "market_type",
                "type": "string",
                "description": "The market type: 'crypto' or 'stock'",
                "required": True
            },
            {
                "name": "category",
                "type": "string",
                "description": "Category to retrieve: 'gainers', 'losers', or 'trending'",
                "required": False,
                "default": "trending"
            },
            {
                "name": "limit",
                "type": "number",
                "description": "Number of results to return (1-25)",
                "required": False,
                "default": 5
            }
        ]
    
    @property
    def examples(self) -> List[str]:
        return [
            "market_trends market_type=crypto",
            "market_trends market_type=stock category=gainers",
            "market_trends market_type=crypto category=losers limit=10"
        ]
    
    # API Base URLs
    COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
    COINGECKO_PRO_BASE_URL = "https://pro-api.coingecko.com/api/v3"
    ALPHAVANTAGE_BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self):
        """Initialize the market trends tool with API keys."""
        self.coingecko_api_key = os.getenv("COINGECKO_API_KEY")
        self.alphavantage_api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        logger.info("MarketTrends tool initialized")
    
    def sanitize_api_key(self, value: str, mask: bool = True) -> str:
        """Sanitize an API key for logging by showing only part of it."""
        if not value or not mask:
            return value
        
        if len(value) <= 8:
            return "***" + value[-2:] if len(value) > 2 else "***"
        else:
            return value[:4] + "..." + value[-4:]
    
    async def make_api_request(self, url: str, headers: Dict[str, str] = None, 
                             params: Dict[str, Any] = None) -> Tuple[bool, Dict[str, Any]]:
        """Make an API request and handle common error cases."""
        if not headers:
            headers = {}
        
        if not params:
            params = {}
        
        # Create a sanitized version of the headers for logging (to avoid exposing API keys)
        log_headers = {}
        for key, value in headers.items():
            if "api-key" in key.lower() or "apikey" in key.lower() or "key" in key.lower():
                log_headers[key] = self.sanitize_api_key(value)
            else:
                log_headers[key] = value
        
        try:
            # Log the full request details at debug level
            logger.info(f"Making API request to: {url}")
            logger.info(f"Headers: {log_headers}")
            logger.info(f"Params: {params}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    response_text = await response.text()
                    
                    logger.info(f"Response status: {response.status}")
                    logger.info(f"Response headers: {dict(response.headers)}")
                    
                    # Log a preview of the response body
                    preview = response_text[:500] + "..." if len(response_text) > 500 else response_text
                    logger.info(f"Response body preview: {preview}")
                    
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status} - {url}")
                        
                        # Try to get more details from the response
                        error_message = f"Status {response.status}"
                        try:
                            error_data = json.loads(response_text)
                            if isinstance(error_data, dict):
                                # Look for common error fields
                                for field in ['message', 'error', 'error_message', 'status', 'detail']:
                                    if field in error_data:
                                        error_message = f"{error_message}: {error_data[field]}"
                                        break
                        except:
                            error_message = f"API request failed with status {response.status}: {response_text[:200]}"
                        
                        return False, {"error": error_message, "status": response.status}
                    
                    try:
                        data = json.loads(response_text)
                        return True, data
                    except Exception as e:
                        logger.error(f"Error parsing JSON response: {e}")
                        logger.error(f"Response text: {response_text[:500]}")
                        return False, {"error": f"Error parsing response: {str(e)}"}
        
        except aiohttp.ClientError as e:
            logger.error(f"API connection error: {e} - {url}")
            return False, {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error in API request: {e} - {url}")
            return False, {"error": f"Unexpected error: {str(e)}"}
    
    def get_coingecko_url(self, endpoint: str, use_pro: bool = True) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
        """Get the appropriate CoinGecko URL, headers, and params."""
        api_key = self.coingecko_api_key
        params = {}
        
        # Ensure no leading slash in endpoint
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
        
        if api_key and use_pro:
            base_url = self.COINGECKO_PRO_BASE_URL
            # For Pro API, the key should be in the x-cg-pro-api-key header
            headers = {"x-cg-pro-api-key": api_key}
            logger.info(f"Using CoinGecko Pro API for endpoint: {endpoint}")
            logger.info(f"API Key (partial): {self.sanitize_api_key(api_key)}")
        else:
            base_url = self.COINGECKO_BASE_URL
            headers = {}
            logger.info(f"Using CoinGecko Public API for endpoint: {endpoint}")
        
        return f"{base_url}/{endpoint}", headers, params
    
    def get_alphavantage_params(self, function: str, symbol: str, **kwargs) -> Dict[str, str]:
        """Get parameters for Alpha Vantage API calls."""
        api_key = self.alphavantage_api_key
        if not api_key:
            logger.warning("Alpha Vantage API key not configured")
        
        params = {
            "function": function,
            "symbol": symbol,
            "apikey": api_key
        }
        
        # Add any additional parameters
        params.update(kwargs)
        
        return params
    
    def format_error_response(self, symbol: str, error_msg: str) -> Dict[str, Any]:
        """Format a standardized error response."""
        return {
            "error": f"Failed to get data for {symbol}: {error_msg}",
            "symbol": symbol,
            "success": False
        }
    
    async def _get_crypto_trends(self, category: str, limit: int) -> Dict[str, Any]:
        """
        Get cryptocurrency trends from CoinGecko.
        
        This method retrieves trend data for cryptocurrencies based on the specified category.
        It handles three different types of trend data:
        - 'trending': Currently popular cryptocurrencies based on user interest
        - 'gainers': Cryptocurrencies with the highest positive price change
        - 'losers': Cryptocurrencies with the highest negative price change
        
        The method implements a fallback mechanism:
        1. First attempts to use the CoinGecko Pro API if an API key is available
        2. Falls back to the public API if the Pro API fails or is unavailable
        3. Uses different endpoints based on the requested category
        
        For trending coins, it uses the 'search/trending' endpoint.
        For gainers/losers, it fetches market data and sorts it accordingly.
        
        Args:
            category: The category to retrieve ('gainers', 'losers', or 'trending')
            limit: Maximum number of results to return (capped at 25)
            
        Returns:
            Dictionary with formatted trend information including results array
        """
        # Ensure limit is reasonable
        limit = max(1, min(25, limit))
        
        # For trending coins
        if category == "trending":
            # Try Pro API first if available
            if self.coingecko_api_key:
                # Get appropriate URL and headers
                url, headers, params = self.get_coingecko_url("search/trending", use_pro=True)
                
                # Make API request
                success, data = await self.make_api_request(url, headers, params)
                
                if success:
                    # Extract trending coins
                    return self._process_trending_coins(data, limit)
                
                # Log failure but continue to fallback
                logger.warning(f"CoinGecko Pro API failed for trending, trying public API: {data.get('error', 'Unknown error')}")
            
            # Fallback to public API
            url, headers, params = self.get_coingecko_url("search/trending", use_pro=False)
            
            # Make API request
            success, data = await self.make_api_request(url, headers, params)
            
            if not success:
                return data  # Error response is already formatted
            
            # Process trending coins
            return self._process_trending_coins(data, limit)
        
        # For gainers and losers
        else:
            # Try Pro API first if available
            if self.coingecko_api_key:
                # Get appropriate URL and headers
                url, headers, params = self.get_coingecko_url("coins/markets", use_pro=True)
                
                # Add query parameters
                params.update({
                    "vs_currency": "usd",
                    "order": "market_cap_desc" if category == "trending" else "price_change_percentage_24h_desc" if category == "gainers" else "price_change_percentage_24h_asc",
                    "per_page": 250,  # Get a good sample to find gainers/losers
                    "page": 1,
                    "sparkline": "false",
                    "price_change_percentage": "24h"
                })
                
                # Make API request
                success, data = await self.make_api_request(url, headers, params)
                
                if success:
                    # Process markets data
                    return self._process_markets_data(data, category, limit)
                
                # Log failure but continue to fallback
                logger.warning(f"CoinGecko Pro API failed for {category}, trying public API: {data.get('error', 'Unknown error')}")
            
            # Fallback to public API
            url, headers, params = self.get_coingecko_url("coins/markets", use_pro=False)
            
            # Add query parameters
            params.update({
                "vs_currency": "usd",
                "order": "market_cap_desc" if category == "trending" else "price_change_percentage_24h_desc" if category == "gainers" else "price_change_percentage_24h_asc",
                "per_page": 250,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "24h"
            })
            
            # Make API request
            success, data = await self.make_api_request(url, headers, params)
            
            if not success:
                return data  # Error response is already formatted
            
            # Process markets data
            return self._process_markets_data(data, category, limit)
    
    def _process_trending_coins(self, data: Dict[str, Any], limit: int) -> Dict[str, Any]:
        """Process trending coins data from CoinGecko response."""
        # Extract trending coins
        trending_coins = data.get("coins", [])
        
        # Format results
        results = []
        for i, coin_data in enumerate(trending_coins[:limit]):
            coin = coin_data.get("item", {})
            results.append({
                "rank": i + 1,
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name", "Unknown"),
                "market_cap_rank": coin.get("market_cap_rank"),
                "price_btc": coin.get("price_btc"),
                "id": coin.get("id")
            })
        
        return {
            "category": "trending",
            "market_type": "crypto",
            "results": results,
            "time": datetime.now().isoformat(),
            "source": "CoinGecko"
        }
    
    def _process_markets_data(self, data: List[Dict[str, Any]], category: str, limit: int) -> Dict[str, Any]:
        """Process market data for gainers/losers from CoinGecko response."""
        # Filter out entries with None price_change_percentage_24h
        filtered_data = [item for item in data if item.get("price_change_percentage_24h") is not None]
        
        # The data should already be sorted by the API based on our 'order' parameter
        # but we'll sort it again just to be sure
        if category == "gainers":
            sorted_data = sorted(filtered_data, key=lambda x: x.get("price_change_percentage_24h", 0), reverse=True)
        else:  # losers
            sorted_data = sorted(filtered_data, key=lambda x: x.get("price_change_percentage_24h", 0))
        
        # Format results
        results = []
        for i, coin in enumerate(sorted_data[:limit]):
            results.append({
                "rank": i + 1,
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name", "Unknown"),
                "price_usd": coin.get("current_price"),
                "price_change_24h": coin.get("price_change_24h"),
                "price_change_percentage_24h": coin.get("price_change_percentage_24h"),
                "market_cap": coin.get("market_cap"),
                "volume_24h": coin.get("total_volume")
            })
        
        return {
            "category": category,
            "market_type": "crypto",
            "results": results,
            "time": datetime.now().isoformat(),
            "source": "CoinGecko"
        }
    
    async def _get_stock_trends(self, category: str, limit: int) -> Dict[str, Any]:
        """
        Get stock market trends from Alpha Vantage.
        
        Args:
            category: The category to retrieve ('gainers', 'losers', or 'trending')
            limit: Maximum number of results to return
            
        Returns:
            Dictionary with trend information
        """
        if not self.alphavantage_api_key:
            logger.error("Alpha Vantage API key not found")
            return format_error_response("market_trends", "Alpha Vantage API key not configured")
        
        # Ensure limit is reasonable
        limit = max(1, min(25, limit))
        
        # Map category to Alpha Vantage function
        function = "TOP_GAINERS_LOSERS"
        
        # Make API request
        url = "https://www.alphavantage.co/query"
        params = {"function": function, "apikey": self.alphavantage_api_key}
        success, data = await self.make_api_request(url, {}, params)
        
        if not success:
            return data  # Error response is already formatted
        
        # Check for API errors or empty responses
        if "Error Message" in data:
            return self.format_error_response("market_trends", data["Error Message"])
        
        # Extract the appropriate category
        if category == "gainers":
            category_data = data.get("top_gainers", [])
        elif category == "losers":
            category_data = data.get("top_losers", [])
        else:  # trending - use most active
            category_data = data.get("most_actively_traded", [])
        
        if not category_data:
            return self.format_error_response("market_trends", f"No {category} data available")
        
        # Format results
        results = []
        for i, stock in enumerate(category_data[:limit]):
            change_percent = stock.get("change_percentage", "0%").replace("%", "")
            try:
                change_percent_float = float(change_percent)
            except:
                change_percent_float = 0.0
                
            results.append({
                "rank": i + 1,
                "symbol": stock.get("ticker", ""),
                "price_usd": float(stock.get("price", 0)),
                "change_amount": float(stock.get("change_amount", 0)),
                "change_percentage": change_percent_float,
                "volume": int(stock.get("volume", 0))
            })
        
        return {
            "category": category,
            "market_type": "stock",
            "results": results,
            "time": datetime.now().isoformat(),
            "source": "Alpha Vantage"
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the market trends tool.
        
        Args:
            market_type: The market type ('crypto' or 'stock')
            category: Category to retrieve ('gainers', 'losers', or 'trending')
            limit: Number of results to return (1-25)
            
        Returns:
            Dictionary with trend information
        """
        market_type = kwargs.get("market_type")
        if not market_type:
            return {"error": "market_type parameter is required"}
        
        category = kwargs.get("category", "trending")
        limit = int(kwargs.get("limit", 5))
        
        # Validate category
        valid_categories = ["gainers", "losers", "trending"]
        if category not in valid_categories:
            return {"error": f"Invalid category: {category}. Valid categories: {', '.join(valid_categories)}"}
        
        logger.info(f"Getting {category} for {market_type} market (limit: {limit})")
        
        # Get trends based on market type
        if market_type.lower() == "crypto":
            return await self._get_crypto_trends(category, limit)
        elif market_type.lower() == "stock":
            return await self._get_stock_trends(category, limit)
        else:
            return {"error": f"Invalid market type: {market_type}. Use 'crypto' or 'stock'"}
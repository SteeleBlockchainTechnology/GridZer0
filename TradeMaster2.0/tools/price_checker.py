"""Market Price Checker Tool for TradeMaster 2.0

This tool retrieves current price information for stocks and cryptocurrencies.
It uses both CoinGecko for crypto prices and Alpha Vantage for stock prices,
with fallback options when primary sources fail.
"""

import logging
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import aiohttp
import json

from .base_tool import BaseTool

logger = logging.getLogger("TradeMaster.Tools.PriceChecker")

class PriceCheckerTool(BaseTool):
    """Tool for checking current market prices of stocks and cryptocurrencies."""
    
    # API Base URLs
    COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
    COINGECKO_PRO_BASE_URL = "https://pro-api.coingecko.com/api/v3"
    ALPHAVANTAGE_BASE_URL = "https://www.alphavantage.co/query"
    
    @property
    def name(self) -> str:
        return "price_checker"
    
    @property
    def description(self) -> str:
        return "Checks current prices of stocks and cryptocurrencies"
    
    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "symbol",
                "type": "string",
                "description": "The symbol to check (e.g. BTC, ETH, AAPL, MSFT)",
                "required": True
            },
            {
                "name": "market_type",
                "type": "string",
                "description": "The market type: 'crypto' or 'stock'",
                "required": False,
                "default": "auto"  # Auto-detect based on symbol
            }
        ]
    
    @property
    def examples(self) -> List[str]:
        return [
            "price_checker symbol=BTC",
            "price_checker symbol=AAPL market_type=stock",
            "price_checker symbol=ETH market_type=crypto"
        ]
    
    def __init__(self):
        """Initialize the price checker tool with API keys."""
        self.coingecko_api_key = os.getenv("COINGECKO_API_KEY")
        self.alphavantage_api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        
        # Market type detection data
        self.common_stocks = {
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM",
            "V", "JNJ", "WMT", "PG", "MA", "UNH", "HD", "BAC", "XOM", "DIS",
            "PYPL", "INTC", "CMCSA", "NFLX", "CSCO", "ADBE", "CRM", "VZ"
        }
        
        self.common_cryptos = {
            "BTC", "ETH", "BNB", "XRP", "SOL", "ADA", "AVAX", "DOT", "DOGE",
            "MATIC", "LINK", "UNI", "LTC", "BCH", "ATOM", "XLM", "ALGO", "NEAR"
        }
        
        self.coingecko_ids = {
            "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
            "SOL": "solana", "XRP": "ripple", "ADA": "cardano",
            "AVAX": "avalanche-2", "DOT": "polkadot", "DOGE": "dogecoin",
            "MATIC": "matic-network", "LINK": "chainlink", "UNI": "uniswap",
            "LTC": "litecoin", "BCH": "bitcoin-cash", "ATOM": "cosmos",
            "XLM": "stellar", "ALGO": "algorand", "NEAR": "near"
        }
        
        logger.info("PriceChecker tool initialized")
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the price checker tool."""
        symbol = kwargs.get("symbol")
        if not symbol:
            return {"error": "Symbol parameter is required"}
        
        market_type = kwargs.get("market_type", "auto")
        
        # Auto-detect market type if set to "auto"
        if market_type == "auto":
            market_type = self._detect_market_type(symbol)
        
        logger.info(f"Checking price for {symbol} as {market_type}")
        
        # Get price based on market type
        if market_type.lower() == "crypto":
            return await self._get_crypto_price(symbol)
        elif market_type.lower() == "stock":
            return await self._get_stock_price(symbol)
        else:
            return {"error": f"Invalid market type: {market_type}. Use 'crypto' or 'stock'"}
    
    def _detect_market_type(self, symbol: str) -> str:
        """Auto-detect whether a symbol is for crypto or stock."""
        symbol_upper = symbol.upper()
        
        # Check common lists first
        if symbol_upper in self.common_cryptos:
            return "crypto"
        if symbol_upper in self.common_stocks:
            return "stock"
        
        # If not in common lists, use heuristics
        return "crypto" if len(symbol) <= 4 and symbol.isalpha() else "stock"
    
    async def make_api_request(self, url: str, headers: Dict[str, str] = None, 
                             params: Dict[str, Any] = None) -> Tuple[bool, Dict[str, Any]]:
        """Make an API request and handle common error cases."""
        headers = headers or {}
        params = params or {}
        
        try:
            logger.info(f"Making API request to: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    response_text = await response.text()
                    
                    if response.status != 200:
                        error_message = f"Status {response.status}"
                        try:
                            error_data = json.loads(response_text)
                            if isinstance(error_data, dict):
                                for field in ['message', 'error', 'error_message', 'status', 'detail']:
                                    if field in error_data:
                                        error_message = f"{error_message}: {error_data[field]}"
                                        break
                        except:
                            error_message = f"API request failed with status {response.status}"
                        
                        return False, {"error": error_message, "status": response.status}
                    
                    try:
                        data = json.loads(response_text)
                        return True, data
                    except Exception as e:
                        logger.error(f"Error parsing JSON response: {e}")
                        return False, {"error": f"Error parsing response: {str(e)}"}
        
        except aiohttp.ClientError as e:
            logger.error(f"API connection error: {e} - {url}")
            return False, {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error in API request: {e} - {url}")
            return False, {"error": f"Unexpected error: {str(e)}"}
    
    def format_error_response(self, symbol: str, error_msg: str) -> Dict[str, Any]:
        """Format a standardized error response."""
        return {
            "error": f"Failed to get data for {symbol}: {error_msg}",
            "symbol": symbol,
            "success": False
        }
    
    async def _get_crypto_price(self, symbol: str) -> Dict[str, Any]:
        """Get cryptocurrency price from CoinGecko with fallback."""
        symbol_upper = symbol.upper()
        coin_id = self.coingecko_ids.get(symbol_upper, symbol.lower())
        
        # Try simple price endpoint first
        result = await self._try_crypto_endpoint("simple/price", coin_id, symbol_upper)
        if "error" not in result:
            return result
            
        # Fall back to detailed endpoint
        return await self._try_crypto_endpoint(f"coins/{coin_id}", coin_id, symbol_upper, detailed=True)
    
    async def _try_crypto_endpoint(self, endpoint: str, coin_id: str, symbol: str, detailed: bool = False) -> Dict[str, Any]:
        """Try a CoinGecko endpoint with Pro API first, then fall back to public API."""
        # Try Pro API first if key available
        if self.coingecko_api_key:
            result = await self._make_coingecko_request(endpoint, coin_id, symbol, True, detailed)
            if "error" not in result:
                return result
        
        # Fall back to public API
        return await self._make_coingecko_request(endpoint, coin_id, symbol, False, detailed)
        
    def _process_simple_coingecko_data(self, coin_data: Dict[str, Any], symbol: str, 
                                     coin_id: str, source: str) -> Dict[str, Any]:
        """Process data from CoinGecko simple/price endpoint."""
        return {
            "symbol": symbol,
            "name": self.coingecko_ids.get(symbol, coin_id).capitalize(),
            "price_usd": coin_data.get("usd"),
            "price_change_24h": coin_data.get("usd_24h_change"),
            "market_cap": coin_data.get("usd_market_cap"),
            "volume_24h": coin_data.get("usd_24h_vol"),
            "time": datetime.now().isoformat(),
            "source": source
        }
    
    def _process_detailed_coingecko_data(self, data: Dict[str, Any], symbol: str, source: str) -> Dict[str, Any]:
        """Process data from CoinGecko coins/{id} endpoint."""
        market_data = data.get("market_data", {})
        return {
            "symbol": symbol,
            "name": data.get("name", "Unknown"),
            "price_usd": market_data.get("current_price", {}).get("usd"),
            "price_change_24h": market_data.get("price_change_percentage_24h"),
            "market_cap": market_data.get("market_cap", {}).get("usd"),
            "volume_24h": market_data.get("total_volume", {}).get("usd"),
            "time": datetime.now().isoformat(),
            "source": source
        }
    
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
        
    def sanitize_api_key(self, value: str, mask: bool = True) -> str:
        """Sanitize an API key for logging by showing only part of it."""
        if not value or not mask:
            return value
        
        if len(value) <= 8:
            return "***" + value[-2:] if len(value) > 2 else "***"
        else:
            return value[:4] + "..." + value[-4:]
    
    async def _make_coingecko_request(self, endpoint: str, coin_id: str, symbol: str, 
                                   use_pro: bool = False, detailed: bool = False) -> Dict[str, Any]:
        """Make a request to the CoinGecko API with appropriate parameters."""
        if endpoint.startswith('simple/price'):
            # For simple price endpoint
            url, headers, params = self.get_coingecko_url(endpoint, use_pro)
            params.update({
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_24hr_change": "true"
            })
            
            # Make API request
            source = "CoinGecko Pro" if use_pro else "CoinGecko"
            logger.info(f"Getting {symbol} price from {source} simple/price endpoint")
            success, data = await self.make_api_request(url, headers, params)
            
            if not success:
                return data  # Error response is already formatted
            
            # Check if we have data for the requested coin
            if coin_id not in data:
                return self.format_error_response(symbol, "Symbol not found")
            
            # Process and format the data
            return self._process_simple_coingecko_data(data[coin_id], symbol, coin_id, source)
            
        elif endpoint.startswith('coins/'):
            # For detailed coin endpoint
            url, headers, params = self.get_coingecko_url(endpoint, use_pro)
            
            # Make API request
            source = "CoinGecko Pro" if use_pro else "CoinGecko"
            logger.info(f"Getting {symbol} price from {source} detailed endpoint")
            success, data = await self.make_api_request(url, headers, params)
            
            if not success:
                return data  # Error response is already formatted
            
            # Check if we have the expected data structure
            if "id" not in data:
                return self.format_error_response(symbol, "Invalid response data structure")
            
            # Process and format the data
            return self._process_detailed_coingecko_data(data, symbol, source)
        
        else:
            return self.format_error_response(symbol, f"Unsupported endpoint: {endpoint}")
            
    async def _get_stock_price(self, symbol: str) -> Dict[str, Any]:
        """Get stock price from Alpha Vantage API."""
        if not self.alphavantage_api_key:
            return self.format_error_response(symbol, "Alpha Vantage API key not configured")
        
        url = self.ALPHAVANTAGE_BASE_URL
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.alphavantage_api_key
        }
        
        logger.info(f"Getting {symbol} price from Alpha Vantage")
        success, data = await self.make_api_request(url, params=params)
        
        if not success:
            return data  # Error response is already formatted
        
        # Check if we have the expected data structure
        if "Global Quote" not in data or not data["Global Quote"]:
            return self.format_error_response(symbol, "Symbol not found or invalid response")
        
        quote = data["Global Quote"]
        
        # Process and format the data
        return {
            "symbol": symbol,
            "name": symbol,  # Alpha Vantage doesn't provide name in this endpoint
            "price_usd": float(quote.get("05. price", 0)),
            "price_change_24h": float(quote.get("10. change percent", "0%").replace("%", "")),
            "market_cap": None,  # Not provided in this endpoint
            "volume_24h": float(quote.get("06. volume", 0)),
            "time": datetime.now().isoformat(),
            "source": "Alpha Vantage"
        }
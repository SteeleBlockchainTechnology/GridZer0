#!/usr/bin/env python3
"""
TradeMaster 2.0 - Discord Trading Assistant Bot
Entry point for the bot application.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import logging
import os
import discord
from dotenv import load_dotenv

# Import bot client
from bot.client import TradeMasterClient
from utils.logging import setup_logging

# Set up logging with more detailed configuration
logger = setup_logging()

# Log Python version and environment info
logger.info(f"Python version: {sys.version}")
logger.info(f"Discord.py version: {discord.__version__ if 'discord' in sys.modules else 'Not loaded yet'}")
logger.info(f"Running from: {os.path.abspath('.')}")

# Load environment variables
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", ".env")
if os.path.exists(config_path):
    load_dotenv(config_path)
else:
    # If .env doesn't exist yet, try to find sample.env
    sample_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "sample.env")
    if os.path.exists(sample_path):
        load_dotenv(sample_path)
        logger.warning("Using sample.env for configuration. Create a .env file with your actual credentials.")
    else:
        logger.warning("No .env or sample.env found. Make sure to set up your environment variables.")

TOKEN = os.getenv("DISCORD_TOKEN")

async def main():
    """Main entry point for the TradeMaster bot."""
    # Validate token
    if not TOKEN:
        logger.critical("Discord token not found! Check your .env file.")
        return

    # Initialize the bot client
    client = TradeMasterClient()
    
    try:
        logger.info("Starting TradeMaster Discord bot...")
        await client.start(TOKEN)
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())
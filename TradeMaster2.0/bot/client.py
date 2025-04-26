"""
TradeMaster 2.0 Discord Client
Handles Discord events and interactions.
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
import re

# Fix imports by using the "sys.path" approach
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import from core directly
from core.llm import LLMEngine
from core.context import ContextManager

# Set up logger for this module
logger = logging.getLogger("TradeMaster.Client")

class TradeMasterClient(commands.Bot):
    """Main Discord bot client for TradeMaster."""
    
    def __init__(self):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        # Initialize bot with command prefix
        super().__init__(
            command_prefix="!",  # Traditional prefix for fallback
            intents=intents,
            help_command=None  # Disable default help command
        )
        
        # Initialize components
        self.context_manager = ContextManager()
        self.llm_engine = LLMEngine()
        
        # Discord message limit (characters)
        self.discord_message_limit = 2000
        
        logger.info("TradeMaster client initialized")
    
    async def setup_hook(self):
        """Register slash commands when the bot is being set up."""
        # Load commands from bot/commands.py
        from bot.commands import setup_commands
        await setup_commands(self)
        
        # Sync commands with Discord
        await self.tree.sync()
        logger.info("Slash commands synchronized")
    
    async def on_ready(self):
        """Handle the bot's connection to Discord."""
        logger.info(f"Bot connected as {self.user}")
        logger.info(f"Connected to {len(self.guilds)} servers")
        
        # Set presence (status)
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="markets | /help"
        )
        await self.change_presence(activity=activity)
        
        # Start background tasks
        self.cleanup_contexts.start()
    
    def _split_message(self, message: str) -> List[str]:
        """
        Split a long message into multiple messages that fit within Discord's character limit.
        
        Args:
            message: The message to split
            
        Returns:
            A list of message parts
        """
        # If message is already within the limit, return it as is
        if len(message) <= self.discord_message_limit:
            return [message]
        
        # Split message into parts
        parts = []
        
        # Try to split by paragraphs first
        paragraphs = message.split('\n\n')
        current_part = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed the limit, start a new part
            if len(current_part) + len(paragraph) + 2 > self.discord_message_limit:
                # If current_part is not empty, add it to parts
                if current_part:
                    parts.append(current_part)
                
                # Check if paragraph itself is too long
                if len(paragraph) > self.discord_message_limit:
                    # Split paragraph by sentences
                    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    current_part = ""
                    
                    for sentence in sentences:
                        if len(current_part) + len(sentence) + 1 > self.discord_message_limit:
                            parts.append(current_part)
                            current_part = sentence
                        else:
                            if current_part:
                                current_part += " " + sentence
                            else:
                                current_part = sentence
                else:
                    current_part = paragraph
            else:
                # Add paragraph to current part
                if current_part:
                    current_part += "\n\n" + paragraph
                else:
                    current_part = paragraph
        
        # Add the last part if it's not empty
        if current_part:
            parts.append(current_part)
        
        return parts
    
    async def on_message(self, message):
        """Handle incoming messages."""
        # Log all incoming messages for debugging
        logger.debug(f"Received message: {message.content[:50]}... from {message.author.name} in {message.channel.name}")
        
        # Ignore own messages
        if message.author == self.user:
            logger.debug("Ignoring own message")
            return
        
        # Process commands with the command prefix
        await self.process_commands(message)
        
        # Ignore messages with a prefix or from bots
        if message.content.startswith(self.command_prefix):
            logger.debug(f"Ignoring message with prefix: {self.command_prefix}")
            return
            
        if message.author.bot:
            logger.debug("Ignoring message from another bot")
            return
        
        # Update user context
        user_id = str(message.author.id)
        channel_id = str(message.channel.id)
        self.context_manager.update_last_message(user_id, message.content)
        
        # Add channel ID to context
        user_context = self.context_manager.get_context(user_id)
        user_context['channel_id'] = channel_id
        
        try:
            # Check if the bot is mentioned (for logging purposes only)
            bot_mentioned = self.user.mentioned_in(message)
            
            # Direct all messages to the LLM engine without gatekeeper filtering
            async with message.channel.typing():
                # Generate response using LLM engine
                response = await self.llm_engine.generate_response(
                    message.content,
                    user_id,
                    context=user_context
                )
                
                # Update context with bot's response
                self.context_manager.add_bot_response(user_id, response)
                
                # Split response if it's too long
                message_parts = self._split_message(response)
                
                # Send the first part as a reply
                await message.reply(message_parts[0])
                
                # Send any additional parts as follow-up messages
                for part in message_parts[1:]:
                    await message.channel.send(part)
                
                logger.info(f"Responded to message from {message.author.name}: {message.content[:50]}... (in {len(message_parts)} parts)")
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            if bot_mentioned:
                await message.reply("I encountered an error processing your request. Please try again later.")
    
    @tasks.loop(hours=6)
    async def cleanup_contexts(self):
        """Periodically clean up expired user contexts."""
        try:
            self.context_manager.clean_expired_contexts()
        except Exception as e:
            logger.error(f"Error cleaning up contexts: {e}")
            
    @cleanup_contexts.before_loop
    async def before_cleanup(self):
        """Wait until the bot is ready before starting the cleanup task."""
        await self.wait_until_ready()
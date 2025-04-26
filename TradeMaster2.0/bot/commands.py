"""
TradeMaster 2.0 Discord Commands
Implements slash commands for the bot.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import discord
from discord import app_commands
import logging

logger = logging.getLogger("TradeMaster.Commands")

async def setup_commands(bot):
    """Set up and register slash commands for the bot."""
    
    @bot.tree.command(name="help", description="Get help with using TradeMaster")
    async def help_command(interaction: discord.Interaction):
        """Display help information about the bot."""
        embed = discord.Embed(
            title="TradeMaster Help",
            description="I'm a trading assistant bot designed to help with market analysis, trading strategies, and financial education.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Basic Usage",
            value="Mention me or use slash commands to interact with me.", 
            inline=False
        )
        
        embed.add_field(
            name="Available Commands",
            value=(
                "/help - Show this help message\n"
                "/about - Learn more about TradeMaster\n"
                "/ping - Check if I'm online"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @bot.tree.command(name="about", description="Learn about TradeMaster")
    async def about_command(interaction: discord.Interaction):
        """Display information about the bot."""
        embed = discord.Embed(
            title="About TradeMaster",
            description="I'm a specialized trading assistant powered by AI.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Capabilities",
            value=(
                "• Trading strategy discussions\n"
                "• Market analysis and insights\n"
                "• Financial education and explanations\n"
                "• Technical and fundamental analysis"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Development",
            value="I'm currently being rebuilt with improved capabilities. Some features may be limited during this time.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @bot.tree.command(name="ping", description="Check if the bot is online")
    async def ping_command(interaction: discord.Interaction):
        """Check the bot's latency."""
        latency = round(bot.latency * 1000)
        await interaction.response.send_message(f"Pong! Latency: {latency}ms")
    
    logger.info("Slash commands registered")
# bot.py
#
# Main entry point for the Discord bot application that handles PDF, DOCX, Images, YouTube, MP4 content,
# and referral links across all channels the bot has access to in servers where it is invited.
#
# The bot has six main functions:
# 1. Process PDF files uploaded to any channel, converting them to images
# 2. Process DOCX files uploaded to any channel, converting them to images
# 3. Process batches of images (PNG, JPG, etc.) uploaded at once, grouping them in a thread
# 4. Process YouTube links posted in any channel, creating discussion threads
# 5. Process MP4 links (e.g., from Google Drive) in any channel, creating discussion threads
# 6. Process referral links posted in the designated referral channel, creating rich embeds

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from handlers.pdf_handler import handle_pdf
from handlers.docx_handler import handle_docx
from handlers.image_handler import handle_image_batch
from handlers.youtube_handler import handle_youtube
from handlers.mp4_handler import handle_mp4
from handlers.referral_handler import handle_referral

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')  # Discord bot authentication token
REFERRAL_CHANNEL_ID = os.getenv('REFERRAL_CHANNEL_ID')  # Discord channel ID for referral links

# Set up Discord intents (permissions)
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
intents.messages = True  # Required to receive message events

# Create bot instance with command prefix and configured intents
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    """Event handler that executes when the bot successfully connects to Discord."""
    try:
        if bot.user is not None:
            print(f'{bot.user.name} has connected to Discord!')
        else:
            print('Bot has connected to Discord, but bot.user is None!')
    except Exception as e:
        print(f'Error during initialization: {e}')

@bot.event
async def on_message(message):
    """Event handler that executes when a message is sent in any channel the bot can see."""
    if message.author == bot.user:
        return
    await bot.process_commands(message)

    # Process messages in any channel the bot has access to
    # Check for attachments in priority order
    if message.attachments:
        # First check for image batches (2+ images)
        images_handled = await handle_image_batch(message)
        if not images_handled:
            # Then check for PDFs
            pdf_handled = await handle_pdf(message)
            if not pdf_handled:
                # Then check for DOCXs
                await handle_docx(message)
    
    # Try MP4 handler first, then YouTube handler, then referral handler for all messages
    mp4_handled = await handle_mp4(message)
    if not mp4_handled:
        youtube_handled = await handle_youtube(message)
        if not youtube_handled and REFERRAL_CHANNEL_ID:
            await handle_referral(message, REFERRAL_CHANNEL_ID)

# Remove the default help command to implement a custom one
bot.remove_command('help')

@bot.command(name='help')
async def help_command(ctx):
    """Custom help command that provides information about the bot's functionality."""
    embed = discord.Embed(
        title="Document and Media Bot Help",
        description="This bot helps manage PDFs, DOCXs, image batches, YouTube videos, and MP4 files in your server.",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="PDF Handling",
        value="Upload PDFs to any channel the bot can see, and it will convert them to images.",
        inline=False
    )
    embed.add_field(
        name="DOCX Handling",
        value="Upload Word documents (.docx, .doc) to any channel the bot can see, and it will convert them to images.",
        inline=False
    )
    embed.add_field(
        name="Image Batch Handling",
        value="Upload multiple images (PNG, JPG, WEBP, etc.) at once, and the bot will collect them into a thread.",
        inline=False
    )
    embed.add_field(
        name="YouTube Videos",
        value="Post YouTube links in any channel the bot can see, and it will create a rich embed with the video.",
        inline=False
    )
    embed.add_field(
        name="MP4 Videos",
        value="Post Google Drive MP4 links in any channel the bot can see, and it will create a discussion thread with the video.",
        inline=False
    )
    embed.add_field(
        name="Referral Links",
        value="Post referral links in the designated referral channel, and the bot will create rich embeds with website previews.",
        inline=False
    )
    await ctx.send(embed=embed)

if __name__ == "__main__":
    if TOKEN is None:
        print("Error: DISCORD_TOKEN is not set in the .env file or could not be loaded.")
    else:
        bot.run(TOKEN)
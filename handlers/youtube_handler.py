# handlers/youtube_handler.py
#
# This module handles the processing of YouTube links posted in Discord channels.
# It detects YouTube URLs in messages, fetches video information using the YouTube API,
# and provides options to either create a thread for the video or post it in the current channel.
# The module creates a rich embed with video details and maintains the original YouTube URL for Discord's auto-embed.

# Import necessary libraries
import os  # For environment variables and file operations
import discord  # Main Discord API library
from discord.ui import Button, View  # UI components for interactive buttons
import re  # For regular expression pattern matching
from googleapiclient.discovery import build  # Google API client for YouTube
from dotenv import load_dotenv  # For loading environment variables

# Load environment variables from .env file
load_dotenv()
# Get YouTube API key from environment variables
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# Initialize YouTube API client with the API key
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Regular expression pattern to match YouTube URLs
# This pattern matches both youtube.com/watch?v= and youtu.be/ formats
YOUTUBE_REGEX = r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'

async def get_video_details(video_id):
    """Get basic information about a YouTube video using the YouTube API.
    
    Args:
        video_id: The YouTube video ID (11-character string)
        
    Returns:
        Dictionary containing video details (title, description, thumbnail, stats)
        or None if the video information couldn't be retrieved
    """
    try:
        # Call the YouTube API to get video details
        # The 'snippet' part contains basic info, 'statistics' has view counts, etc.
        response = youtube.videos().list(part="snippet,statistics", id=video_id).execute()
        
        # Check if the API returned any items
        if response['items']:
            # Extract the video data from the response
            data = response['items'][0]['snippet']  # Basic video info
            stats = response['items'][0].get('statistics', {})  # View counts, likes, etc.
            
            # Return a simplified dictionary with the most relevant information
            return {
                'title': data['title'],  # Video title
                'description': data['description'],  # Video description
                'thumbnail': data.get('thumbnails', {}).get('high', {}).get('url', None),  # Thumbnail URL
                'views': stats.get('viewCount', 'N/A'),  # View count
                'likes': stats.get('likeCount', 'N/A')  # Like count
            }
        return None  # No items found for this video ID
    except Exception as e:
        # Log any errors that occur during the API call
        print(f"YouTube API error: {e}")
        return None

class YouTubeOptionsView(View):
    """View class to present YouTube handling options as buttons.
    
    This class creates an interactive UI with buttons that allow users to choose
    how they want to view a YouTube video - either in a new thread or in the current channel.
    """
    def __init__(self, message, video_id, video_details, processing_msg):
        # Set a 60-second timeout for the buttons
        super().__init__(timeout=60)  # Timeout after 60 seconds
        self.message = message  # The original message containing the YouTube link
        self.video_id = video_id  # The extracted YouTube video ID
        self.video_details = video_details  # Dictionary with video information
        self.processing_msg = processing_msg  # Message showing processing status
        self.button_clicked = False  # Flag to track if a button has been clicked

    @discord.ui.button(label="Create Thread", style=discord.ButtonStyle.primary)
    async def create_thread(self, interaction: discord.Interaction, button: Button):
        """Handle the 'Create Thread' button press.
        
        Creates a new thread for the YouTube video and posts the video link there.
        
        Args:
            interaction: The Discord interaction object
            button: The button that was pressed
        """
        # Prevent multiple clicks from processing the same video multiple times
        if self.button_clicked:
            await interaction.response.defer()
            return
        self.button_clicked = True
        
        # Disable all buttons to prevent further interaction
        for item in self.children:
            item.disabled = True
        
        # Update the message with disabled buttons
        await interaction.response.edit_message(view=self)
        
        # Process the YouTube video in a thread
        await self.process_youtube(use_thread=True)

    @discord.ui.button(label="Post Here", style=discord.ButtonStyle.secondary)
    async def post_here(self, interaction: discord.Interaction, button: Button):
        """Handle the 'Post Here' button press.
        
        Posts the YouTube video in the current channel.
        
        Args:
            interaction: The Discord interaction object
            button: The button that was pressed
        """
        # Prevent multiple clicks from processing the same video multiple times
        if self.button_clicked:
            await interaction.response.defer()
            return
        self.button_clicked = True
        
        # Disable all buttons to prevent further interaction
        for item in self.children:
            item.disabled = True
        
        # Update the message with disabled buttons
        await interaction.response.edit_message(view=self)
        
        # Process the YouTube video in the current channel
        await self.process_youtube(use_thread=False)

    async def process_youtube(self, use_thread):
        """Process the YouTube video, either in a thread or the current channel.
        
        This is the main processing function that handles posting the YouTube
        video link and information to the appropriate location.
        
        Args:
            use_thread: Boolean indicating whether to create a new thread
        """
        try:
            # Remove the view by editing the processing message
            await self.processing_msg.edit(content=f"Processing YouTube video...", view=None)
            
            if use_thread:
                # Create a thread with the video title as the thread name
                thread_name = f"Watch: {self.video_details['title'][:50]}"
                # Truncate thread name if too long (Discord limit)
                if len(thread_name) > 100:
                    thread_name = thread_name[:97] + "..."
                    
                # Create a temporary message to anchor the thread
                temp_msg = await self.message.channel.send("Creating video thread...")
                # Create the thread from the temporary message
                target = await temp_msg.create_thread(name=thread_name)
                # Delete the temporary message to keep the channel clean
                await temp_msg.delete()
                final_message = f"Video posted in thread: {target.mention}"
            else:
                # Use current channel as the target
                target = self.message.channel
                final_message = f"Video posted in channel."

            # Send the YouTube URL by itself to trigger Discord's auto-embed
            # This allows Discord to show the video player directly in the chat
            await target.send(f"https://www.youtube.com/watch?v={self.video_id}")
            
            # Create a simple embed with just the description
            # Truncate description to 200 characters to keep it concise
            embed = discord.Embed(
                description=self.video_details['description'][:200] + ("..." if len(self.video_details['description']) > 200 else ""),
                color=discord.Color.red()  # YouTube's brand color
            )
            
            # Send the simplified embed with just the description
            await target.send(embed=embed)
            
            # Update processing message or delete it based on where we posted
            if use_thread:
                # Only show the final message for thread creation
                await self.processing_msg.edit(content=final_message)
            else:
                # For posting in channel, just delete the processing message
                await self.processing_msg.delete()
            
            # Delete the original message with the YouTube link to keep channel clean
            try:
                await self.message.delete()
            except discord.Forbidden:
                print("Bot lacks permission to delete messages.")
        except Exception as e:
            # Handle any errors during processing
            await self.processing_msg.edit(content=f"❌ Error processing YouTube video: {str(e)}")
            print(f"Error processing YouTube video: {e}")
            # Clean up thread if it was created but processing failed
            if use_thread and 'target' in locals() and isinstance(target, discord.Thread):
                await target.delete()
    
    async def on_timeout(self):
        """Handle timeout of the view when buttons aren't pressed within the timeout period.
        
        This method is automatically called when the view times out.
        """
        try:
            # Instead of showing a timeout message, just remove the buttons
            await self.processing_msg.delete()
        except:
            pass  # Ignore errors if the message was already deleted

async def handle_youtube(message):
    """Main handler function for YouTube links in messages.
    
    This is the entry point function called by the bot when a message is received.
    It checks for YouTube URLs and offers options to process them.
    
    Args:
        message: The Discord message object to check for YouTube links
        
    Returns:
        Boolean indicating whether the message was handled as a YouTube link
    """
    # Look for YouTube URLs in the message content using regex
    matches = re.findall(YOUTUBE_REGEX, message.content)
    if not matches:
        return False  # No YouTube URLs found
        
    # Extract the first YouTube video ID found
    video_id = matches[0]
    
    # Send initial processing message to indicate the bot is working
    processing_msg = await message.channel.send(f"Getting video information...")
    
    # Get video information from YouTube API
    video = await get_video_details(video_id)
    if not video:
        # If we couldn't get video info, update the message and return
        await processing_msg.edit(content="Couldn't get information about this YouTube video.")
        return False
    
    # Create options view with buttons for the user to choose how to view the video
    view = YouTubeOptionsView(message, video_id, video, processing_msg)
    await processing_msg.edit(content=f"Video: {video['title']}\nChoose an option:", view=view)
    
    return True  # Successfully handled the YouTube link
# handlers/image_handler.py
#
# This module handles the processing of multiple image files uploaded to a Discord channel.
# It collects images from a message and creates a thread containing all the images in sequence.
# Supports PNG, JPG, JPEG, GIF, WEBP and other common image formats.

# Import necessary libraries
import discord  # Main Discord API library
from discord.ui import Button, View  # UI components for interactive buttons
import asyncio  # For asynchronous operations and delays
from discord.errors import Forbidden  # For handling permission errors
from collections import defaultdict  # For grouping images by message
import re  # For regular expression operations
from io import BytesIO  # For handling binary data in memory

# Define supported image extensions for filtering attachments
IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff']

class ImageBatchView(View):
    """A view class to present image batch handling options as buttons.
    
    This class creates an interactive UI with buttons that allow users to choose
    how they want to view multiple images - either in a new thread or in the current channel.
    """
    def __init__(self, message, attachments, processing_msg):
        # No timeout to keep buttons active indefinitely
        super().__init__(timeout=None)
        self.message = message  # The original message containing the images
        self.attachments = attachments  # List of image attachments
        self.processing_msg = processing_msg  # Message showing processing status
        self.button_clicked = False  # Flag to track if a button has been clicked

    @discord.ui.button(label="Create Thread", style=discord.ButtonStyle.primary)
    async def create_thread(self, interaction: discord.Interaction, button: Button):
        """Handle the 'Create Thread' button press.
        
        Creates a new thread for the images and posts each image in sequence.
        
        Args:
            interaction: The Discord interaction object
            button: The button that was pressed
        """
        # Prevent multiple clicks from processing the same images multiple times
        if self.button_clicked:
            await interaction.response.defer()
            return
        self.button_clicked = True
        
        # Disable all buttons to prevent further interaction
        for item in self.children:
            item.disabled = True
        
        # Update the message with disabled buttons
        await interaction.response.edit_message(view=self)
        # Process the images in a thread
        await self.process_images(use_thread=True)

    @discord.ui.button(label="Post Here", style=discord.ButtonStyle.secondary)
    async def post_here(self, interaction: discord.Interaction, button: Button):
        """Handle the 'Post Here' button press.
        
        Posts all images in the current channel.
        
        Args:
            interaction: The Discord interaction object
            button: The button that was pressed
        """
        # Prevent multiple clicks from processing the same images multiple times
        if self.button_clicked:
            await interaction.response.defer()
            return
        self.button_clicked = True
        
        # Disable all buttons to prevent further interaction
        for item in self.children:
            item.disabled = True
        
        # Update the message with disabled buttons
        await interaction.response.edit_message(view=self)
        # Process the images in the current channel
        await self.process_images(use_thread=False)

    async def process_images(self, use_thread):
        """Process the batch of images, either in a thread or the current channel.
        
        This is the main processing function that handles posting images
        to the appropriate location.
        
        Args:
            use_thread: Boolean indicating whether to create a new thread
        """
        try:
            # Update processing message and remove buttons
            num_images = len(self.attachments)
            await self.processing_msg.edit(
                content=f"Processing {num_images} image{'s' if num_images > 1 else ''}...", 
                view=None
            )
            
            # Determine target channel (thread or current channel)
            if use_thread:
                # Create a descriptive thread name based on the number of images
                # and the first image name
                first_image_name = self.attachments[0].filename
                # Extract base name without extension
                base_name = re.sub(r'\.[^.]+$', '', first_image_name)
                
                # Create thread name based on number of images
                if len(self.attachments) > 1:
                    thread_name = f"{base_name} and {len(self.attachments)-1} more"
                else:
                    thread_name = base_name
                    
                # Truncate thread name if too long (Discord limit)
                if len(thread_name) > 100:
                    thread_name = thread_name[:97] + "..."
                
                try:
                    # Create thread with retry mechanism for rate limits
                    target = await self.create_thread_with_retry(thread_name)
                    if not target:
                        # If thread creation failed, fall back to current channel
                        target = self.message.channel
                        final_message = "⚠️ Could not create thread. Posted images in channel instead."
                    else:
                        final_message = f"{target.mention}"  # Mention the thread
                except Exception as e:
                    print(f"Thread creation error: {e}")
                    target = self.message.channel
                    final_message = "⚠️ Could not create thread. Posted images in channel instead."
            else:
                # Use current channel
                target = self.message.channel
                # Delete the processing message completely when posting in channel
                final_message = None

            # Post images to the target (thread or channel)
            await self.post_images(target)
            
            # Update or delete processing message
            if final_message:
                await self.processing_msg.edit(content=final_message)
            else:
                # Delete the processing message when posting in channel
                await self.processing_msg.delete()
            
            # Delete original message with attachments to keep channel clean
            try:
                await self.message.delete()
            except Forbidden:
                print("Bot lacks permission to delete messages.")
            except Exception as e:
                print(f"Error deleting original message: {e}")
                
        except Forbidden as e:
            # Handle permission errors
            error_msg = f"⚠️ Permission error: {str(e)}"
            await self.processing_msg.edit(content=error_msg)
            print(f"Discord permission error: {e}")
        except Exception as e:
            # Handle general errors
            error_msg = f"❌ Error processing images: {str(e)}"
            await self.processing_msg.edit(content=error_msg)
            print(f"Error processing images: {e}")
            # Clean up thread if it was created but processing failed
            if use_thread and 'target' in locals() and isinstance(target, discord.Thread):
                try:
                    await target.delete()
                except Exception:
                    pass
    
    async def create_thread_with_retry(self, thread_name):
        """Create a thread with retry logic for rate limits.
        
        Discord has rate limits that can cause thread creation to fail.
        This function implements retry logic with exponential backoff.
        
        Args:
            thread_name: Name for the new thread
            
        Returns:
            The created thread object or None if creation failed
        """
        max_retries = 3  # Maximum number of attempts
        retry_delay = 2  # Start with 2 seconds delay
        
        for attempt in range(max_retries):
            try:
                # Create thread directly using channel's create_thread method
                thread = await self.message.channel.create_thread(
                    name=thread_name,
                    type=discord.ChannelType.public_thread,
                    auto_archive_duration=1440  # 24 hours
                )
                
                # Wait a bit longer for the notification message to appear
                await asyncio.sleep(2)
                
                # Delete the thread creation notification to keep channel clean
                try:
                    # First try to find system messages about thread creation
                    found = False
                    async for msg in self.message.channel.history(limit=10):
                        # Check for system message type
                        if msg.type == discord.MessageType.thread_created:
                            await msg.delete()
                            found = True
                            break
                        
                        # Fallback: Check for content that looks like a thread notification
                        # This handles cases where the message type check doesn't work
                        if msg.author.bot and "started a thread" in msg.content and thread_name in msg.content:
                            await msg.delete()
                            found = True
                            break
                    
                    if not found:
                        print(f"Could not find thread notification message to delete")
                except Exception as e:
                    print(f"Error deleting thread notification: {e}")
                
                return thread
                
            except discord.Forbidden as e:
                # Handle permission errors during thread creation
                print(f"Thread creation attempt {attempt+1} failed due to permissions: {e}")
                if attempt == max_retries - 1:
                    return None  # Failed after all retries
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            except Exception as e:
                # Handle other errors during thread creation
                print(f"Unexpected error in thread creation: {e}")
                return None
        
        return None  # Failed to create thread after all retries
    
    async def post_images(self, target):
        """Post images to the target channel or thread in sequence.
        
        Args:
            target: The Discord channel or thread to post images to
        """
        try:
            # Sort attachments by filename to maintain order
            sorted_attachments = sorted(self.attachments, key=lambda a: a.filename)
            
            # Post each image with no caption
            for attachment in sorted_attachments:
                # Download the attachment content
                file_content = await attachment.read()
                
                # Create a BytesIO object from the content
                file_obj = BytesIO(file_content)
                
                # Send the file to the target channel/thread
                await target.send(file=discord.File(fp=file_obj, filename=attachment.filename))
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
                
        except Exception as e:
            # Propagate any errors during posting
            raise Exception(f"Error posting images: {e}")

async def handle_image_batch(message):
    """Main handler function for image attachments, offering processing options.
    
    This is the entry point function called by the bot when images are detected.
    It checks for multiple image attachments and offers options to process them.
    
    Args:
        message: The Discord message containing image attachments
        
    Returns:
        Boolean indicating whether the message was handled as an image batch
    """
    # Check if the message has any attachments
    if not message.attachments:
        return False
    
    # Filter for image attachments by checking file extensions
    image_attachments = []
    for attachment in message.attachments:
        # Extract the file extension and convert to lowercase
        _, ext = os.path.splitext(attachment.filename.lower())
        if ext in IMAGE_EXTENSIONS:
            image_attachments.append(attachment)
    
    # Only process if there are multiple images (2 or more)
    if len(image_attachments) < 2:
        return False
    
    # Check basic permissions to ensure the bot can function
    channel = message.channel
    bot_member = channel.guild.me if hasattr(channel, 'guild') else None
    
    if bot_member:
        permissions = channel.permissions_for(bot_member)
        missing_permissions = []
        
        # Check for required permissions
        if not permissions.send_messages:
            missing_permissions.append("Send Messages")
        if not permissions.attach_files:
            missing_permissions.append("Attach Files")
        if not permissions.manage_messages:
            missing_permissions.append("Manage Messages")
        
        # Notify if permissions are missing
        if missing_permissions:
            await message.channel.send(
                f"⚠️ Bot lacks required permissions: {', '.join(missing_permissions)}. "
                f"Please ensure the bot has these permissions in this channel."
            )
            return False
    
    try:
        # Present options to the user via buttons
        processing_msg = await message.channel.send(
            f"Found {len(image_attachments)} images. Choose an option:"
        )
        view = ImageBatchView(message, image_attachments, processing_msg)
        await processing_msg.edit(view=view)
        return True  # Successfully handled the image batch
    except Exception as e:
        # Handle any errors during setup
        print(f"Error presenting image batch options: {e}")
        return False  # Failed to handle the image batch

# Helper function to group images by message for bulk processing
async def process_image_groups(messages):
    """Process groups of images across multiple messages.
    
    This function is used to handle cases where a user posts multiple
    images across several messages in quick succession.
    
    Args:
        messages: List of Discord message objects to process
        
    Returns:
        Number of image groups processed
    """
    # Group images by message author
    image_groups = defaultdict(list)
    
    for message in messages:
        # Skip messages without attachments
        if not message.attachments:
            continue
            
        # Get image attachments from this message
        for attachment in message.attachments:
            _, ext = os.path.splitext(attachment.filename.lower())
            if ext in IMAGE_EXTENSIONS:
                # Add to the author's group
                image_groups[message.author.id].append((message, attachment))
    
    # Process each author's image group
    groups_processed = 0
    
    for author_id, image_data in image_groups.items():
        # Only process if there are multiple images
        if len(image_data) < 2:
            continue
            
        # Get all messages and attachments
        messages = [data[0] for data in image_data]
        attachments = [data[1] for data in image_data]
        
        # Use the first message as the reference
        first_message = messages[0]
        
        # Create a processing message
        processing_msg = await first_message.channel.send(
            f"Found {len(attachments)} images from {first_message.author.display_name}. Choose an option:"
        )
        
        # Create and show the options view
        view = ImageBatchView(first_message, attachments, processing_msg)
        await processing_msg.edit(view=view)
        
        groups_processed += 1
    
    return groups_processed

# Import os at the top of the file
import os
# handlers/mp4_handler.py
#
# This module handles the processing of uploaded MP4/MOV files in Discord.
# It applies a "Confidential - GridZer0" watermark to videos and posts them with a warning.
import os
import discord
from discord.ui import Button, View
import re
import asyncio
from dotenv import load_dotenv
from io import BytesIO
import subprocess
import math
import tempfile
import shutil

# Load environment variables
load_dotenv()
# Path to FFmpeg binary (update this path to match your environment)
FFMPEG_PATH = r"C:\Users\Sturgis\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
# Verify FFmpeg path exists
if not os.path.isfile(FFMPEG_PATH):
    error_msg = f"FFmpeg not found at {FFMPEG_PATH}. Please install FFmpeg and update FFMPEG_PATH in the script."
    print(error_msg)
    raise FileNotFoundError(error_msg)
print(f"FFmpeg found at: {FFMPEG_PATH}")
# Regex to identify .mov or .mp4 file attachments
VIDEO_REGEX = r'\.(mov|mp4)$'
processed_files = set()  # Keep track of processed file IDs to avoid duplicates

# Maximum file size limit (500MB)
MAX_FILE_SIZE_MB = 500
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Discord size limits
DISCORD_SIZE_LIMIT_MB = 25  # For regular users/servers
MAX_SEGMENT_SIZE_MB = 8     # Target size for video segments to ensure they upload

def process_video(input_file, output_file, watermark=True):
    """Process video with optional watermark."""
    try:
        # Get file size in MB
        file_size_mb = os.path.getsize(input_file) / (1024 * 1024)
        
        # Adjust bitrate based on input file size
        target_size_mb = 6
        video_duration_estimate = file_size_mb / 5  # Rough estimate: ~5MB per minute of video
        target_bitrate_kbps = int((target_size_mb * 8 * 1024) / video_duration_estimate) if video_duration_estimate > 0 else 300
        
        # Cap bitrate between reasonable values
        target_bitrate_kbps = max(150, min(target_bitrate_kbps, 400))
        
        # Add scale filter for larger videos to reduce dimensions
        scale_filter = "scale=640:-2" if file_size_mb > 40 else "scale=854:-2"
        
        # Set up the filter based on whether watermark is needed
        if watermark:
            vf_param = f"{scale_filter},drawtext=fontfile=Arial.ttf:text='Confidential - GridZer0':fontsize=24:fontcolor=white@0.8:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-tw)/2:y=h-th-10"
        else:
            vf_param = scale_filter
        
        # FFmpeg command 
        command = [
            FFMPEG_PATH,
            '-i', input_file,  # Input file
            '-vf', vf_param,
            '-f', 'mp4',  # Output format
            '-vcodec', 'libx264',  # Video codec
            '-b:v', f'{target_bitrate_kbps}k',  # Bitrate
            '-preset', 'ultrafast',  # Speed up encoding
            '-crf', '32',  # Constant Rate Factor - higher value = more compression
            '-maxrate', f'{target_bitrate_kbps * 1.5}k',  # Maximum bitrate
            '-bufsize', f'{target_bitrate_kbps * 3}k',  # Buffer size
            '-movflags', '+faststart',  # Optimize for web playback
            '-pix_fmt', 'yuv420p',  # Standard pixel format for better compatibility
            output_file  # Output file
        ]
        
        print(f"FFmpeg command: {' '.join(command)}")
        
        # Run FFmpeg process
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        # Check output file size
        output_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print(f"Original size: {file_size_mb:.2f}MB, Processed size: {output_size_mb:.2f}MB")
        
        return True
            
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else 'Unknown FFmpeg error'
        print(f"FFmpeg stderr: {error_msg}")
        raise Exception(f"FFmpeg failed with return code {process.returncode}")
    except Exception as e:
        print(f"Unexpected error in process_video: {str(e)}")
        raise

class LocationOptionsView(View):
    """View class to present options for where to post the video before processing."""
    def __init__(self, message, attachment, processing_msg):
        super().__init__(timeout=None)  # No timeout
        self.message = message
        self.attachment = attachment
        self.processing_msg = processing_msg
        self.button_clicked = False
    @discord.ui.button(label="Create Thread", style=discord.ButtonStyle.primary)
    async def create_thread(self, interaction: discord.Interaction, button: Button):
        """Handle the 'Create Thread' button press."""
        if self.button_clicked:
            await interaction.response.defer()
            return
        self.button_clicked = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(view=self)
        await self.process_video(use_thread=True)
    @discord.ui.button(label="Post Here", style=discord.ButtonStyle.secondary)
    async def post_here(self, interaction: discord.Interaction, button: Button):
        """Handle the 'Post Here' button press."""
        if self.button_clicked:
            await interaction.response.defer()
            return
        self.button_clicked = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(view=self)
        await self.process_video(use_thread=False)
    async def process_video(self, use_thread):
        """Process the video and post it either in a thread or the current channel."""
        thread_ref = None  # Store the thread reference for later
        
        # Create a temporary directory for working files
        temp_dir = tempfile.mkdtemp()
        try:
            # Update processing message
            await self.processing_msg.edit(content=f"Processing {self.attachment.filename}... This may take a few minutes.", view=None)
            
            # Set up temporary files
            input_file = os.path.join(temp_dir, 'input.mp4')
            output_file = os.path.join(temp_dir, 'output.mp4')
            
            # Download the attachment to a file
            content = await self.attachment.read()
            with open(input_file, 'wb') as f:
                f.write(content)
            
            # Get output filename
            file_name = self.attachment.filename.rsplit('.', 1)[0] + '.mp4' if '.' in self.attachment.filename else self.attachment.filename + '.mp4'
            
            try:
                await self.processing_msg.edit(content=f"Processing video... This may take a few minutes.")
                # Process the video with watermark
                process_video(input_file, output_file, watermark=True)
            except Exception as e:
                raise Exception(f"Processing failed: {str(e)}")
            
            # Get the size of the processed file
            processed_size = os.path.getsize(output_file) / (1024 * 1024)
            print(f"Successfully processed video: {file_name}, Size: {processed_size:.2f}MB")
            
            await self.processing_msg.edit(content=f"Video processed. Preparing to post ({processed_size:.2f}MB)...")
            
            # Determine target channel (thread or current channel)
            if use_thread:
                # Create thread
                thread_name = file_name
                if len(thread_name) > 100:
                    thread_name = thread_name[:97] + "..."
                
                try:
                    # Create thread with retry mechanism
                    target = await self.create_thread_with_retry(thread_name)
                    thread_ref = target  # Store the thread reference
                    
                    if not target:
                        # If thread creation failed, fall back to current channel
                        target = self.message.channel
                        await self.processing_msg.edit(content="⚠️ Could not create thread. Posting video in channel instead...")
                    else:
                        await self.processing_msg.edit(content=f"Created thread. Preparing video...")
                except Exception as e:
                    print(f"Thread creation error: {e}")
                    target = self.message.channel
                    await self.processing_msg.edit(content="⚠️ Could not create thread. Posting video in channel instead...")
            else:
                # Use current channel
                target = self.message.channel
                
            # Check if the processed file is under Discord's limit
            if processed_size <= DISCORD_SIZE_LIMIT_MB:
                # Upload the file
                try:
                    await self.processing_msg.edit(content=f"Uploading video ({processed_size:.2f}MB)...")
                    
                    # Upload the processed video
                    with open(output_file, 'rb') as f:
                        await target.send(
                            file=discord.File(f, filename=file_name)
                        )
                    
                    # Add a warning message
                    await target.send("⚠️ **WARNING**: Do not download or share this video outside the server.")
                    
                    # Delete original message with attachment
                    try:
                        await self.message.delete()
                    except discord.Forbidden:
                        print("Bot lacks permission to delete messages.")
                    
                    # Update the processing message
                    if use_thread and thread_ref:
                        await self.processing_msg.edit(content=f"{thread_ref.mention}")
                    else:
                        await self.processing_msg.delete()
                    
                except discord.HTTPException as e:
                    # Even though we checked the size, Discord might still reject it
                    await self.handle_large_video(input_file, file_name, target, use_thread, thread_ref, temp_dir)
            else:
                # File is too large, use segment approach
                await self.handle_large_video(input_file, file_name, target, use_thread, thread_ref, temp_dir)
                    
        except Exception as e:
            error_msg = str(e)[:500] + '...' if len(str(e)) > 500 else str(e)
            await self.processing_msg.edit(content=f"❌ Error processing video: {error_msg}")
            print(f"Error processing video: {e}")
            # Clean up thread if it was created but processing failed
            if use_thread and thread_ref:
                try:
                    await thread_ref.delete()
                except Exception:
                    pass
        finally:
            # Clean up temp directory
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Error cleaning up temp directory: {e}")
                    
    async def handle_large_video(self, input_file, file_name, target, use_thread, thread_ref=None, temp_dir=None):
        """Handle videos that are too large by splitting them into segments."""
        if temp_dir is None:
            temp_dir = tempfile.mkdtemp()
            
        try:
            await self.processing_msg.edit(content="Video too large for Discord. Creating shorter clips...")
            
            # Get video duration using FFmpeg
            probe_cmd = [
                FFMPEG_PATH,
                '-i', input_file,
                '-hide_banner'
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            
            # Parse duration
            duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)', result.stderr)
            if not duration_match:
                raise ValueError("Could not determine video duration")
            
            hours = int(duration_match.group(1))
            minutes = int(duration_match.group(2))
            seconds = float(duration_match.group(3))
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            # Determine file size and calculate number of segments needed
            file_size_mb = os.path.getsize(input_file) / (1024 * 1024)
            
            # Calculate number of segments
            segments = max(6, min(int(file_size_mb / MAX_SEGMENT_SIZE_MB), 15))
            
            # For very long videos, we need more segments regardless of file size
            duration_based_segments = int(total_seconds / 180)  # ~3 minutes per segment
            segments = max(segments, duration_based_segments)
            
            # Cap at a reasonable number
            segments = min(segments, 20)
            
            print(f"Video duration: {total_seconds:.2f} seconds, file size: {file_size_mb:.2f}MB, creating {segments} segments")
            
            segment_duration = total_seconds / segments
            
            # Create output directory for segments
            segments_dir = os.path.join(temp_dir, 'segments')
            os.makedirs(segments_dir, exist_ok=True)
            
            # Create segments with watermark
            segment_files = []
            
            # Adjust compression based on file size
            target_crf = 30  # Default CRF value
            if file_size_mb > 200:
                target_crf = 33
            if file_size_mb > 300:
                target_crf = 35
                
            # Lower resolution for larger files
            scale_param = "scale=854:-2"  # Default scale
            if file_size_mb > 200:
                scale_param = "scale=640:-2"
            if file_size_mb > 300:
                scale_param = "scale=480:-2"
            
            # Create all segments with watermark included
            for i in range(segments):
                start_time = i * segment_duration
                segment_file = os.path.join(segments_dir, f'segment_{i}.mp4')
                
                # Create segment with watermark
                segment_cmd = [
                    FFMPEG_PATH,
                    '-i', input_file,
                    '-ss', str(start_time),
                    '-t', str(segment_duration),
                    '-vf', f"{scale_param},drawtext=fontfile=Arial.ttf:text='Confidential - GridZer0':fontsize=24:fontcolor=white@0.8:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-tw)/2:y=h-th-10",
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-crf', str(target_crf),
                    '-c:a', 'aac',
                    '-b:a', '64k',
                    '-ac', '1',
                    '-ar', '22050',
                    segment_file
                ]
                
                await self.processing_msg.edit(content=f"Creating segment {i+1} of {segments}...")
                subprocess.run(segment_cmd)
                
                # Check if segment is still too large
                segment_size = os.path.getsize(segment_file) / (1024 * 1024)
                
                if segment_size > MAX_SEGMENT_SIZE_MB:
                    # If still too large, compress more but WITHOUT adding another watermark
                    compressed_file = os.path.join(segments_dir, f'compressed_{i}.mp4')
                    
                    # Compress without adding another watermark
                    compress_cmd = [
                        FFMPEG_PATH,
                        '-i', segment_file,
                        '-c:v', 'libx264',  # Re-encode video 
                        '-preset', 'ultrafast',
                        '-crf', '38',       # Higher compression
                        '-vf', 'scale=480:-2',  # Lower resolution
                        '-c:a', 'aac',
                        '-b:a', '32k',      # Lower audio quality
                        '-ac', '1',         # Mono audio
                        compressed_file
                    ]
                    
                    await self.processing_msg.edit(content=f"Further compressing segment {i+1}...")
                    subprocess.run(compress_cmd)
                    
                    # Check if it's still too large
                    if os.path.getsize(compressed_file) > MAX_SEGMENT_SIZE_MB * 1024 * 1024:
                        # One more aggressive compression attempt
                        final_file = os.path.join(segments_dir, f'final_{i}.mp4')
                        final_cmd = [
                            FFMPEG_PATH,
                            '-i', compressed_file,
                            '-c:v', 'libx264',
                            '-preset', 'ultrafast',
                            '-crf', '42',       # Very high compression
                            '-vf', 'scale=320:-2',  # Very low resolution
                            '-c:a', 'aac',
                            '-b:a', '24k',
                            '-ac', '1',
                            '-ar', '16000',    # Lower sample rate
                            final_file
                        ]
                        
                        await self.processing_msg.edit(content=f"Final compression for segment {i+1}...")
                        subprocess.run(final_cmd)
                        segment_files.append(final_file)
                    else:
                        segment_files.append(compressed_file)
                else:
                    segment_files.append(segment_file)
            
            # Upload each segment
            successful_uploads = 0
            for i, segment_file in enumerate(segment_files):
                segment_size = os.path.getsize(segment_file) / (1024 * 1024)
                
                await self.processing_msg.edit(content=f"Uploading segment {i+1} of {segments} ({segment_size:.2f}MB)...")
                
                try:
                    base_name = os.path.splitext(file_name)[0]
                    segment_name = f"{base_name}_part{i+1}of{segments}.mp4"
                    
                    # Upload the segment
                    with open(segment_file, 'rb') as f:
                        await target.send(
                            f"Video part {i+1} of {segments}",
                            file=discord.File(f, filename=segment_name)
                        )
                    successful_uploads += 1
                except discord.HTTPException as e:
                    print(f"Error uploading segment {i}: {e}")
                    await target.send(f"⚠️ Failed to upload segment {i+1} of {segments} (Size: {segment_size:.2f}MB)")
            
            # Add a warning message
            await target.send("⚠️ **WARNING**: Do not download or share these video segments outside the server.")
            
            # Update processing message
            if use_thread and thread_ref:
                if successful_uploads == segments:
                    await self.processing_msg.edit(content=f"{thread_ref.mention}")
                else:
                    await self.processing_msg.edit(content=f"{thread_ref.mention} (Uploaded {successful_uploads} of {segments} segments)")
            else:
                await self.processing_msg.delete()
                
            # Delete original message
            try:
                await self.message.delete()
            except Exception as e:
                print(f"Error deleting original message: {e}")
                
        except Exception as e:
            print(f"Error handling large video: {e}")
            await self.processing_msg.edit(content=f"❌ Could not process large video: {str(e)[:100]}")
            
        finally:
            # We don't clean up temp_dir here as it's passed from parent function
            pass
    
    async def create_thread_with_retry(self, thread_name):
        """Create a thread with retry logic for rate limits."""
        max_retries = 3
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
                
                # Delete the thread creation notification
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
                print(f"Thread creation attempt {attempt+1} failed due to permissions: {e}")
                if attempt == max_retries - 1:
                    return None  # Failed after all retries
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            except Exception as e:
                print(f"Unexpected error in thread creation: {e}")
                return None
        
        return None  # Failed to create thread

async def handle_mp4(message):
    """Process .mov or .mp4 attachments uploaded to the channel."""
    if message.author == message.guild.me:  # Ignore bot's own messages
        return False
        
    # Check for video attachments
    if message.attachments:
        for attachment in message.attachments:
            if re.search(VIDEO_REGEX, attachment.filename, re.IGNORECASE):
                # Check if already processed to avoid duplicates
                if attachment.id in processed_files:
                    await message.reply("This video has already been processed recently.")
                    return True
                
                # Check file size before processing - allow larger files but warn about potential issues
                if attachment.size > MAX_FILE_SIZE_BYTES:  # 500MB in bytes
                    await message.reply(f"⚠️ Video is too large ({attachment.size / (1024 * 1024):.1f}MB). Maximum size is {MAX_FILE_SIZE_MB}MB.")
                    return True
                
                file_size_mb = attachment.size / (1024 * 1024)
                
                # Mark as processed
                processed_files.add(attachment.id)
                
                # Send initial processing message
                processing_msg = await message.channel.send(f"Video detected: {attachment.filename} ({file_size_mb:.2f}MB)")
                
                # Present options to the user BEFORE processing
                view = LocationOptionsView(message, attachment, processing_msg)
                await processing_msg.edit(
                    content=f"Video: {attachment.filename} ({file_size_mb:.2f}MB)\nChoose where to post the watermarked version:", 
                    view=view
                )
                return True
    
    return False  # Indicate that we didn't handle any videos
import discord
from discord.ui import Button, View
import fitz
from io import BytesIO
import asyncio
from discord.errors import Forbidden, HTTPException, NotFound
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration from environment variables
MAX_FILE_SIZE = int(os.getenv('MAX_PDF_SIZE', 8 * 1024 * 1024))  # Default 8MB
WATERMARK_TEXT = os.getenv('WATERMARK_TEXT', 'GridZer0')  # Default to GridZer0
WATERMARK_FONTSIZE = int(os.getenv('WATERMARK_FONTSIZE', 24))  # Default to 24 for smaller text

# Single global set to track processed message IDs
_processed_pdf_messages = set()

async def convert_and_upload_pdf(pdf_bytes, target, use_thread=False, watermark_text=WATERMARK_TEXT,
                                fontsize=WATERMARK_FONTSIZE):
    """Convert PDF bytes and upload images directly to the target channel or thread."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        start_idx = 1 if use_thread and isinstance(target, discord.Thread) else 0

        for i, page in enumerate(doc, start=1):
            if i <= start_idx and use_thread:
                continue
            if watermark_text:
                logger.info(f"Applying watermark: {watermark_text} on page {i}")
                # Calculate text width for centering
                text_width = fitz.get_text_length(watermark_text, "helv", fontsize)
                x = (page.rect.width - text_width) / 2
                y = page.rect.height - 20  # Position near the bottom
                # Insert text without opacity
                page.insert_text(
                    fitz.Point(x, y),
                    watermark_text,
                    fontsize=fontsize,
                    fontname="helv",
                    color=(0.5, 0.5, 0.5)  # Gray color
                )
            pix = page.get_pixmap()
            img_bytes = pix.tobytes("png")
            img = BytesIO(img_bytes)
            img.seek(0)
            try:
                await target.send(file=discord.File(fp=img, filename=f"page_{i}.png"))
            except HTTPException as e:
                if e.code == 429:  # Rate limit
                    logger.warning(f"Rate limit hit, retrying after {e.retry_after} seconds")
                    await asyncio.sleep(e.retry_after)
                    await target.send(file=discord.File(fp=img, filename=f"page_{i}.png"))
                else:
                    raise
        doc.close()
        return True
    except Exception as e:
        logger.error(f"Error converting/uploading PDF: {e}")
        return False

class PDFOptionsView(View):
    """A view class to present PDF handling options as buttons."""
    def __init__(self, message, attachment, processing_msg):
        super().__init__(timeout=None)
        self.message = message
        self.attachment = attachment
        self.processing_msg = processing_msg
        self.button_clicked = False

    @discord.ui.button(label="Create Thread", style=discord.ButtonStyle.primary)
    async def create_thread(self, interaction: discord.Interaction, button: Button):
        if self.button_clicked:
            await interaction.response.defer()
            return
        self.button_clicked = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        await self.process_pdf(use_thread=True)

    @discord.ui.button(label="Post Here", style=discord.ButtonStyle.secondary)
    async def post_here(self, interaction: discord.Interaction, button: Button):
        if self.button_clicked:
            await interaction.response.defer()
            return
        self.button_clicked = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        await self.process_pdf(use_thread=False)

    async def process_pdf(self, use_thread):
        """Process the PDF, either in a thread or the current channel."""
        try:
            await self.processing_msg.edit(content="Converting PDF to images...", view=None)
            pdf_bytes = await self.attachment.read()
            target = self.message.channel
            final_message = None

            if use_thread:
                thread_name = self.attachment.filename
                if len(thread_name) > 100:
                    thread_name = thread_name[:97] + "..."
                try:
                    target = await self.create_thread_with_retry(thread_name)
                    if not target:
                        target = self.message.channel
                        final_message = "⚠️ Could not create thread. Posted PDF in current channel instead."
                    else:
                        final_message = f"{target.mention}"
                except Exception as e:
                    logger.error(f"Thread creation error in channel {self.message.channel.id}: {e}")
                    target = self.message.channel
                    final_message = "⚠️ Could not create thread. Posted PDF in current channel instead."

            if use_thread and isinstance(target, discord.Thread) and target != self.message.channel:
                first_page = await self.get_first_page(pdf_bytes)
                if first_page:
                    first_page.seek(0)
                    await target.send(file=discord.File(fp=first_page, filename="page_1.png"))

            success = await asyncio.wait_for(
                convert_and_upload_pdf(pdf_bytes, target, use_thread),
                timeout=300  # 5-minute timeout for large PDFs
            )

            if not success:
                raise ValueError("Failed to convert/upload PDF")

            # Wait briefly to ensure message is still accessible
            await asyncio.sleep(0.5)
            try:
                if final_message:
                    await self.processing_msg.edit(content=final_message)
                else:
                    await self.processing_msg.delete()
            except NotFound:
                logger.warning(f"Processing message {self.processing_msg.id} not found, sending to channel")
                if final_message:
                    await self.message.channel.send(final_message)

            try:
                await self.message.delete()
            except Forbidden:
                logger.warning("Bot lacks permission to delete messages in channel {self.message.channel.id}")
            except Exception as e:
                logger.error(f"Error deleting original message {self.message.id}: {e}")

        except Forbidden as e:
            error_msg = f"⚠️ Permission error: {str(e)}"
            await self.safe_edit_processing_msg(error_msg)
            logger.error(f"Discord permission error in channel {self.message.channel.id}: {e}")
        except asyncio.TimeoutError:
            error_msg = "❌ PDF processing timed out after 5 minutes."
            await self.safe_edit_processing_msg(error_msg)
            logger.error(f"PDF processing timed out for message {self.message.id}")
        except Exception as e:
            error_msg = f"❌ Error processing PDF: {str(e)}"
            await self.safe_edit_processing_msg(error_msg)
            logger.error(f"Error processing PDF for message {self.message.id}: {e}")
            if use_thread and 'target' in locals() and isinstance(target, discord.Thread):
                try:
                    await target.delete()
                except Exception:
                    pass
        finally:
            global _processed_pdf_messages
            if self.message.id in _processed_pdf_messages:
                _processed_pdf_messages.remove(self.message.id)

    async def safe_edit_processing_msg(self, content):
        """Safely edit or send the processing message to avoid NotFound errors."""
        try:
            await asyncio.sleep(0.5)  # Brief delay for API consistency
            await self.processing_msg.edit(content=content)
        except NotFound:
            logger.warning(f"Processing message {self.processing_msg.id} not found, sending to channel")
            await self.message.channel.send(content)
        except Exception as e:
            logger.error(f"Error editing processing message {self.processing_msg.id}: {e}")
            await self.message.channel.send(content)

    async def get_first_page(self, pdf_bytes):
        """Extract the first page of the PDF as an image."""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page = doc[0]
            if WATERMARK_TEXT:
                logger.info("Applying watermark to first page")
                # Calculate text width for centering
                text_width = fitz.get_text_length(WATERMARK_TEXT, "helv", WATERMARK_FONTSIZE)
                x = (page.rect.width - text_width) / 2
                y = page.rect.height - 20  # Position near the bottom
                # Insert text without opacity
                page.insert_text(
                    fitz.Point(x, y),
                    WATERMARK_TEXT,
                    fontsize=WATERMARK_FONTSIZE,
                    fontname="helv",
                    color=(0.5, 0.5, 0.5)  # Gray color
                )
            pix = page.get_pixmap()
            img_bytes = pix.tobytes("png")
            doc.close()
            return BytesIO(img_bytes)
        except Exception as e:
            logger.error(f"Error extracting first page: {e}")
            return None

    async def create_thread_with_retry(self, thread_name):
        """Create a thread with retry logic for rate limits."""
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                thread = await self.message.channel.create_thread(
                    name=thread_name,
                    type=discord.ChannelType.public_thread,
                    auto_archive_duration=1440
                )
                await asyncio.sleep(2)
                try:
                    async for msg in self.message.channel.history(limit=10, after=self.message.created_at):
                        if msg.author.bot and msg.created_at > self.message.created_at and "thread" in msg.content.lower():
                            await msg.delete()
                            break
                    else:
                        logger.warning(f"Could not find thread notification for thread {thread_name}")
                except Exception as e:
                    logger.error(f"Error deleting thread notification: {e}")
                return thread
            except discord.Forbidden as e:
                logger.error(f"Thread creation attempt {attempt+1} failed due to permissions: {e}")
                if attempt == max_retries - 1:
                    return None
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            except Exception as e:
                logger.error(f"Unexpected error in thread creation: {e}")
                return None
        return None

async def handle_pdf(message):
    """Main handler function for PDF attachments."""
    if message.id in _processed_pdf_messages:
        return True
    if not message.attachments:
        return False
    pdf_attachments = [att for att in message.attachments if att.filename.lower().endswith('.pdf')]
    if not pdf_attachments:
        return False
    _processed_pdf_messages.add(message.id)
    attachment = pdf_attachments[0]

    if attachment.size > MAX_FILE_SIZE:
        await message.channel.send(f"⚠️ PDF too large: {attachment.filename} (max {MAX_FILE_SIZE // 1024 // 1024}MB)")
        _processed_pdf_messages.remove(message.id)
        return True

    channel = message.channel
    bot_member = channel.guild.me if hasattr(channel, 'guild') else None
    if bot_member:
        permissions = channel.permissions_for(bot_member)
        missing_permissions = []
        if not permissions.send_messages:
            missing_permissions.append("Send Messages")
        if not permissions.attach_files:
            missing_permissions.append("Attach Files")
        if not permissions.create_public_threads:
            missing_permissions.append("Create Public Threads")
        if not permissions.manage_threads:
            missing_permissions.append("Manage Threads")
        if missing_permissions:
            await message.channel.send(
                f"⚠️ Bot lacks required permissions: {', '.join(missing_permissions)}."
            )
            _processed_pdf_messages.remove(message.id)
            return True

    try:
        processing_msg = await message.channel.send("Choose an option for this PDF:")
        view = PDFOptionsView(message, attachment, processing_msg)
        await processing_msg.edit(view=view)
        return True
    except Exception as e:
        logger.error(f"Error presenting PDF options for message {message.id}: {e}")
        _processed_pdf_messages.remove(message.id)
        return False
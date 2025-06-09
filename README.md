# PDF and YouTube Discord Bot

A Discord bot that enhances your server with PDF viewing capabilities and YouTube video integration. This bot automatically converts uploaded PDFs into images for easy viewing and creates discussion threads for YouTube videos.

## Features

### PDF Handling

- **PDF to Image Conversion**: Automatically converts uploaded PDF files into images
- **Thread Creation**: Creates a dedicated thread for each PDF for organized discussions
- **Page Navigation**: Posts each page as a separate image with page numbers
- **File Size Limit**: Enforces an 8MB limit on PDF files to prevent abuse

### YouTube Integration

- **Video Monitoring**: Periodically checks for new videos from a specified YouTube channel
- **Automatic Posting**: Posts new videos to a designated Discord channel with rich embeds
- **Link Enhancement**: Automatically enhances YouTube links posted in the designated channel with video details
- **Discussion Threads**: Creates discussion threads for each video

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- A Discord bot token (from [Discord Developer Portal](https://discord.com/developers/applications))
- A YouTube API key (from [Google Cloud Console](https://console.cloud.google.com/))
- Poppler installed (required for PDF conversion)

### Installation

1. Clone or download this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Install Poppler (required for pdf2image):
   - **Windows**: Download from [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/) and add to PATH
   - **macOS**: `brew install poppler`
   - **Linux**: `apt-get install poppler-utils`

### Configuration

1. Copy the `.env` file and fill in your credentials:

```
# Discord Bot Configuration
# Replace these placeholder values with your actual credentials

# Your Discord bot token from the Discord Developer Portal
DISCORD_TOKEN=your_discord_token_here

# YouTube API key from Google Cloud Console
YOUTUBE_API_KEY=your_youtube_api_key_here

# YouTube channel ID to monitor for new videos
YOUTUBE_CHANNEL_ID=your_youtube_channel_id_here

# Discord channel ID where PDFs will be processed
# This should be a numeric ID, e.g., 123456789012345678
PDF_CHANNEL_ID=0

# Discord channel ID where YouTube videos will be posted
# This should be a numeric ID, e.g., 123456789012345678
YOUTUBE_CHANNEL_ID_DISCORD=0
```

2. Update the channel IDs in the `.env` file:
   - `PDF_CHANNEL_ID`: The Discord channel ID where PDFs will be processed
   - `YOUTUBE_CHANNEL_ID_DISCORD`: The Discord channel ID where YouTube videos will be posted

### Finding Channel IDs

1. Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
2. Right-click on a channel and select "Copy ID"

## Usage

### Running the Bot

```
python bot.py
```

### Bot Commands

- `!help` - Displays help information about the bot

### PDF Processing

1. Upload a PDF file to the designated PDF channel
2. The bot will create a thread with the PDF filename
3. Each page of the PDF will be posted as an image in the thread

### YouTube Features

1. The bot will automatically check for new videos from the configured YouTube channel every hour
2. When users post YouTube links in the designated channel, the bot will enhance them with video details

## Troubleshooting

### Common Issues

- **PDF Processing Fails**: Ensure Poppler is correctly installed and accessible in your PATH
- **YouTube API Errors**: Verify your YouTube API key is valid and has the YouTube Data API v3 enabled
- **Bot Not Responding**: Check that your Discord token is correct and the bot has proper permissions

### Required Permissions

Ensure your bot has the following permissions:

- Read Messages/View Channels
- Send Messages
- Embed Links
- Attach Files
- Manage Threads
- Read Message History

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [discord.py](https://github.com/Rapptz/discord.py) - Discord API wrapper for Python
- [pdf2image](https://github.com/Belval/pdf2image) - PDF to image conversion library
- [google-api-python-client](https://github.com/googleapis/google-api-python-client) - Google API Client Library for Python

## Install FFmpeg

winget install "FFmpeg (Essentials Build)"
choco install ffmpeg

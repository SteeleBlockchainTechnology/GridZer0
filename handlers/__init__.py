# handlers/__init__.py
#
# This file makes the handlers directory a Python package, allowing its modules to be imported
# using the 'handlers' namespace. It enables the bot.py file to import handler modules with:
# from handlers.pdf_handler import handle_pdf
# from handlers.youtube_handler import handle_youtube
# from handlers.mp4_handler import handle_mp4
#
# The handlers package contains specialized modules for processing different types of content:
# - pdf_handler.py: Processes PDF files uploaded to a designated Discord channel
# - youtube_handler.py: Processes YouTube links posted to a designated Discord channel
# - mp4_handler.py: Processes Google Drive MP4 videos posted to a designated Discord channel
#
# Each handler module contains a main handler function that is called by bot.py when
# a message is posted in the appropriate channel.
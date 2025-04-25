# handlers/referral_handler.py
#
# Handler for referral links in Discord that creates rich embeds

import os
import re
import time
import random
import json
import hashlib
import discord
import requests
import asyncio
import logging
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from pathlib import Path
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('referral_handler')

# Import Selenium components for headless browser
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    logger.warning("Selenium not installed. Headless browser functionality will not be available.")
    SELENIUM_AVAILABLE = False
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('referral_handler')

# Import Selenium components for headless browser
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    logger.warning("Selenium not installed. Headless browser functionality will not be available.")
    SELENIUM_AVAILABLE = False
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('referral_handler')

# Regular expression to match URLs
URL_REGEX = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'

# No longer using cache as per user request

# List of user agents to rotate through
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Android 14; Mobile; rv:123.0) Gecko/123.0 Firefox/123.0',
]

# List of referrer URLs to rotate through
REFERRERS = [
    'https://www.google.com/',
    'https://www.bing.com/',
    'https://www.yahoo.com/',
    'https://www.reddit.com/',
    'https://www.facebook.com/',
    'https://www.twitter.com/',
    'https://www.instagram.com/',
]

# Function removed as caching is no longer used

# Function removed as caching is no longer used

async def fetch_with_standard_request(url):
    """Attempt to fetch website data using standard requests"""
    # Select a random user agent and referrer
    user_agent = random.choice(USER_AGENTS)
    referrer = random.choice(REFERRERS)
    
    # Comprehensive browser-like headers
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'Referer': referrer,
        'Cookie': f'session={hashlib.md5(str(time.time()).encode()).hexdigest()}; has_visited=true; consent=true'
    }
    
    try:
        # Add a small random delay to avoid rate limiting
        await asyncio.sleep(random.uniform(0.5, 2))
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Standard request failed: {e}")
        return None

async def fetch_with_mobile_emulation(url):
    """Attempt to fetch website data emulating a mobile device"""
    # Select a mobile user agent
    mobile_agents = [ua for ua in USER_AGENTS if 'Mobile' in ua]
    user_agent = random.choice(mobile_agents if mobile_agents else USER_AGENTS)
    
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'Referer': random.choice(REFERRERS),
        # Mobile-specific headers
        'Viewport-Width': '412',
        'Width': '412',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    try:
        # Add a small random delay
        await asyncio.sleep(random.uniform(0.5, 2))
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Mobile emulation request failed: {e}")
        return None

async def extract_metadata_from_html(html, url):
    """Extract metadata from HTML content"""
    if not html:
        return None
        
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract metadata
        title = None
        description = None
        image_url = None
        favicon = None
        
        # Get title
        if soup.title:
            title = soup.title.string
        
        # Try to get description from meta tags
        desc_tag = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        if desc_tag and 'content' in desc_tag.attrs:
            description = desc_tag['content']
        
        # Try to get image from meta tags
        image_tag = soup.find('meta', attrs={'property': 'og:image'}) or soup.find('meta', attrs={'name': 'twitter:image'})
        if image_tag and 'content' in image_tag.attrs:
            image_url = image_tag['content']
            
            # If image URL is relative, make it absolute
            if image_url and not image_url.startswith(('http://', 'https://')):
                image_url = urljoin(url, image_url)
        
        # If no OpenGraph image, try to find a prominent image
        if not image_url:
            # Look for large images in the page
            for img in soup.find_all('img', src=True):
                # Skip tiny images, icons, etc.
                if img.get('width') and int(img.get('width')) > 200:
                    image_url = img['src']
                    if not image_url.startswith(('http://', 'https://')):
                        image_url = urljoin(url, image_url)
                    break
        
        # Get favicon
        favicon_tag = soup.find('link', rel='icon') or soup.find('link', rel='shortcut icon')
        if favicon_tag and 'href' in favicon_tag.attrs:
            favicon = favicon_tag['href']
            # If favicon URL is relative, make it absolute
            if favicon and not favicon.startswith(('http://', 'https://')):
                favicon = urljoin(url, favicon)
        
        # Get domain name for display
        domain = urlparse(url).netloc
        
        return {
            'title': title,
            'description': description,
            'image': image_url,
            'favicon': favicon,
            'domain': domain,
            'url': url
        }
    except Exception as e:
        print(f"Error extracting metadata: {e}")
        return None

async def fetch_with_selenium(url):
    """Attempt to fetch website data using Selenium headless browser"""
    if not SELENIUM_AVAILABLE:
        logger.warning("Selenium not available for headless browser fetching")
        return None
        
    try:
        # Configure Chrome options for headless operation
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')  # Use new headless mode
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Add random user agent
        user_agent = random.choice(USER_AGENTS)
        chrome_options.add_argument(f'--user-agent={user_agent}')
        
        # Add additional browser-like settings to avoid detection
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Add referrer
        referrer = random.choice(REFERRERS)
        chrome_options.add_argument(f'--referrer={referrer}')
        
        # Add window size to mimic real browser
        chrome_options.add_argument('--window-size=1920,1080')
        
        logger.info(f"Initializing Selenium with user agent: {user_agent[:30]}...")
        
        # Create a service using ChromeDriverManager for automatic driver installation
        service = Service(ChromeDriverManager().install())
        
        # Create a new WebDriver instance with service and options
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set page load timeout
        driver.set_page_load_timeout(30)  # Increased timeout for complex sites
        
        # Execute CDP commands to modify navigator properties to avoid detection
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'es']});
            """
        })
        
        # Add a small random delay to avoid detection
        await asyncio.sleep(random.uniform(2, 5))  # Increased delay
        
        # Special handling for known problematic domains
        domain = urlparse(url).netloc
        is_blofin = 'blofin.com' in domain
        
        try:
            logger.info(f"Navigating to URL with Selenium: {url}")
            # Navigate to the URL
            driver.get(url)
            
            # Wait for the page to load (wait for body element)
            WebDriverWait(driver, 15).until(  # Increased wait time
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait to allow JavaScript to execute
            await asyncio.sleep(random.uniform(1, 3))
            
            # Special handling for blofin.com
            if is_blofin:
                # Try to interact with the page to bypass protection
                try:
                    # Scroll down to simulate user interaction
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                    await asyncio.sleep(1)
                    driver.execute_script("window.scrollTo(0, 0);")
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.warning(f"Error during page interaction: {e}")
            
            # Get the page source after JavaScript execution
            html = driver.page_source
            
            if "403 Forbidden" in html or "Access Denied" in html:
                logger.warning(f"Selenium received 403 Forbidden response for: {url}")
                return None
                
            logger.info(f"Successfully fetched page with Selenium: {url}")
            return html
            
        except TimeoutException:
            logger.warning(f"Timeout while loading page with Selenium: {url}")
            return None
        except Exception as e:
            logger.error(f"Error during Selenium page load: {e}")
            return None
        finally:
            # Always close the browser
            driver.quit()
            
    except WebDriverException as e:
        logger.error(f"WebDriver error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error with Selenium: {e}")
        return None

async def get_website_metadata(url):
    """Get metadata from a website for rich embedding using multiple methods"""
    # Parse the domain
    domain = urlparse(url).netloc
    
    # Try standard request first
    html = await fetch_with_standard_request(url)
    metadata = await extract_metadata_from_html(html, url)
    
    # If standard request failed or returned incomplete metadata, try mobile emulation
    if not html or not metadata or not metadata.get('title'):
        logger.info(f"Standard request failed or incomplete for {url}, trying mobile emulation")
        html = await fetch_with_mobile_emulation(url)
        mobile_metadata = await extract_metadata_from_html(html, url)
        
        # Merge metadata, preferring mobile if it has more info
        if mobile_metadata:
            if not metadata:
                metadata = mobile_metadata
            else:
                # Update missing fields from mobile metadata
                for key in ['title', 'description', 'image']:
                    if not metadata.get(key) and mobile_metadata.get(key):
                        metadata[key] = mobile_metadata.get(key)
    
    # If standard and mobile requests failed, try Selenium headless browser
    if (not html or not metadata or not metadata.get('title')) and SELENIUM_AVAILABLE:
        logger.info(f"Mobile emulation failed or incomplete for {url}, trying Selenium headless browser")
        html = await fetch_with_selenium(url)
        selenium_metadata = await extract_metadata_from_html(html, url)
        
        # Use Selenium metadata if available
        if selenium_metadata:
            metadata = selenium_metadata
    
    # If we still couldn't get metadata, create basic metadata
    if not metadata or not metadata.get('title'):
        logger.warning(f"All fetch methods failed for {url}, using fallback metadata")
        # Create basic metadata with domain info
        
        # Special handling for blofin.com
        if 'blofin.com' in domain:
            metadata = {
                'title': f"Blofin - Crypto Exchange Platform",
                'description': "Blofin is a cryptocurrency exchange platform. This link appears to be a referral link. The website restricts automated access, but you can click to visit directly.",
                'image': None,
                'favicon': None,
                'domain': domain,
                'url': url,
                'error': '403 Forbidden'
            }
        else:
            metadata = {
                'title': f"Visit {domain}",
                'description': "This website restricts automated access. Click the link to visit directly.",
                'image': None,
                'favicon': None,
                'domain': domain,
                'url': url,
                'error': '403 Forbidden'
            }
    
    return metadata

async def create_referral_embed(url, metadata):
    """Create a rich embed for a referral link"""
    # Choose color based on whether there was an error
    color = discord.Color.red() if 'error' in metadata else discord.Color.blue()
    
    embed = discord.Embed(
        title=metadata['title'] or "Visit Website",
        description=metadata['description'] or "No description available",
        url=url,
        color=color
    )
    
    if metadata['image']:
        embed.set_image(url=metadata['image'])
    
    # Set footer with domain name and favicon
    footer_text = metadata['domain']
    if 'error' in metadata:
        footer_text += f" • {metadata['error']}"
    
    embed.set_footer(text=footer_text, icon_url=metadata['favicon'] if metadata['favicon'] else None)
    
    return embed

async def handle_referral(message, referral_channel_id):
    """Process referral links in messages"""
    # Only process messages in the designated referral channel
    if message.channel.id != int(referral_channel_id):
        return False
    
    # Look for URLs in the message
    matches = re.findall(URL_REGEX, message.content)
    if not matches:
        return False
    
    # Process the first URL found
    url = matches[0]
    domain = urlparse(url).netloc
    
    # Send initial processing message
    processing_msg = await message.channel.send(f"Processing referral link...")
    
    try:
        # Special handling for known problematic sites
        is_known_problematic = 'blofin.com' in domain
        if is_known_problematic:
            logger.info(f"Detected known problematic site: {domain}")
            await processing_msg.edit(content=f"⚠️ Fetching preview for {domain} (this site is known to block automated access)...")
        
        # Get website metadata
        metadata = await get_website_metadata(url)
        
        # Create and send the embed
        embed = await create_referral_embed(url, metadata)
        
        # Update processing message if there was an error but we're still showing an embed
        if 'error' in metadata and metadata['error'] == '403 Forbidden':
            if 'blofin.com' in domain:
                await processing_msg.edit(content=f"⚠️ Blofin.com blocks automated access. This appears to be a referral link. Click to visit directly.")
            else:
                await processing_msg.edit(content=f"⚠️ This website blocks automated access, but you can still click the link to visit directly.")
            await message.channel.send(embed=embed)
        elif 'error' in metadata:
            await processing_msg.edit(content=f"⚠️ Limited preview available due to access restrictions.")
            await message.channel.send(embed=embed)
        else:
            # If no errors, delete the processing message and show the embed
            await message.channel.send(embed=embed)
            await processing_msg.delete()
        
        # Delete the original message with the link
        try:
            await message.delete()
        except discord.Forbidden:
            logger.warning("Bot lacks permission to delete messages.")
        except Exception as e:
            logger.error(f"Error deleting original message: {e}")
        
        return True
    except Exception as e:
        await processing_msg.edit(content=f"❌ Error processing referral link: {str(e)}")
        logger.error(f"Error processing referral link: {e}")
        return False
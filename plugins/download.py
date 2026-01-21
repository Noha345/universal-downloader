import os
import time
import math
import asyncio
import aiohttp
import re
from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified
from yt_dlp import YoutubeDL

# --- CONFIGURATION ---
# Create a folder named 'downloads' in the same directory
DOWNLOAD_PATH = "downloads/"
if not os.path.exists(DOWNLOAD_PATH): os.makedirs(DOWNLOAD_PATH)

# --- HELPER FUNCTIONS ---
def format_bytes(size):
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"

async def progress(current, total, message, start_time):
    now = time.time()
    diff = now - start_time
    if round(diff % 5.00) == 0 or current == total:
        if total == 0: return # Avoid division by zero
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
        estimated_total_time = elapsed_time + time_to_completion 

        if speed > 0:
            estimated_str = time.strftime('%H:%M:%S', time.gmtime(estimated_total_time / 1000))
        else:
            estimated_str = "00:00:00"
        
        progress_str = "[{0}{1}] {2}%\n".format(
            ''.join(["●" for i in range(math.floor(percentage / 10))]),
            ''.join(["○" for i in range(10 - math.floor(percentage / 10))]),
            round(percentage, 2))
            
        tmp = f"{progress_str}{format_bytes(current)} of {format_bytes(total)}\nSpeed: {format_bytes(speed)}/s\nETA: {estimated_str}"
        
        try:
            await message.edit_text(f"📤 **Uploading...**\n{tmp}")
        except MessageNotModified:
            pass 
        except Exception as e:
            pass

@Client.on_message(filters.regex(r"(https?://\S+)"))
async def download_handler(client, message):
    url = message.text.strip()
    # Reject non-http links to prevent errors
    if not url.startswith(("http://", "https://")): return

    status_msg = await message.reply_text("🔎 **Analysing Link...**")
    start_time = time.time()
    
    filename = None
    caption = "Downloaded Media"

    # --- 1. COOKIE CHECK ---
    # Many anime/adult sites require cookies to bypass "Are you 18?" or Cloudflare.
    # Put a 'cookies.txt' file in your bot's root folder to enable this.
    cookie_file = 'cookies.txt' if os.path.exists('cookies.txt') else None

    # --- 2. GOD MODE CONFIGURATION ---
    # This configuration is tuned for maximum compatibility across YouTube, Hianime, Hentaicity, etc.
    ydl_opts = {
        # Format: Try best video+audio (YouTube), fallback to best single file (Generic sites)
        'format': 'bestvideo+bestaudio/best', 
        
        # Filename template
        'outtmpl': f'{DOWNLOAD_PATH}%(title)s.%(ext)s',
        
        # Performance & Network
        'noplaylist': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'quiet': True,
        
        # Post-processing: Essential for HLS (m3u8) streams used by Anime sites
        'merge_output_format': 'mp4',
        
        # Headers: TRICK WEBSITES into thinking we are a real browser
        'http_headers': {
            'Referer': url, # Crucial for Hentaicity/Hianime
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
        
        # Advanced Extractor Args (The "Magic" Part)
        # This helps bypass Cloudflare on some sites
        'extractor_args': {
            'generic': {'impersonate': True},
        },
        
        # Cookies
        'cookiefile': cookie_file
    }

    try:
        await status_msg.edit_text("⬇️ **Downloading...**\n(This may take time for HLS streams)")
        
        # Run yt-dlp in a separate thread to not block the bot
        loop = asyncio.get_event_loop()
        
        # Define the download task
        def run_download():
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info, ydl.prepare_filename(info)

        # Execute download
        info, filename = await loop.run_in_executor(None, run_download)
        
        # Fix filename for merged files (mkv -> mp4)
        if not filename.endswith(".mp4") and os.path.exists(filename.rsplit(".", 1)[0] + ".mp4"):
            filename = filename.rsplit(".", 1)[0] + ".mp4"
            
        caption = info.get('title', caption)

        # Check if file exists and is not empty
        if not filename or not os.path.exists(filename) or os.path.getsize(filename) == 0:
            raise Exception("File downloaded but empty (likely a protection block).")

        # --- UPLOAD ---
        await status_msg.edit_text("📤 **Uploading...**")
        
        # Determine upload method
        if filename.lower().endswith(('.mp4', '.mkv', '.webm', '.mov')):
            await client.send_video(
                message.chat.id, 
                video=filename, 
                caption=caption,
                supports_streaming=True, 
                progress=progress, 
                progress_args=(status_msg, start_time)
            )
        else:
            await client.send_document(
                message.chat.id, 
                document=filename, 
                caption=caption,
                progress=progress, 
                progress_args=(status_msg, start_time)
            )

        # Cleanup
        os.remove(filename)
        await status_msg.delete()

    except Exception as e:
        error_text = str(e)
        print(f"Download Error: {error_text}")
        
        # Friendly Error Messages
        if "403" in error_text:
            msg = "❌ **Access Denied (403).**\nThe website blocked the bot. Try adding a `cookies.txt` file."
        elif "drm" in error_text.lower():
            msg = "❌ **DRM Protected.**\nThis content is encrypted and cannot be downloaded."
        elif "browser" in error_text.lower() or "challenge" in error_text.lower():
            msg = "❌ **Cloudflare Block.**\nThe site is verifying browsers. I cannot bypass this right now."
        else:
            msg = f"❌ **Error:** {error_text[:200]}"
            
        await status_msg.edit_text(msg)
        if filename and os.path.exists(filename): os.remove(filename)

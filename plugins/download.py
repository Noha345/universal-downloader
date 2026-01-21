import os
import sys
import subprocess
import time
import math
import asyncio
from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified

# --- 0. FORCE UPDATE ---
try:
    print("cw Checking for yt-dlp updates...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
    import yt_dlp.version
    print(f"✅ yt-dlp version: {yt_dlp.version.__version__}")
except Exception as e:
    print(f"⚠️ Update Warning: {e}")

from yt_dlp import YoutubeDL

# --- CONFIGURATION ---
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
        if total == 0: return 
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
    if not url.startswith(("http://", "https://")): return

    status_msg = await message.reply_text("🔎 **Analysing Link...**")
    start_time = time.time()
    
    filename = None
    caption = "Downloaded Media"

    # --- 1. CONFIGURATION (TV MODE BYPASS) ---
    ydl_opts = {
        'format': 'best', 
        'outtmpl': f'{DOWNLOAD_PATH}%(title)s.%(ext)s',
        
        # Network fixes
        'source_address': '0.0.0.0', 
        'socket_timeout': 30,
        
        # --- THE FIX: USE TV CLIENT ---
        # We pretend to be a Smart TV. This client is highly resistant to IP bans
        # and usually does not require Sign-In or Cookies.
        'extractor_args': {
            'youtube': {
                'player_client': ['tv', 'android', 'ios']
            }
        },
        
        # CRITICAL: Prevent the 'NoneType' crash by defining headers explicitly
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        },

        # Ensure we do NOT use the broken cookies
        'cookiefile': None,

        # Standard settings
        'noplaylist': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'quiet': True,
        'ignoreerrors': True,
        
        # Post Processing
        'writethumbnail': True,
        'postprocessors': [
            {'key': 'EmbedThumbnail'},
            {'key': 'FFmpegMetadata'},
        ],
        'merge_output_format': 'mp4',
    }

    try:
        await status_msg.edit_text("⬇️ **Downloading...**\n(Mode: TV Client Bypass 📺)")
        
        loop = asyncio.get_event_loop()
        
        def run_download():
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info, ydl.prepare_filename(info)

        info, filename = await loop.run_in_executor(None, run_download)
        
        # Handle filename quirks
        if not filename.endswith(".mp4"):
            base_name = filename.rsplit(".", 1)[0]
            if os.path.exists(base_name + ".mp4"):
                filename = base_name + ".mp4"
            
        caption = info.get('title', caption)

        if not filename or not os.path.exists(filename):
             raise Exception("File not found.")
        if os.path.getsize(filename) == 0:
            raise Exception("File is empty (IP Banned).")

        # --- UPLOAD ---
        await status_msg.edit_text("📤 **Uploading...**")
        
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

        os.remove(filename)
        await status_msg.delete()

    except Exception as e:
        error_text = str(e)
        print(f"Download Error: {error_text}")
        
        if "Sign in" in error_text:
            msg = "❌ **Blocked.**\nYouTube has completely banned this server IP."
        elif "NoneType" in error_text:
             msg = "❌ **Internal Error.**\nTry restarting the bot."
        else:
            msg = f"❌ **Error:** {error_text[:200]}"
            
        await status_msg.edit_text(msg)
        if filename and os.path.exists(filename): os.remove(filename)
   

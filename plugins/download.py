import os
import sys
import subprocess
import time
import math
import asyncio
from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified

# --- 0. CRITICAL: FORCE UPDATE YT-DLP ON BOOT ---
# This block runs every time the bot restarts to ensure you have the LATEST version.
# This fixes the "n challenge" and "Empty File" errors.
try:
    print("🔄 Checking for yt-dlp updates...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
    print("✅ yt-dlp is up to date!")
except Exception as e:
    print(f"⚠️ Update failed: {e}")

# Import yt-dlp AFTER updating
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

    # --- 1. COOKIE CHECK (CRITICAL FOR 403 ERRORS) ---
    cookie_file = "cookies.txt"
    if os.path.exists(cookie_file):
        pass 
    elif "COOKIES_FILE_CONTENT" in os.environ:
        try:
            with open(cookie_file, "w") as f:
                f.write(os.environ["COOKIES_FILE_CONTENT"])
        except:
            pass
    else:
        cookie_file = None 

    # --- 2. ROBUST CONFIGURATION ---
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best', 
        'outtmpl': f'{DOWNLOAD_PATH}%(title)s.%(ext)s',
        
        # --- NETWORK STABILITY ---
        'source_address': '0.0.0.0', 
        'socket_timeout': 30,
        
        # --- ANTI-BOT SETTINGS ---
        # We removed the "Android" force because it broke your specific video.
        # Instead, we rely on the Auto-Update (top of script) to fix the "n challenge".
        
        'noplaylist': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'quiet': True,
        
        # --- POST PROCESSING ---
        'writethumbnail': True,
        'postprocessors': [
            {'key': 'EmbedThumbnail'},
            {'key': 'FFmpegMetadata'},
        ],
        'merge_output_format': 'mp4',
        
        'cookiefile': cookie_file
    }

    try:
        await status_msg.edit_text("⬇️ **Downloading...**\n(Fresh tools installed 🛠️)")
        
        loop = asyncio.get_event_loop()
        
        def run_download():
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info, ydl.prepare_filename(info)

        info, filename = await loop.run_in_executor(None, run_download)
        
        # Filename correction for merged files
        if not filename.endswith(".mp4"):
            base_name = filename.rsplit(".", 1)[0]
            if os.path.exists(base_name + ".mp4"):
                filename = base_name + ".mp4"
            
        caption = info.get('title', caption)

        # --- VALIDATION ---
        if not filename or not os.path.exists(filename):
             raise Exception("File not found.")
        if os.path.getsize(filename) == 0:
            raise Exception("Empty File Error (Bot Detected). Try adding cookies.")

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
        
        if "403" in error_text:
            msg = "❌ **Access Denied.**\nI need a `cookies.txt` file to download this."
        elif "empty" in error_text.lower():
             msg = "❌ **Empty File.**\nYouTube throttled the connection. Retrying might work."
        else:
            msg = f"❌ **Error:** {error_text[:200]}"
            
        await status_msg.edit_text(msg)
        if filename and os.path.exists(filename): os.remove(filename)
            

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

from yt_dlp import YoutubeDL, DownloadError

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

    # --- 1. PREPARE COOKIES ---
    cookie_file = "cookies.txt"
    has_cookies = False
    if "COOKIES_FILE_CONTENT" in os.environ:
        with open(cookie_file, "w") as f: 
            f.write(os.environ["COOKIES_FILE_CONTENT"])
        has_cookies = True
    elif os.path.exists(cookie_file):
        has_cookies = True

    # --- 2. INTELLIGENT CLIENT LIST ---
    attempts = [
        # Mode 1: Android (Most reliable for bypassing bans)
        {'client': 'android', 'cookies': False, 'format': 'bestvideo+bestaudio/best'},
        # Mode 2: iOS (Good alternative)
        {'client': 'ios', 'cookies': False, 'format': 'bestvideo+bestaudio/best'},
        # Mode 3: TV (Fallback for harsh IP bans)
        {'client': 'tv', 'cookies': False, 'format': 'bestvideo+bestaudio/best'},
        # Mode 4: Web (Last resort - needs cookies)
        {'client': 'web', 'cookies': True, 'format': 'bestvideo+bestaudio/best'},
        # Mode 5: FALLBACK (Low Quality / Worst) - If everything else fails
        {'client': 'android', 'cookies': False, 'format': 'worst'}, 
    ]

    success = False
    last_error = ""

    # --- 3. THE LOOP ---
    for config in attempts:
        if success: break
        
        use_cookie_file = cookie_file if (config['cookies'] and has_cookies) else None
        client_name = config['client']
        fmt_str = config['format']

        try:
            await status_msg.edit_text(f"⬇️ **Trying {client_name.upper()} Mode...**\nFormat: {fmt_str}")
            print(f"🔄 Attempting: {client_name} (Cookies: {use_cookie_file}) | Format: {fmt_str}")

            ydl_opts = {
                # FIX: Broader format selector to catch separate streams
                'format': fmt_str,
                'outtmpl': f'{DOWNLOAD_PATH}%(title)s.%(ext)s',
                'source_address': '0.0.0.0', 
                'socket_timeout': 30,
                
                # Force specific client
                'extractor_args': {
                    'youtube': {
                        'player_client': [client_name]
                    }
                },

                'noplaylist': True,
                'geo_bypass': True,
                'nocheckcertificate': True,
                'quiet': True,
                'ignoreerrors': True, # Prevent crashing on individual format errors
                
                # Thumbnail & Metadata
                'writethumbnail': True,
                'postprocessors': [
                    {'key': 'EmbedThumbnail'},
                    {'key': 'FFmpegMetadata'},
                ],
                'merge_output_format': 'mp4',
                
                'cookiefile': use_cookie_file
            }

            loop = asyncio.get_event_loop()
            
            def run_download():
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    return info, ydl.prepare_filename(info)

            info, filename = await loop.run_in_executor(None, run_download)
            
            if not filename:
                 raise Exception("No filename returned.")
            
            # Filename correction
            if not filename.endswith(".mp4"):
                base_name = filename.rsplit(".", 1)[0]
                if os.path.exists(base_name + ".mp4"):
                    filename = base_name + ".mp4"

            # Verify file actually exists and has size
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                success = True
                caption = info.get('title', caption)
            else:
                raise Exception("Empty file generated.")

        except Exception as e:
            last_error = str(e)
            print(f"⚠️ {client_name} failed: {last_error}")
            continue

    # --- 4. FINISH ---
    try:
        if not success or not filename or not os.path.exists(filename):
            raise Exception(f"All modes failed. Last error: {last_error}")

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
        print(f"Final Error: {error_text}")
        
        if "requested format" in error_text.lower():
             msg = "❌ **Restricted Content.**\nThis video is likely Age-Restricted or Premium, and the bot cannot access it with the current server IP/Cookies."
        else:
             msg = f"❌ **Error:** {error_text[:200]}"

        await status_msg.edit_text(msg)
        if filename and os.path.exists(filename): os.remove(filename)

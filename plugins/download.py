import os
import time
import math
import asyncio
import aiohttp
import re
from pyrogram import Client, filters
from yt_dlp import YoutubeDL

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
    # Update every 5 seconds to avoid 'Message ID Invalid' or FloodWait
    if round(diff % 5.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
        estimated_total_time = elapsed_time + time_to_completion

        estimated_str = time.strftime('%H:%M:%S', time.gmtime(estimated_total_time / 1000))

        progress_str = "[{0}{1}] {2}%\n".format(
            ''.join(["●" for i in range(math.floor(percentage / 10))]),
            ''.join(["○" for i in range(10 - math.floor(percentage / 10))]),
            round(percentage, 2))
            
        tmp = progress_str + \
              f"{format_bytes(current)} of {format_bytes(total)}\n" + \
              f"Speed: {format_bytes(speed)}/s\n" + \
              f"ETA: {estimated_str}"
              
        try:
            # Wrapped in try-except to solve the Render log edit errors
            await message.edit_text(f"📤 **Uploading...**\n{tmp}")
        except:
            pass

# --- MAIN LOGIC ---

@Client.on_message(filters.text & ~filters.command("start"))
async def download_handler(client, message):
    url = message.text.strip()
    if not url.startswith(("http://", "https://")):
        return

    status_msg = await message.reply_text("🔎 **Processing URL...**")
    start_time = time.time()
    
    DOWNLOAD_PATH = "downloads/"
    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)

    filename = None
    caption = "Downloaded Media"
    
    try:
        # STRATEGY 1: yt-dlp (Media Sites)
        ydl_opts = {
            # Forced MP4/M4A for Telegram streaming compatibility
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': f'{DOWNLOAD_PATH}%(title)s.%(ext)s',
            'merge_output_format': 'mp4', 
            'noplaylist': True,
            'quiet': True,
        }

        # SMART COOKIE CHECK: Mandatory for Render to bypass 'Sign in' error
        if os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'
        
        try:
            await status_msg.edit_text("⬇️ **Downloading via Media Engine...**")
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                # Correcting path if merged into mp4
                if not filename.endswith(".mp4") and os.path.exists(filename.rsplit(".", 1)[0] + ".mp4"):
                    filename = filename.rsplit(".", 1)[0] + ".mp4"
                
                caption = info.get('title', 'Downloaded Media')
        
        except Exception as e:
            # STRATEGY 2: Direct Link Fallback
            await status_msg.edit_text("⬇️ **Media engine failed. Trying Direct Link...**")
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        fname = ""
                        if "Content-Disposition" in response.headers:
                            res = re.findall("filename=(.+)", response.headers["Content-Disposition"])
                            fname = res[0].strip('"') if res else url.split("/")[-1]
                        else:
                            fname = url.split("/")[-1]
                        
                        fname = fname.split("?")[0] if "?" in fname else fname
                        filename = os.path.join(DOWNLOAD_PATH, fname or "file")
                        
                        with open(filename, 'wb') as f:
                            while True:
                                chunk = await response.content.read(1024*1024)
                                if not chunk: break
                                f.write(chunk)
                    else:
                        raise Exception(f"Server returned {response.status}")

        # UPLOAD PHASE
        if filename and os.path.exists(filename):
            file_size = os.path.getsize(filename)
            
            # Bot API 2GB Limit Check
            if file_size > 2 * 1024 * 1024 * 1024:
                await status_msg.edit_text("❌ **File is too big!** (Max 2GB)")
                os.remove(filename)
                return

            await status_msg.edit_text("📤 **Uploading to Telegram...**")
            
            # Logic to force send_video for playable player format
            if filename.lower().endswith(('.mp4', '.mkv', '.webm', '.mov')):
                 await client.send_video(
                    chat_id=message.chat.id,
                    video=filename,
                    caption=caption,
                    supports_streaming=True, # Critical for instant playback
                    progress=progress, 
                    progress_args=(status_msg, start_time)
                )
            else:
                await client.send_document(
                    chat_id=message.chat.id,
                    document=filename,
                    caption=caption,
                    progress=progress,
                    progress_args=(status_msg, start_time)
                )
            
            # Cleanup server space
            if os.path.exists(filename):
                os.remove(filename)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ **Download Failed.**")

    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** `{str(e)}`")
        if filename and os.path.exists(filename):
            os.remove(filename)

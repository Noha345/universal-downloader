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
    if round(diff % 5.00) == 0 or current == total:
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
        except:
            pass

@Client.on_message(filters.text & ~filters.command("start"))
async def download_handler(client, message):
    url = message.text.strip()
    if not url.startswith(("http://", "https://")) or len(url) > 500: return

    status_msg = await message.reply_text("🔎 **Processing URL...**")
    start_time = time.time()
    DOWNLOAD_PATH = "downloads/"
    if not os.path.exists(DOWNLOAD_PATH): os.makedirs(DOWNLOAD_PATH)

    filename = None
    caption = "Downloaded Media"

    try:
        # STRATEGY: Masquerade as a Real Browser
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': f'{DOWNLOAD_PATH}%(title)s.%(ext)s',
            'merge_output_format': 'mp4',
            'noplaylist': True,
            'quiet': True,
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            
            # Standard Browser User Agent
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            
            'extractor_args': {
                # 1. Fix for YouTube (Keeps YouTube working)
                'youtube': {'player_client': ['android_creator']},
                # 2. Fix for Cloudflare Sites (Fixes HentaiHaven/others)
                'generic': {'impersonate': True}
            }
        }

        try:
            await status_msg.edit_text("⬇️ **Downloading...**")
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if not filename.endswith(".mp4") and os.path.exists(filename.rsplit(".", 1)[0] + ".mp4"):
                    filename = filename.rsplit(".", 1)[0] + ".mp4"
                caption = info.get('title', caption)

        except Exception as e:
            print(f"Media Download Error: {e}")
            try:
                await status_msg.edit_text(f"⬇️ **Engine Failed.**\nTrying Direct Link...")
            except:
                pass
            
            # Direct Link Fallback
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        fname = "file"
                        if "Content-Disposition" in response.headers:
                            res = re.findall("filename=(.+)", response.headers["Content-Disposition"])
                            if res: fname = res[0].strip('"')
                        filename = os.path.join(DOWNLOAD_PATH, fname)
                        with open(filename, 'wb') as f:
                            while True:
                                chunk = await response.content.read(1024*1024)
                                if not chunk: break
                                f.write(chunk)
                    else:
                        raise Exception("Direct Download Failed")

        # UPLOAD
        if filename and os.path.exists(filename) and os.path.getsize(filename) > 0:
            await status_msg.edit_text("📤 **Uploading...**")
            if filename.lower().endswith(('.mp4', '.mkv', '.webm', '.mov')):
                await client.send_video(
                    message.chat.id, video=filename, caption=caption,
                    supports_streaming=True, progress=progress, progress_args=(status_msg, start_time)
                )
            else:
                await client.send_document(
                    message.chat.id, document=filename, caption=caption,
                    progress=progress, progress_args=(status_msg, start_time)
                )
            os.remove(filename)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ **Download Failed.**\nThe website blocked the bot or the file is protected.")
            if filename and os.path.exists(filename): os.remove(filename)

    except Exception as e:
        error_text = str(e)
        if "Sign in to confirm" in error_text:
            error_text = "❌ **YouTube Blocked IP.**\nCookies are missing or invalid."
        elif "Cloudflare" in error_text or "403" in error_text:
             error_text = "❌ **Cloudflare Block.**\nImpersonation failed or cookies required."
        
        await message.reply_text(f"❌ **Error:** {error_text[:200]}")
        if filename and os.path.exists(filename): os.remove(filename)
            

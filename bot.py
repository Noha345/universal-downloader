import os
import sys
import subprocess
import asyncio
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.errors import MessageNotModified

# --- 1. FORCE UPDATE (Must happen first) ---
try:
    print("cw Checking for yt-dlp updates...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
    import yt_dlp.version
    print(f"✅ yt-dlp version: {yt_dlp.version.__version__}")
except Exception as e:
    print(f"⚠️ Update Warning: {e}")

# Import after update
from yt_dlp import YoutubeDL

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", "12345"))     # REPLACE OR SET ENV VAR
API_HASH = os.environ.get("API_HASH", "your_hash") # REPLACE OR SET ENV VAR
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_token") # REPLACE OR SET ENV VAR

DOWNLOAD_PATH = "downloads/"
if not os.path.exists(DOWNLOAD_PATH): os.makedirs(DOWNLOAD_PATH)

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- WEB SERVER (Keeps Render Happy) ---
async def web_server():
    async def handle(request):
        return web.Response(text="Bot is running!")
    
    server = web.Application()
    server.router.add_get("/", handle)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("✅ Web Server started on port 8080")

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
    # (Existing progress code...)
    import time
    now = time.time()
    diff = now - start_time
    if round(diff % 5.00) == 0 or current == total:
        if total == 0: return 
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        estimated_str = "00:00:00" # Simplified for brevity
        
        try:
            await message.edit_text(f"📤 **Uploading...**\n{format_bytes(current)} of {format_bytes(total)}")
        except:
            pass

@app.on_message(filters.regex(r"(https?://\S+)"))
async def download_handler(client, message):
    import time
    url = message.text.strip()
    status_msg = await message.reply_text("🔎 **Analysing Link...**")
    start_time = time.time()
    
    # --- CLIENT CONFIG ---
    # Using iOS mode as it is the most stable without Node.js
    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{DOWNLOAD_PATH}%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'extractor_args': {'youtube': {'player_client': ['ios']}} 
    }

    try:
        await status_msg.edit_text("⬇️ **Downloading...**")
        
        loop = asyncio.get_event_loop()
        def run_download():
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info, ydl.prepare_filename(info)

        info, filename = await loop.run_in_executor(None, run_download)
        
        if not filename: raise Exception("Download failed")
        
        # Filename fix
        if not filename.endswith(".mp4") and os.path.exists(filename.rsplit(".", 1)[0] + ".mp4"):
            filename = filename.rsplit(".", 1)[0] + ".mp4"

        await status_msg.edit_text("📤 **Uploading...**")
        await client.send_video(message.chat.id, video=filename, caption=info.get('title', 'Video'))
        
        os.remove(filename)
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)[:200]}")
        if filename and os.path.exists(filename): os.remove(filename)

# --- MAIN ENTRY POINT ---
async def main():
    print("🤖 Starting Bot...")
    await app.start()
    print("✅ Bot Started!")
    
    # Start Web Server for Render
    await web_server()
    
    # Keep the script running
    await idle()
    await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

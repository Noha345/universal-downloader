import os
import sys
import shutil
import psutil
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

# 1. Get Admin ID safely
# We treat it as a list so you can eventually add multiple admins if you want
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

# --- HELPER: Human Readable File Sizes ---
def humanbytes(size):
    if not size:
        return "0B"
    power = 2**10
    n = 0
    dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + dic_powerN[n] + 'B'

# --- COMMAND: /stats ---
@Client.on_message(filters.command("stats") & filters.user(ADMIN_ID))
async def stats_command(client: Client, message: Message):
    status_msg = await message.reply_text("🔄 **Checking Server Health...**")
    
    # 1. Disk Usage (Storage)
    total, used, free = shutil.disk_usage(".")
    disk_usage = f"{humanbytes(used)} used / {humanbytes(total)} total"
    
    # 2. RAM Usage (Memory)
    ram = psutil.virtual_memory()
    ram_usage = f"{humanbytes(ram.used)} / {humanbytes(ram.total)} ({ram.percent}%)"
    
    # 3. CPU Usage
    cpu_usage = f"{psutil.cpu_percent()}%"
    
    # 4. Uptime (Optional simple calculation)
    # Getting real uptime is complex in Docker, so we skip it for simplicity
    
    msg = (
        "🤖 **System Status**\n\n"
        f"💾 **Disk:** `{disk_usage}`\n"
        f"🧠 **RAM:** `{ram_usage}`\n"
        f"⚙️ **CPU:** `{cpu_usage}`\n\n"
        "✅ Bot is running smoothly."
    )
    
    await status_msg.edit_text(msg)

# --- COMMAND: /log ---
@Client.on_message(filters.command("log") & filters.user(ADMIN_ID))
async def log_command(client: Client, message: Message):
    # This sends the cookies.txt file to you. 
    # It serves as a good debug check to see if cookies are actually on the server.
    
    if os.path.exists("cookies.txt"):
        await message.reply_document(
            document="cookies.txt", 
            caption="🍪 **Debug:** Here is your active Cookies file."
        )
    else:
        await message.reply_text("❌ **No cookies.txt found on server.**")

# --- COMMAND: /restart ---
@Client.on_message(filters.command("restart") & filters.user(ADMIN_ID))
async def restart_command(client: Client, message: Message):
    await message.reply_text("🔄 **Restarting Bot...**\nWait 15-30 seconds.")
    
    # Restart the current process
    # This works on Render/VPS by killing the script and letting the container restart it,
    # or re-executing the python command directly.
    os.execl(sys.executable, sys.executable, "main.py")

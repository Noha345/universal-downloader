import os
import asyncio
from pyrogram import Client, idle
from aiohttp import web

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Initialize the Client
app = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")
)

# --- WEB SERVER FOR HEALTH CHECKS ---
async def web_server():
    async def handle(request):
        return web.Response(text="Bot is running!")

    app = web.Application()
    app.add_routes([web.get('/', handle)])
    return app

async def start_services():
    # 1. Start the Telegram Bot
    print("Starting Telegram Bot...")
    await app.start()

    # 2. Start the Web Server on the Render PORT
    print("Starting Web Server...")
    port = int(os.environ.get("PORT", 8080)) # Default to 8080 if not set
    
    # Create the web runner
    runner = web.AppRunner(await web_server())
    await runner.setup()
    
    # Bind to 0.0.0.0 so external services can reach it
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    print(f"Server live at http://0.0.0.0:{port}")
    
    # 3. Idle - Keep the script running
    await idle()
    
    # 4. Stop gracefully
    await app.stop()

if __name__ == "__main__":
    # Run the async loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_services())

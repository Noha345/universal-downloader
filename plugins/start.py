from pyrogram import Client, filters

@Client.on_message(filters.command("start"))
async def start_command(client, message):
    welcome_text = (
        "👋 **Hello! I am your Universal Downloader Bot.**\n\n"
        "Send me any supported link (YouTube, Twitter, Instagram, Direct Links), "
        "and I will download it for you.\n\n"
        "**Note:** I can upload files up to 2GB."
    )
    await message.reply_text(welcome_text)

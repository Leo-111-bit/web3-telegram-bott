import os
import sys
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from groq import Groq

# 1. Environment Config Validation
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

if not TELEGRAM_BOT_TOKEN or not GROQ_API_KEY:
    logging.error("CRITICAL: Missing TELEGRAM_BOT_TOKEN or GROQ_API_KEY.")
    sys.exit(1)

# 2. Initialization
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

# A simple in-memory storage dictionary to map Telegram usernames to their chat IDs
# To work, users must have interacted with the bot at least once so it captures their ID
user_registry = {}

SYSTEM_INSTRUCTION = """
You are King Leo, an elite, highly knowledgeable AI Assistant. 
You can answer questions about any topic in the world, handle general knowledge, or engage in friendly, non-explicit banter.

Rules:
1. Detect and adapt automatically to whatever language the user speaks (English, Pidgin, Yoruba, etc.) and reply natively.
2. NEVER mention or print any warning phrases about seed phrases or private keys unless explicitly asked about security. Keep responses clean.
3. You must append the phrase "KINGLEO BOT" to the very end of your response, regardless of what the user asked.
"""

# 3. Message Handlers
@dp.message(CommandStart())
async def handle_start_command(message: types.Message):
    # Track user ID when they interact privately or join
    if message.from_user.username:
        user_registry[f"@{message.from_user.username.lower()}"] = message.from_user.id
    
    await message.reply("Welcome to Web3 Brain AI!\n\nI am King Leo, your elite AI assistant. Ask me anything! KINGLEO BOT")

@dp.message(Command("pm"))
async def handle_private_message_command(message: types.Message):
    """
    Usage in group or private: /pm @username Your secret message here
    """
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply("Usage format: /pm @username Your message text KINGLEO BOT")
        return

    target_username = args[1].lower()
    text_to_send = args[2]

    # Look up the internal Telegram chat ID from our active user tracking list
    target_chat_id = user_registry.get(target_username)

    if not target_chat_id:
        await message.reply(
            f"Cannot send message to {args[1]}. "
            f"The user must open a private DM and click /start with me first so I can capture their ID! KINGLEO BOT"
        )
        return

    try:
        await bot.send_message(chat_id=target_chat_id, text=f"{text_to_send}\n\n[Direct Admin PM] KINGLEO BOT")
        await message.reply(f"Successfully sent private message to {args[1]}! KINGLEO BOT")
    except Exception as e:
        logging.error(f"Failed to send direct message: {e}")
        await message.reply(f"Failed to DM user. They might have blocked the bot. KINGLEO BOT")

@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text:
        return

    # Track username mappings dynamically as people talk in the group chat
    if message.from_user.username:
        user_registry[f"@{message.from_user.username.lower()}"] = message.from_user.id

    bot_info = await bot.get_me()
    bot_username = f"@{bot_info.username}"
    
    is_private = message.chat.type == "private"
    is_tagged = bot_username in message.text
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id

    if is_private or is_tagged or is_reply_to_bot:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        clean_prompt = message.text.replace(bot_username, "").strip()
        
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": clean_prompt if clean_prompt else "Hello!"}
                ],
                temperature=0.7,
            )
            
            reply_text = response.choices[0].message.content
            if reply_text:
                reply_text = reply_text.strip()
                if not reply_text.endswith("KINGLEO BOT"):
                    reply_text += " KINGLEO BOT"
                    
                await message.reply(reply_text, parse_mode=None)
                
        except Exception as e:
            logging.error(f"Groq API Error: {e}")
            await message.reply("Sorry, I encountered a network error. Please try again! KINGLEO BOT")

# 4. Dummy Web Server to stop Render from killing the bot
async def home_page(request):
    return web.Response(text="KingLeo Engine is Online and Running Fine!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", home_page)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Render dummy port listener active on port {port}")

# 5. Main Execution Loop
async def main():
    logging.info("Clearing old webhook hooks from Telegram...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    await start_web_server()
    
    logging.info("KingLeo Polling Engine is now fully live!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

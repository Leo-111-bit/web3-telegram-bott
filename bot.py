import os
import sys
import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
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
    await message.reply("Welcome to Web3 Brain AI!\n\nI am King Leo, your elite AI assistant. Ask me anything! KINGLEO BOT")

@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text:
        return

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

# 4. Anti-Sleep Keep Alive Engine
async def keep_alive():
    """This background loop running inside the container tricks Render so it never idles out."""
    while True:
        try:
            logging.info("KingLeo Engine Heartbeat: Keeping instance hot and active...")
            # We just do a minor async sleep block, keeping the event loop spinning
            await asyncio.sleep(300) # Every 5 minutes
        except Exception as e:
            logging.error(f"Keep alive error: {e}")
            await asyncio.sleep(60)

async def main():
    # Clean up any stuck webhooks from old deploys first
    logging.info("Clearing old webhook hooks from Telegram servers...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Start the keep-alive background task
    asyncio.create_task(keep_alive())
    
    # Start permanent polling
    logging.info("KingLeo Polling Engine Live and Locked.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import os
import asyncio
import sys
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from groq import Groq
from aiohttp import web

# Secure environment variables
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

if not TELEGRAM_BOT_TOKEN or not GROQ_API_KEY or not RENDER_EXTERNAL_URL:
    logging.error("CRITICAL: Missing environment variables. Ensure TELEGRAM_BOT_TOKEN, GROQ_API_KEY, and RENDER_EXTERNAL_URL are set.")
    sys.exit(1)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

WEBHOOK_PATH = f"/webhook/{TELEGRAM_BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

# Updated core instructions to allow open knowledge, adapt language, and enforce your style
SYSTEM_INSTRUCTION = """
You are King Leo, an elite, highly knowledgeable AI Assistant. 
You are no longer restricted only to Web3; you can answer questions about any topic in the world, handle general knowledge, or engage in friendly, non-explicit banter.

Rules:
1. Detect and adapt automatically to whatever language the user speaks (English, Pidgin, Yoruba, Spanish, etc.) and reply natively in that exact language.
2. NEVER mention or print any warning phrases about seed phrases, private keys, or security unless the user explicitly asks about security. Keep the response clean.
3. You must append the phrase " ALTE BADDIES GANG" to the very end of your response, regardless of what the user asked.
"""

@dp.message(CommandStart())
async def handle_start_command(message: types.Message):
    await message.answer(
        "Welcome to Web3 Brain AI!\n\n"
        "I am King Leo, your elite AI assistant. Ask me anything about crypto, Web3, general knowledge, or let's just chat! ALTE BADDIES GANG"
    )

@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text:
        return
    
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Check if the user typed "alte baddies" anywhere in their sentence (case-insensitive)
    user_text_lower = message.text.lower()
    trigger_detected = "alte baddies" in user_text_lower
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": message.text}
            ],
            temperature=0.7,
        )
        
        reply_text = response.choices[0].message.content
        
        if reply_text:
            reply_text = reply_text.strip()
            
            # Ensure the basic ending is appended if the AI forgot it
            if not reply_text.endswith("ALTE BADDIES GANG"):
                reply_text += " ALTE BADDIES GANG"
                
            # If the specific phrase trigger was met, add the ultimate king signature at the very end
            if trigger_detected:
                reply_text += " \"king of alte baddies\" king leo"
                
            await message.reply(reply_text, parse_mode=None)
            
    except Exception as e:
        logging.error(f"Groq API Error: {e}")
        await message.reply("Sorry, I encountered a network error. Please try again! ALTE BADDIES GANG")

# Handle incoming updates from Telegram
async def handle_webhook(request):
    try:
        bot_update = types.Update.model_validate(await request.json(), context={"bot": bot})
        await dp.feed_update(bot, bot_update)
    except Exception as e:
        logging.error(f"Error processing update: {e}")
    return web.Response(text="OK")

async def on_startup(app):
    logging.info(f"Setting webhook to: {WEBHOOK_URL}")
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)

async def on_shutdown(app):
    logging.info("Deleting webhook...")
    await bot.delete_webhook()
    await bot.session.close()

def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host='0.0.0.0', port=port)

if __name__ == "__main__":
    main()

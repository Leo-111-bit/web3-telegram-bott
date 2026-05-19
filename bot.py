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
    logging.error("CRITICAL: Missing environment variables.")
    sys.exit(1)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

WEBHOOK_PATH = f"/webhook/{TELEGRAM_BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

# Clear instructions with the new simple signature requirement
SYSTEM_INSTRUCTION = """
You are King Leo, an elite, highly knowledgeable AI Assistant. 
You can answer questions about any topic in the world, handle general knowledge, or engage in friendly, non-explicit banter.

Rules:
1. Detect and adapt automatically to whatever language the user speaks (English, Pidgin, Yoruba, etc.) and reply natively.
2. NEVER mention or print any warning phrases about seed phrases or private keys unless explicitly asked about security. Keep responses clean.
3. You must append the phrase "KINGLEO BOT" to the very end of your response, regardless of what the user asked.
"""

@dp.message(CommandStart())
async def handle_start_command(message: types.Message):
    if message.chat.type == "private":
        await message.answer(
            "Welcome to Web3 Brain AI!\n\n"
            "I am King Leo, your elite AI assistant. Ask me anything! KINGLEO BOT"
        )

@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text:
        return

    bot_info = await bot.get_me()
    bot_username = f"@{bot_info.username}"
    
    is_private = message.chat.type == "private"
    is_tagged = bot_username in message.text
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id

    # Respond in DMs, group tags, or direct replies in groups
    if is_private or is_tagged or is_reply_to_bot:
        
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        
        # Clean the username tag out of the message text
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
                
                # Enforce the new signature ending cleanly
                if not reply_text.endswith("KINGLEO BOT"):
                    reply_text += " KINGLEO BOT"
                    
                await message.reply(reply_text, parse_mode=None)
                
        except Exception as e:
            logging.error(f"Groq API Error: {e}")
            await message.reply("Sorry, I encountered a network error. Please try again! KINGLEO BOT")

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

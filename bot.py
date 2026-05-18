import os
import asyncio
import sys
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from groq import Groq
from aiohttp import web

# Secure environment variables for Render hosting
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Safety check: Prevent startup crash if keys are missing
if not TELEGRAM_BOT_TOKEN:
    logging.error("CRITICAL ERROR: TELEGRAM_BOT_TOKEN is missing or improperly named in Render settings.")
    sys.exit(1)
if not GROQ_API_KEY:
    logging.error("CRITICAL ERROR: GROQ_API_KEY is missing or improperly named in Render settings.")
    sys.exit(1)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

SYSTEM_INSTRUCTION = """
You are a standalone, elite Web3 AI Assistant. 
Your job is to answer user questions regarding blockchain, cryptocurrency, decentralized finance (DeFi), smart contracts, gas fees, and ecosystems like Solana and Ethereum.

Rules:
1. Be highly accurate, professional, and clear.
2. Keep formatting simple so it transmits reliably. Do not use complex markdown tags.
3. SECURITY: Explicitly remind users to NEVER share their seed phrases or private keys.
"""

@dp.message(CommandStart())
async def handle_start_command(message: types.Message):
    welcome_text = (
        "Welcome to Web3 Brain AI!\n\n"
        "I am an artificial intelligence assistant dedicated to answering your cryptocurrency, blockchain, and decentralized finance questions.\n\n"
        "Ask me anything about tokens, smart contracts, gas fees, or ecosystems like Solana and Ethereum to get started!"
    )
    await message.answer(welcome_text)

@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text:
        return
    
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        # Using the absolute latest, super-fast Llama 3.3 model on Groq
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
            await message.reply(reply_text, parse_mode=None)
        else:
            await message.reply("I processed your request but couldn't generate an answer.")
            
    except Exception as e:
        logging.error(f"Error handling Groq API request: {e}")
        await message.reply("Sorry, the AI network encountered an error. Please try asking again!")

# Fake web server handler to satisfy Render's port requirements
async def handle_render_health_check(request):
    return web.Response(text="Bot is running smoothly!")

async def main():
    logging.info("Starting Web3 Standalone AI Bot on Groq Engine...")
    
    # Setup dummy web server on the port Render assigns us
    app = web.Application()
    app.router.add_get('/', handle_render_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    asyncio.create_task(site.start())
    logging.info(f"Dummy web server started on port {port}")
    
    # Start Telegram Polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")

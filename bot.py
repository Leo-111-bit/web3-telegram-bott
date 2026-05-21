import os
import sys
import logging
import asyncio
import aiohttp
import re
import random
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from groq import Groq

# 1. Environment Config
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
if not TELEGRAM_BOT_TOKEN or not GROQ_API_KEY:
    logging.error("CRITICAL: Missing credentials."); sys.exit(1)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

# Database
xp_database = {}

# 2. Frontend HTML
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>King Leo Premium Hub</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: sans-serif; background: radial-gradient(circle at top, #141a29 0%, #080b11 100%); color: #ffffff; padding: 20px; text-align: center; }
        .profile-capsule { background: rgba(0, 255, 204, 0.1); border: 1px solid #00ffcc; border-radius: 20px; padding: 20px; margin-bottom: 25px; }
        .xp-display { font-size: 32px; color: #00ffcc; font-weight: 900; }
        .calendar-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; background: rgba(22, 31, 44, 0.6); padding: 15px; border-radius: 16px; }
        .calendar-day { background: #0d121c; padding: 15px; border-radius: 10px; border: 1px solid #202b3d; cursor: pointer; }
        .calendar-day.claimed { background: #00ffcc; color: #000; font-weight: 900; }
        .sync-action-btn { background: linear-gradient(90deg, #ff007f, #7f00ff); color: white; padding: 15px; width: 100%; border: none; border-radius: 14px; margin-top: 25px; font-weight: 800; }
    </style>
</head>
<body>
    <div class="profile-capsule">
        <h2 id="user-display">🔥 LEO COIN HUB 🔥</h2>
        <div class="xp-display" id="user-total-xp">0000</div>
    </div>
    <div class="calendar-grid" id="calendar-box"></div>
    <button class="sync-action-btn" onclick="window.location.reload()">🔄 REFRESH STATS</button>
    <script>
        const tg = window.Telegram.WebApp; tg.expand();
        // Add sync logic here
    </script>
</body>
</html>
"""

# 3. Handlers
@dp.message(CommandStart())
async def handle_start_command(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚡ LAUNCH KING LEO HUB ⚡", web_app=WebAppInfo(url=WEB_APP_URL))]])
    await message.reply("🔥 **WELCOME TO THE KING LEO ECOSYSTEM** 🔥\n\nTap below to open your custom Web3 Dashboard!", reply_markup=kb)

@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text: return
    # Block other commands in groups
    if message.chat.type != "private" and message.text.startswith("/") and not message.text.startswith("/start"):
        return
        
    try:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        completion = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": message.text}],
            temperature=0.7
        )
        await message.reply(completion.choices[0].message.content)
    except Exception: pass

# 4. Web Server
async def frontend_mini_app_dashboard(request): return web.Response(text=DASHBOARD_HTML, content_type="text/html")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", frontend_mini_app_dashboard)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000))).start()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

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
        body { font-family: sans-serif; background: #080b11; color: #ffffff; padding: 20px; text-align: center; }
        .xp-display { font-size: 32px; color: #00ffcc; font-weight: 900; margin: 20px 0; }
        .sync-action-btn { background: #ff007f; color: white; padding: 15px; width: 100%; border: none; border-radius: 14px; margin-top: 25px; }
    </style>
</head>
<body>
    <h2>🔥 KING LEO XP STATS 🔥</h2>
    <div class="xp-display" id="user-total-xp">Loading...</div>
    <button class="sync-action-btn" onclick="window.location.reload()">🔄 REFRESH STATS</button>
    <script>
        const tg = window.Telegram.WebApp; tg.expand();
        fetch('/api/userstatus?user_id=' + tg.initDataUnsafe.user.id)
            .then(r => r.json()).then(d => document.getElementById('user-total-xp').innerText = d.xp + ' XP');
    </script>
</body>
</html>
"""

# 3. Handlers
def log_user_activity(user: types.User):
    user_id = str(user.id)
    if user_id not in xp_database:
        xp_database[user_id] = {"username": user.username or user.first_name, "xp": 10}
    xp_database[user_id]["xp"] += 1

@dp.message(CommandStart())
async def handle_start_command(message: types.Message):
    log_user_activity(message.from_user)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚡ LAUNCH KING LEO HUB ⚡", web_app=WebAppInfo(url=WEB_APP_URL))]])
    await message.reply("🔥 **WELCOME TO THE KING LEO ECOSYSTEM** 🔥\n\nTap below to open your Dashboard.", reply_markup=kb)

@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text: return
    
    # GROUP GATEKEEPER: Ignore all commands except /start
    if message.chat.type != "private" and message.text.startswith("/"):
        return

    # PRIVATE DM FUNCTION: Redirect to Stats only
    if message.chat.type == "private":
        log_user_activity(message.from_user)
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📊 CHECK YOUR XP STATUS", web_app=WebAppInfo(url=WEB_APP_URL))]])
        await message.reply("🚀 **KING LEO PORTAL**\n\nUse the button below to check your current XP.", reply_markup=kb)
        return

    # General AI Engine active only if tagged in groups
    bot_info = await bot.get_me()
    if f"@{bot_info.username}" in message.text:
        try:
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": message.text}],
                temperature=0.7
            )
            await message.reply(completion.choices[0].message.content)
        except Exception: pass

# 4. Web Server
async def frontend_mini_app_dashboard(request): return web.Response(text=DASHBOARD_HTML, content_type="text/html")
async def api_user_status(request): 
    uid = request.query.get("user_id")
    return web.json_response(xp_database.get(uid, {"xp": 0}))

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", frontend_mini_app_dashboard)
    app.router.add_get("/api/userstatus", api_user_status)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000))).start()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

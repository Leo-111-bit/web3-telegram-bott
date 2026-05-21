import sys
import logging
import asyncio
import os
import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.enums import ChatType

# --- CONFIG ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
if not TELEGRAM_BOT_TOKEN:
    logging.error("CRITICAL: Missing TELEGRAM_BOT_TOKEN.")
    sys.exit(1)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
xp_database = {}

def get_or_create_user(user: types.User):
    user_id = str(user.id)
    if user_id not in xp_database:
        xp_database[user_id] = {
            "username": user.username or user.first_name or "Trader",
            "xp": 0, "last_checkin": "", "checkin_days": []
        }
    return user_id

# --- BOT HANDLERS ---
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    get_or_create_user(message.from_user)
    app_url = WEB_APP_URL or "https://your-server.com"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐼 OPEN TRADING DESK", web_app=WebAppInfo(url=app_url))]
    ])
    await message.reply("🐼 **WELCOME TO PD CARD** 🐼\n\nTap below to claim your daily allocation in sequence!", reply_markup=kb)

# --- API ENDPOINTS ---
async def api_user_status(request):
    user_id = request.query.get("user_id")
    if user_id not in xp_database:
        xp_database[user_id] = {"username": "Trader", "xp": 0, "last_checkin": "", "checkin_days": []}
    return web.json_response(xp_database[user_id])

async def api_execute_checkin(request):
    data = await request.json()
    user_id = data.get("user_id")
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    
    if user_id not in xp_database:
        return web.json_response({"success": False, "message": "User not found!"})
        
    user_profile = xp_database[user_id]
    
    # Check if already claimed today
    if user_profile["last_checkin"] == today_str:
        return web.json_response({"success": False, "message": "🚫 You don claim today reward already!"})
    
    # Calculate next day
    next_day = len(user_profile["checkin_days"]) + 1
    
    if next_day > 30:
        return web.json_response({"success": False, "message": "✅ You don finish all 30 days!"})
        
    user_profile["xp"] += 10
    user_profile["last_checkin"] = today_str
    user_profile["checkin_days"].append(next_day)
    return web.json_response({"success": True, "message": f"💳 Success! You claimed Day {next_day}."})

async def api_leaderboard(request):
    data = sorted(xp_database.values(), key=lambda x: x["xp"], reverse=True)
    return web.json_response({"leaderboard": data})

# --- FRONTEND ---
async def frontend_mini_app_dashboard(request):
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { background: #0f172a; color: white; font-family: sans-serif; padding: 20px; }
        .card { background: rgba(30,41,59,0.7); padding: 20px; border-radius: 20px; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
        .day { padding: 10px; background: #334155; border-radius: 8px; text-align: center; cursor: pointer; }
        .day.done { background: #8b5cf6; }
        .day.next { border: 2px solid #22c55e; }
    </style>
</head>
<body>
    <div class="card">
        <h2 id="user-xp">0 XP</h2>
        <p>Wallet Balance</p>
    </div>
    <div class="card">
        <h3>30-Day Check-in</h3>
        <div class="grid" id="grid"></div>
    </div>
    <script>
        const tg = window.Telegram.WebApp; tg.expand();
        const userId = String(tg.initDataUnsafe.user?.id || 7777);
        
        async function sync() {
            const res = await fetch('/api/userstatus?user_id='+userId);
            const u = await res.json();
            document.getElementById('user-xp').innerText = u.xp + ' XP';
            const grid = document.getElementById('grid'); grid.innerHTML = '';
            const nextDay = u.checkin_days.length + 1;
            
            for(let i=1; i<=30; i++) {
                const done = u.checkin_days.includes(i);
                const el = document.createElement('div');
                el.className = 'day ' + (done ? 'done' : (i == nextDay ? 'next' : ''));
                el.innerText = 'D' + i;
                if(i == nextDay) el.onclick = claim;
                grid.appendChild(el);
            }
        }
        async function claim() {
            const res = await fetch('/api/checkin', {
                method: 'POST', body: JSON.stringify({user_id: userId}), 
                headers: {'Content-Type': 'application/json'}
            });
            const r = await res.json(); alert(r.message); sync();
        }
        sync();
    </script>
</body>
</html>"""
    return web.Response(text=html_content, content_type="text/html")

# --- SERVER ---
async def start_web_server():
    app = web.Application()
    app.router.add_get("/", frontend_mini_app_dashboard)
    app.router.add_get("/api/userstatus", api_user_status)
    app.router.add_get("/api/leaderboard", api_leaderboard)
    app.router.add_post("/api/checkin", api_execute_checkin)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000))).start()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import sys
import logging
import asyncio
import random
import datetime
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.enums import ChatType

# ==========================================
# 1. CONFIG & INIT
# ==========================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
if not TELEGRAM_BOT_TOKEN:
    logging.error("CRITICAL: Missing TELEGRAM_BOT_TOKEN.")
    sys.exit(1)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Memory Database
xp_database = {}

def get_or_create_user(user: types.User):
    user_id = str(user.id)
    if user_id not in xp_database:
        xp_database[user_id] = {
            "username": user.username or user.first_name, 
            "xp": 0, "checkin_days": [], "last_checkin": ""
        }
    return user_id

# ==========================================
# 2. BOT HANDLERS
# ==========================================
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    app_url = WEB_APP_URL or "https://your-server-url.com"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐼 OPEN PD CARD PRO", web_app=WebAppInfo(url=app_url))]
    ])
    await message.reply("🐼 **WELCOME TO PD CARD PRO** 🐼\n\nCheck your daily allocations here:", reply_markup=kb)

# ==========================================
# 3. API ENDPOINTS
# ==========================================
async def api_leaderboard_data(request):
    sorted_data = sorted(xp_database.values(), key=lambda x: x["xp"], reverse=True)
    return web.json_response({"leaderboard": sorted_data})

async def api_user_status(request):
    user_id = request.query.get("user_id")
    return web.json_response(xp_database.get(user_id, {"xp": 0, "checkin_days": []}))

async def api_execute_checkin(request):
    data = await request.json()
    user_id = data.get("user_id")
    day = int(data.get("day"))
    if user_id in xp_database and day not in xp_database[user_id]["checkin_days"]:
        xp_database[user_id]["checkin_days"].append(day)
        xp_database[user_id]["xp"] += 10
        return web.json_response({"success": True, "message": "💳 +10 XP Added!"})
    return web.json_response({"success": False, "message": "Already claimed!"})

# ==========================================
# 4. FRONTEND (FIXED INDENTATION)
# ==========================================
async def frontend_mini_app_dashboard(request):
    # Oga, notice how the HTML string starts flush left here:
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PD Card Pro</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
:root { --bg: #0f172a; --card-bg: rgba(30, 41, 59, 0.7); --accent: #8b5cf6; --text: #f8fafc; --glass: rgba(255, 255, 255, 0.05); }
body { font-family: sans-serif; background: var(--bg); color: var(--text); padding: 20px; }
.glass-card { background: var(--card-bg); backdrop-filter: blur(12px); border-radius: 24px; padding: 24px; margin-bottom: 20px; }
.slider-container { display: flex; overflow-x: auto; gap: 15px; padding: 10px 0; }
.panda-slide { min-width: 100px; height: 100px; background: var(--glass); border-radius: 20px; display: flex; align-items: center; justify-content: center; font-size: 30px; border: 2px solid var(--accent); }
.grid-container { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.day-item { background: var(--glass); padding: 10px; border-radius: 8px; text-align: center; }
.day-item.redeemed { background: var(--accent); }
</style>
</head>
<body>
<div class="glass-card">
    <h3 id="user-display">Trader</h3>
    <div id="user-total-xp" style="font-size: 32px; font-weight: 800;">0 XP</div>
</div>
<div class="glass-card">
    <div class="slider-container" id="panda-slider"></div>
</div>
<div class="glass-card">
    <div class="grid-container" id="calendar-box"></div>
</div>
<script>
const tg = window.Telegram.WebApp; tg.expand();
const userId = String(tg.initDataUnsafe.user?.id || 7777);
const slider = document.getElementById('panda-slider');
for(let i=1; i<=30; i++) slider.innerHTML += `<div class="panda-slide">🐼</div>`;

async function syncAllData() {
    const res = await fetch('/api/userstatus?user_id=' + userId);
    const user = await res.json();
    document.getElementById('user-total-xp').innerText = user.xp + ' XP';
    const cal = document.getElementById('calendar-box'); cal.innerHTML = '';
    for(let i=1; i<=30; i++) {
        const isClaimed = user.checkin_days.includes(i);
        cal.innerHTML += `<div class="day-item ${isClaimed ? 'redeemed' : ''}" onclick="claim(${i})">D${i}</div>`;
    }
}
async function claim(d) {
    await fetch('/api/checkin', {method:'POST', body:JSON.stringify({user_id:userId, day:d}), headers:{'Content-Type':'application/json'}});
    syncAllData();
}
window.onload = syncAllData;
</script>
</body>
</html>"""
    return web.Response(text=html_content, content_type="text/html")

# ==========================================
# 5. SERVER RUNNER
# ==========================================
async def start_web_server():
    app = web.Application()
    app.router.add_get("/", frontend_mini_app_dashboard)
    app.router.add_get("/api/userstatus", api_user_status)
    app.router.add_get("/api/leaderboard", api_leaderboard_data)
    app.router.add_post("/api/checkin", api_execute_checkin)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    await web.TCPSite(runner, "0.0.0.0", port).start()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

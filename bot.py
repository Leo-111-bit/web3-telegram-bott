import os
import sys
import logging
import asyncio
import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.enums import ChatType

# 1. Environment Config
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

if not TELEGRAM_BOT_TOKEN:
    logging.error("CRITICAL: Missing TELEGRAM_BOT_TOKEN.")
    sys.exit(1)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Active In-Memory Database Engine
xp_database = {}  

def get_or_create_user(user: types.User):
    user_id = str(user.id)
    username = user.username or user.first_name or f"Trader_{user_id[:5]}"
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    if user_id not in xp_database:
        xp_database[user_id] = {
            "username": username,
            "messages": 0,
            "xp": 0,
            "last_active": today,
            "last_checkin": "",
            "checkin_days": [],
            "last_tag_claim": ""
        }
    return user_id

def log_user_activity(user: types.User):
    if user.is_bot: return
    user_id = get_or_create_user(user)
    xp_database[user_id]["messages"] += 1
    xp_database[user_id]["xp"] += 15

# ==========================================
# 3. TELEGRAM BOT HANDLERS
# ==========================================

@dp.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def handle_start_command_private(message: types.Message):
    log_user_activity(message.from_user)
    app_url = WEB_APP_URL or "https://google.com"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐼 WELCOME TO PD CARD 🐼", web_app=WebAppInfo(url=app_url))]
    ])
    await message.reply("🐼 **WELCOME TO PD CARD** 🐼\n\nTap the button to access your trading tools and daily vouchers.", reply_markup=kb, parse_mode="Markdown")

@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text: return
    log_user_activity(message.from_user)
    raw_text = message.text.strip().upper()

    if "CHECK XP" in raw_text:
        sorted_users = sorted(xp_database.values(), key=lambda x: x["xp"], reverse=True)
        stats_output = "📊 **PD CARD LEADERBOARD** 📊\n\n"
        for index, user in enumerate(sorted_users, start=1):
            stats_output += f"🏅 #{index} | **{user['username']}** — `{user['xp']} XP`\n"
        await message.reply(stats_output, parse_mode="Markdown")

# ==========================================
# 4. WEB SERVER API ENDPOINTS
# ==========================================
async def api_leaderboard_data(request):
    sorted_players = sorted(xp_database.values(), key=lambda x: x["xp"], reverse=True)
    return web.json_response({"leaderboard": sorted_players})

async def api_user_status(request):
    user_id = request.query.get("user_id", "default_guest")
    if user_id not in xp_database:
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        xp_database[user_id] = {"username": "Guest", "messages": 0, "xp": 0, "last_active": today, "last_checkin": "", "checkin_days": [], "last_tag_claim": ""}
    return web.json_response(xp_database[user_id])

async def api_execute_checkin(request):
    data = await request.json()
    user_id = data.get("user_id")
    day_num = int(data.get("day"))
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    user_profile = xp_database.get(user_id)
    
    if not user_profile or user_profile["last_checkin"] == today_str:
        return web.json_response({"success": False, "message": "🚫 Voucher Locked: Come back tomorrow!"})

    user_profile["xp"] += 10
    user_profile["last_checkin"] = today_str
    user_profile["checkin_days"].append(day_num)
    return web.json_response({"success": True, "message": f"💳 Day {day_num} processed! +10 XP added."})

# ==========================================
# 5. WEB APP UI
# ==========================================
async def frontend_mini_app_dashboard(request):
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { background: #08070d; color: white; font-family: sans-serif; padding: 20px; }
            .feature-section-panel { background: rgba(15, 12, 28, 0.8); border-radius: 18px; padding: 20px; margin-bottom: 25px; border: 1px solid #333; }
            .voucher-grid-matrix { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
            .voucher-ticket { background: #1e1b36; padding: 14px 0; border-radius: 10px; cursor: pointer; text-align: center; }
            .voucher-ticket.redeemed { background: #f43f5e; }
        </style>
    </head>
    <body>
        <div class="feature-section-panel">
            <h2 id="user-total-xp">0 XP</h2>
            <div id="calendar-box" class="voucher-grid-matrix"></div>
        </div>
        <script>
            const tg = window.Telegram.WebApp; tg.expand();
            const userId = String(tg.initDataUnsafe.user?.id || 7777);
            
            async function syncAllData() {
                const res = await fetch(`/api/userstatus?user_id=${userId}`);
                const u = await res.json();
                document.getElementById('user-total-xp').innerText = u.xp + ' XP';
                const container = document.getElementById('calendar-box');
                container.innerHTML = '';
                for (let d = 1; d <= 30; d++) {
                    const isClaimed = u.checkin_days.includes(d);
                    const coupon = document.createElement('div');
                    coupon.className = `voucher-ticket ${isClaimed ? 'redeemed' : ''}`;
                    coupon.innerText = isClaimed ? `✓ D${d}` : `D${d}`;
                    if (!isClaimed) coupon.onclick = () => claimCoupon(d);
                    container.appendChild(coupon);
                }
            }
            async function claimCoupon(dayNum) {
                const res = await fetch('/api/checkin', {
                    method: 'POST', body: JSON.stringify({ user_id: userId, day: dayNum }),
                    headers: { 'Content-Type': 'application/json' }
                });
                const result = await res.json();
                alert(result.message);
                syncAllData();
            }
            window.onload = syncAllData;
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type="text/html")

# ==========================================
# 6. SERVER & POLLING CONFIGURATION
# ==========================================
async def start_web_server():
    app = web.Application()
    app.router.add_get("/", frontend_mini_app_dashboard)
    app.router.add_get("/api/leaderboard", api_leaderboard_data)
    app.router.add_get("/api/userstatus", api_user_status)
    app.router.add_post("/api/checkin", api_execute_checkin)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await start_web_server()
    logging.info("PD Card Trading Engine Live!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

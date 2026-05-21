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
# 1. ENVIRONMENT CONFIG & INIT
# ==========================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

if not TELEGRAM_BOT_TOKEN:
    logging.error("CRITICAL: Missing TELEGRAM_BOT_TOKEN.")
    sys.exit(1)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Active In-Memory Database
user_registry = {}
xp_database = {}  

def get_or_create_user(user: types.User):
    user_id = str(user.id)
    if user.username:
        username = f"@{user.username}"
        user_registry[f"@{user.username.lower()}"] = user.id
    else:
        username = user.first_name if user.first_name else f"Trader_{user_id[:5]}"
    
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    if user_id not in xp_database:
        xp_database[user_id] = {
            "username": username, "messages": 0, "xp": 0, "last_active": today,
            "last_checkin": "", "checkin_days": [], "last_tag_claim": "", "last_wheel_spin": ""
        }
    else:
        xp_database[user_id]["username"] = username
    return user_id

def log_user_activity(user: types.User):
    if user.is_bot: return
    user_id = get_or_create_user(user)
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    xp_database[user_id]["messages"] += 1
    xp_database[user_id]["xp"] += 15
    xp_database[user_id]["last_active"] = today

# ==========================================
# 2. TELEGRAM BOT HANDLERS
# ==========================================
@dp.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def handle_start_command_private(message: types.Message):
    log_user_activity(message.from_user)
    app_url = WEB_APP_URL if WEB_APP_URL else "https://your-server-url.com"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐼 WELCOME TO PD CARD 🐼", web_app=WebAppInfo(url=app_url))]
    ])
    await message.reply("🐼 **WELCOME TO PD CARD** 🐼\n\nAccess your live tools below!", reply_markup=kb, parse_mode="Markdown")

@dp.message(Command("whale"))
async def handle_whale_command(message: types.Message):
    log_user_activity(message.from_user)
    await message.reply("📡 Tracking live gift card allocation ledgers...", parse_mode="Markdown")

@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text: return
    log_user_activity(message.from_user)
    raw_text = message.text.strip().upper()
    
    if "CHECK XRP" in raw_text or "CHECK XP" in raw_text:
        sorted_users = sorted(xp_database.values(), key=lambda x: x["xp"], reverse=True)
        stats_output = "📊 **PD CARD OFFICIAL TRADING LEDGER** 📊\n\n"
        for index, user in enumerate(sorted_users, start=1):
            stats_output += f"🏅 #{index} | **{user['username']}** — `{user['xp']} XP`\n"
        await message.reply(stats_output, parse_mode="Markdown")

# ==========================================
# 3. WEB SERVER API ENDPOINTS
# ==========================================
async def api_leaderboard_data(request):
    sorted_players = sorted(xp_database.values(), key=lambda x: x["xp"], reverse=True)
    return web.json_response({"leaderboard": sorted_players})

async def api_user_status(request):
    user_id = request.query.get("user_id", "default_guest")
    username = request.query.get("username", "Guest")
    if user_id not in xp_database:
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        xp_database[user_id] = {"username": username, "messages": 0, "xp": 0, "last_active": today, "last_checkin": "", "checkin_days": [], "last_tag_claim": "", "last_wheel_spin": ""}
    return web.json_response(xp_database[user_id])

async def api_execute_checkin(request):
    data = await request.json()
    user_id = data.get("user_id")
    day_num = int(data.get("day"))
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    user_profile = xp_database[user_id]
    if user_profile["last_checkin"] == today_str:
        return web.json_response({"success": False, "message": "🚫 Voucher Locked: Come back tomorrow!"})
    user_profile["xp"] += 10
    user_profile["last_checkin"] = today_str
    user_profile["checkin_days"].append(day_num)
    return web.json_response({"success": True, "message": f"💳 Day {day_num} processed! +10 XP."})

async def api_execute_spin(request):
    data = await request.json()
    user_id = data.get("user_id")
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    user_profile = xp_database[user_id]
    if user_profile.get("last_wheel_spin") == today_str:
        return web.json_response({"success": False, "message": "🚫 Wheel Locked!"})
    prizes = [{"name": "+5 XP", "value": 5, "index": 0}, {"name": "+50 XP", "value": 50, "index": 1}, {"name": "+15 XP", "value": 15, "index": 2}, {"name": "+5/$", "value": 0, "index": 3}, {"name": "+25 XP", "value": 25, "index": 4}, {"name": "+10 XP", "value": 10, "index": 5}]
    winning_slice = random.choice(prizes)
    user_profile["xp"] += winning_slice["value"]
    user_profile["last_wheel_spin"] = today_str
    return web.json_response({"success": True, "slice_index": winning_slice["index"], "message": f"🎉 Won {winning_slice['name']}!"})

# ==========================================
# 4. FRONTEND UI
# ==========================================
async def frontend_mini_app_dashboard(request):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PD Card</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { font-family: sans-serif; background: #08070d; color: white; margin: 0; padding: 20px; text-align: center; }
            .giftcard-3d-frame { background: linear-gradient(135deg, #1e1b36, #0f0c1c); border: 2px solid #a855f7; border-radius: 20px; padding: 25px; margin-bottom: 25px; }
            .brand-logo-text { font-size: 26px; font-weight: 900; background: linear-gradient(90deg, #a855f7, #f43f5e); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .voucher-balance-display { font-size: 45px; font-weight: 900; margin: 15px 0; font-family: monospace; }
            .feature-section-panel { background: #151224; border-radius: 18px; padding: 20px; margin-bottom: 25px; text-align: left; }
            .section-header-title { font-weight: 800; color: #a855f7; margin-bottom: 15px; text-transform: uppercase; }
            .calc-input-box { width: 100%; padding: 12px; background: #1e1b36; border: 1px solid #a855f7; border-radius: 10px; color: white; margin-bottom: 10px; box-sizing: border-box; }
            .calc-output-payout { padding: 15px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: 900; color: #f43f5e; border: 1px solid #f43f5e; }
            .wheel-spinner-canvas { width: 200px; height: 200px; border-radius: 50%; border: 6px solid #a855f7; background: conic-gradient(#1e1b36 0deg 60deg, #f43f5e 60deg 120deg, #2e2a54 120deg 180deg, #a855f7 180deg 240deg, #121024 240deg 300deg, #ec4899 300deg 360deg); margin: 15px auto; transition: transform 4s ease-out; }
            .spin-trigger-btn { width: 100%; background: #a855f7; border: none; padding: 15px; border-radius: 12px; color: white; font-weight: 900; cursor: pointer; }
            .voucher-grid-matrix { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
            .voucher-ticket { background: #1e1b36; padding: 10px; border-radius: 8px; font-size: 10px; cursor: pointer; border: 1px solid #333; }
            .voucher-ticket.redeemed { background: #f43f5e; }
            .leader-desk-row { display: flex; justify-content: space-between; padding: 10px; background: #1e1b36; margin-bottom: 5px; border-radius: 8px; }
        </style>
    </head>
    <body>
        <div class="giftcard-3d-frame">
            <div class="brand-logo-text">PD CARD</div>
            <div class="voucher-balance-display" id="user-total-xp">00 XP</div>
            <div id="user-display">TRADER</div>
        </div>
        <div class="feature-section-panel">
            <div class="section-header-title">📈 Live Rate Index</div>
            <select class="calc-input-box" id="card-type" onchange="runCalculation()">
                <option value="920">Apple - ₦920/$</option>
                <option value="950">Razer - ₦950/$</option>
            </select>
            <input type="number" class="calc-input-box" id="card-amount" value="100" oninput="runCalculation()">
            <div class="calc-output-payout" id="payout-payout">ESTIMATED PAYOUT: ₦92,000</div>
        </div>
        <div class="feature-section-panel">
            <div class="section-header-title">🎡 Lucky Panda Wheel</div>
            <div class="wheel-spinner-canvas" id="spin-wheel"></div>
            <button class="spin-trigger-btn" onclick="executeLuckySpin()">SPIN</button>
        </div>
        <div class="feature-section-panel">
            <div class="section-header-title">🎫 30-Day Grid</div>
            <div class="voucher-grid-matrix" id="calendar-box"></div>
        </div>
        <div class="feature-section-panel">
            <div class="section-header-title">🏆 Leaderboard</div>
            <div id="leaderboard-box"></div>
        </div>
        <script>
            const tg = window.Telegram.WebApp; tg.expand();
            const rawUser = tg.initDataUnsafe.user || { id: 7777, first_name: "Trader" };
            const userId = String(rawUser.id);
            let userHandle = rawUser.username ? `@${rawUser.username}` : (rawUser.first_name || "Trader");
            document.getElementById('user-display').innerText = userHandle;

            function runCalculation() {
                const rate = parseFloat(document.getElementById('card-type').value);
                const amt = parseFloat(document.getElementById('card-amount').value) || 0;
                document.getElementById('payout-payout').innerText = `ESTIMATED PAYOUT: ₦${(rate*amt).toLocaleString()}`;
            }

            async function executeLuckySpin() {
                const res = await fetch('/api/spinwheel', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ user_id: userId }) });
                const result = await res.json();
                if(result.success) {
                    const wheel = document.getElementById('spin-wheel');
                    wheel.style.transform = `rotate(${(result.slice_index * 60) + 1440}deg)`;
                    setTimeout(syncAllData, 4100);
                } else alert(result.message);
            }

            async function syncAllData() {
                const [statusRes, lbRes] = await Promise.all([
                    fetch(`/api/userstatus?user_id=${userId}&username=${encodeURIComponent(userHandle)}`),
                    fetch('/api/leaderboard')
                ]);
                const user = await statusRes.json();
                const lb = await lbRes.json();
                document.getElementById('user-total-xp').innerText = `${user.xp} XP`;
                const cal = document.getElementById('calendar-box'); cal.innerHTML = '';
                for(let i=1; i<=30; i++) {
                    const isClaimed = user.checkin_days.includes(i);
                    cal.innerHTML += `<div class="voucher-ticket ${isClaimed ? 'redeemed' : ''}" onclick="claimCoupon(${i})">D${i}</div>`;
                }
                const lbBox = document.getElementById('leaderboard-box'); lbBox.innerHTML = '';
                lb.leaderboard.forEach((u, i) => lbBox.innerHTML += `<div class="leader-desk-row"><span>#${i+1} ${u.username}</span><span>${u.xp} XP</span></div>`);
            }

            async function claimCoupon(day) {
                const res = await fetch('/api/checkin', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ user_id: userId, day: day }) });
                const r = await res.json(); alert(r.message); syncAllData();
            }

            window.onload = () => { syncAllData(); runCalculation(); };
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type="text/html")

# ==========================================
# 5. SERVER RUNNER
# ==========================================
async def start_web_server():
    app = web.Application()
    app.router.add_get("/", frontend_mini_app_dashboard)
    app.router.add_get("/api/leaderboard", api_leaderboard_data)
    app.router.add_get("/api/userstatus", api_user_status)
    app.router.add_post("/api/checkin", api_execute_checkin)
    app.router.add_post("/api/spinwheel", api_execute_spin)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await start_web_server()
    logging.info("PD Card Trading Engine V2 Live!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

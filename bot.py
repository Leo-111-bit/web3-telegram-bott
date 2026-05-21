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
        <title>PD Card Pro</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            :root {
                --bg: #0f172a;
                --card-bg: rgba(30, 41, 59, 0.7);
                --accent: #8b5cf6;
                --accent-hover: #7c3aed;
                --text: #f8fafc;
                --text-muted: #94a3b8;
                --glass: rgba(255, 255, 255, 0.05);
            }
            body {
                font-family: 'Inter', -apple-system, sans-serif;
                background: var(--bg);
                color: var(--text);
                margin: 0;
                padding: 20px;
                background-image: radial-gradient(circle at top right, #1e1b4b, transparent), radial-gradient(circle at bottom left, #4c0519, transparent);
                min-height: 100vh;
            }
            .glass-card {
                background: var(--card-bg);
                backdrop-filter: blur(12px);
                border: 1px solid var(--glass);
                border-radius: 24px;
                padding: 24px;
                margin-bottom: 20px;
                box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);
            }
            .brand-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .balance-text { font-size: 32px; font-weight: 800; color: #fff; margin: 10px 0; letter-spacing: -1px; }
            
            /* Calculator Styles */
            select, input { width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass); padding: 14px; border-radius: 12px; color: white; margin: 10px 0; font-size: 16px; }
            
            /* Horizontal Panda Slider */
            .slider-container {
                display: flex;
                overflow-x: auto;
                gap: 15px;
                padding: 10px 0;
                scroll-behavior: smooth;
                scrollbar-width: none;
            }
            .slider-container::-webkit-scrollbar { display: none; }
            .panda-slide {
                min-width: 120px;
                height: 120px;
                background: var(--glass);
                border-radius: 20px;
                border: 2px solid var(--accent);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 40px;
                flex-shrink: 0;
                transition: transform 0.3s;
            }
            .panda-slide:hover { transform: scale(1.05); }

            /* Grid & List */
            .grid-container { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
            .day-item { background: var(--glass); padding: 10px 0; border-radius: 8px; font-size: 11px; text-align: center; border: 1px solid rgba(255,255,255,0.05); cursor: pointer; }
            .day-item.redeemed { background: var(--accent); color: white; }
            
            .leaderboard-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; background: var(--glass); border-radius: 12px; margin-bottom: 8px; }
        </style>
    </head>
    <body>

        <div class="glass-card">
            <div class="brand-header">
                <span style="font-weight: 800; color: var(--accent);">PD CARD PRO</span>
                <span id="user-display" style="color: var(--text-muted); font-size: 12px;">@trader</span>
            </div>
            <div class="balance-text" id="user-total-xp">0.00 XP</div>
            <div style="font-size: 12px; color: var(--text-muted);">Current Wallet Balance</div>
        </div>

        <div class="glass-card">
            <h3 style="margin-top:0; font-size: 14px; color: var(--text-muted);">30-DAY PANDA GALLERY</h3>
            <div class="slider-container" id="panda-slider">
                </div>
        </div>

        <div class="glass-card">
            <h3 style="margin-top:0; font-size: 14px; color: var(--text-muted);">RATE CALCULATOR</h3>
            <select id="card-type" onchange="runCalculation()">
                <option value="920">Apple iTunes - ₦920/$</option>
                <option value="950">Razer Gold - ₦950/$</option>
            </select>
            <input type="number" id="card-amount" value="100" oninput="runCalculation()">
            <div id="payout-payout" style="font-size: 24px; font-weight: 800; color: #22c55e; margin-top: 10px;">₦92,000</div>
        </div>

        <div class="glass-card">
            <h3 style="font-size: 14px; color: var(--text-muted);">CHECK-IN ALLOCATION</h3>
            <div class="grid-container" id="calendar-box"></div>
        </div>

        <div class="glass-card">
            <h3 style="font-size: 14px; color: var(--text-muted);">GLOBAL RANKINGS</h3>
            <div id="leaderboard-box"></div>
        </div>

        <script>
            const tg = window.Telegram.WebApp; tg.expand();
            const rawUser = tg.initDataUnsafe.user || { id: 7777, first_name: "Trader" };
            const userId = String(rawUser.id);
            let userHandle = rawUser.username ? `@${rawUser.username}` : (rawUser.first_name || "Trader");
            document.getElementById('user-display').innerText = userHandle;

            // Generate Slideshow
            const slider = document.getElementById('panda-slider');
            for(let i=1; i<=30; i++) {
                slider.innerHTML += `<div class="panda-slide">🐼</div>`;
            }

            function runCalculation() {
                const rate = parseFloat(document.getElementById('card-type').value);
                const amt = parseFloat(document.getElementById('card-amount').value) || 0;
                document.getElementById('payout-payout').innerText = `₦${(rate*amt).toLocaleString()}`;
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
                    cal.innerHTML += `<div class="day-item ${isClaimed ? 'redeemed' : ''}" onclick="claimCoupon(${i})">D${i}</div>`;
                }
                const lbBox = document.getElementById('leaderboard-box'); lbBox.innerHTML = '';
                lb.leaderboard.forEach((u, i) => lbBox.innerHTML += `<div class="leaderboard-item"><span>#${i+1} ${u.username}</span><span style="font-weight:700;">${u.xp} XP</span></div>`);
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

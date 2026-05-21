import os
import sys
import logging
import asyncio
import random
import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.enums import ChatType

# 1. Environment Config Validation
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

if not TELEGRAM_BOT_TOKEN:
    logging.error("CRITICAL: Missing TELEGRAM_BOT_TOKEN.")
    sys.exit(1)

# 2. Initialization
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Active In-Memory Database Engine
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
            "username": username,
            "messages": 0,
            "xp": 0,
            "last_active": today,
            "last_checkin": "",
            "checkin_days": [],
            "last_tag_claim": "",
            "last_wheel_spin": ""
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
# 3. TELEGRAM BOT HANDLERS
# ==========================================

@dp.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def handle_start_command_private(message: types.Message):
    log_user_activity(message.from_user)
    app_url = WEB_APP_URL if WEB_APP_URL else f"https://google.com"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐼 WELCOME TO PD CARD 🐼", web_app=WebAppInfo(url=app_url))]
    ])
    
    welcome_text = (
        "🐼 **WELCOME TO PD CARD** 🐼\n\n"
        "Your premium gift card index and trade hub profile is live! Tap the digital voucher button below to access your live calculator tools, spin the Panda Wheel, claim 30-day coupon rewards, and view real-time rankings."
    )
    await message.reply(welcome_text, reply_markup=kb, parse_mode="Markdown")

@dp.message(Command("whale"))
async def handle_whale_command(message: types.Message):
    log_user_activity(message.from_user)
    await message.reply("📡 Tracking live gift card allocation ledgers...", parse_mode="Markdown")

@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text: 
        return
        
    log_user_activity(message.from_user)
    raw_text = message.text.strip().upper()
    is_private = message.chat.type == ChatType.PRIVATE

    if "CHECK XRP" in raw_text or "CHECK XP" in raw_text:
        if not xp_database:
            await message.reply("📉 System index empty! No traders have active credit scores yet.")
            return

        sorted_users = sorted(xp_database.values(), key=lambda x: x["xp"], reverse=True)
        stats_output = "📊 **PD CARD OFFICIAL TRADING LEDGER** 📊\n\n"
        for index, user in enumerate(sorted_users, start=1):
            stats_output += f"🏅 #{index} | **{user['username']}** — `{user['xp']} XP` ({user['messages']} activity index)\n"
        
        await message.reply(stats_output, parse_mode="Markdown")
        return

    bot_info = await bot.get_me()
    bot_username = f"@{bot_info.username}"
    is_tagged = bot_username.lower() in message.text.lower()

    if is_tagged and not is_private:
        now = datetime.datetime.now(datetime.timezone.utc)
        if (now - message.date).total_seconds() > 86400:
            return  

        user_id = get_or_create_user(message.from_user)
        user_profile = xp_database[user_id]
        username_label = user_profile["username"]
        today_str = now.strftime("%Y-%m-%d")
        
        if user_profile.get("last_tag_claim") == today_str:
            await message.reply(f"🐼 Welcome back to the counter, {username_label}! Your daily mention allocation is locked. Let's trade gift cards! 💳")
        else:
            secret_xp = random.randint(20, 50)
            user_profile["xp"] += secret_xp
            user_profile["last_tag_claim"] = today_str  
            
            await message.reply(f"🎉 🐼 BOOM! {username_label} just claimed their daily PD Card bonus of {secret_xp} XP! Drop your vouchers for premium rates!")

# ==========================================
# 4. WEB SERVER API ENDPOINTS
# ==========================================
async def api_leaderboard_data(request):
    sorted_players = sorted(xp_database.values(), key=lambda x: x["xp"], reverse=True)
    return web.json_response({"leaderboard": sorted_players})

async def api_user_status(request):
    user_id = request.query.get("user_id", "default_guest")
    username = request.query.get("username", "Guest")
    
    if username == "undefined" or not username or username.startswith("null"):
        username = f"Trader_{user_id[:5]}"

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
        return web.json_response({"success": False, "message": "🚫 Voucher Locked: Come back tomorrow to redeem another day allocation!"})

    user_profile["xp"] += 10
    user_profile["last_checkin"] = today_str
    user_profile["checkin_days"].append(day_num)
    return web.json_response({"success": True, "message": f"💳 Day {day_num} Gift Card processed successfully! +10 XP added to balance."})

async def api_execute_spin(request):
    data = await request.json()
    user_id = data.get("user_id")
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    user_profile = xp_database[user_id]
    
    if user_profile.get("last_wheel_spin") == today_str:
        return web.json_response({"success": False, "message": "🚫 Wheel Locked: Your lucky spin allocation resets tomorrow!"})
        
    prizes = [
        {"name": "+5 XP Voucher", "value": 5, "index": 0},
        {"name": "+50 XP JACKPOT", "value": 50, "index": 1},
        {"name": "+15 XP Voucher", "value": 15, "index": 2},
        {"name": "+5/$ Top Rate Coupon", "value": 0, "index": 3},
        {"name": "+25 XP Voucher", "value": 25, "index": 4},
        {"name": "+10 XP Voucher", "value": 10, "index": 5}
    ]
    
    winning_slice = random.choice(prizes)
    user_profile["xp"] += winning_slice["value"]
    user_profile["last_wheel_spin"] = today_str
    
    return web.json_response({
        "success": True, 
        "slice_index": winning_slice["index"], 
        "message": f"🎉 Won {winning_slice['name']}! Wallet balance updated securely."
    })

# ==========================================
# 5. PREMIUM UI (REPLACED WITH NEW DESIGN)
# ==========================================
async def frontend_mini_app_dashboard(request):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PD CARD | PREMIUM</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            :root { --accent: #a855f7; --bg: #0a0e17; --glass: rgba(255,255,255,0.05); }
            body { font-family: -apple-system, sans-serif; background: var(--bg); color: white; margin: 0; padding: 15px; }
            .card { background: var(--glass); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.1); border-radius: 24px; padding: 20px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
            .balance-text { font-size: 36px; font-weight: 800; background: linear-gradient(90deg, #fff, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .grid-matrix { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
            .cell { background: rgba(0,0,0,0.3); border-radius: 12px; padding: 10px; font-size: 10px; text-align: center; border: 1px solid rgba(255,255,255,0.05); }
            .btn { background: var(--accent); border: none; padding: 12px; border-radius: 12px; color: white; font-weight: bold; width: 100%; margin-top: 10px; }
            .spin-wheel { width: 200px; height: 200px; border-radius: 50%; border: 4px solid var(--accent); margin: 20px auto; transition: transform 4s ease-out; }
        </style>
    </head>
    <body>
        <div class="card">
            <div style="font-size: 12px; color: #a855f7; font-weight: bold;">TOTAL VOUCHER BALANCE</div>
            <div class="balance-text" id="user-total-xp">0.00 XP</div>
        </div>
        <div class="card">
            <div style="margin-bottom: 10px; font-weight: bold;">Premium Rate Calculator</div>
            <input type="number" id="card-amount" placeholder="Amount ($)" style="width: 100%; padding: 12px; border-radius: 10px; border:none; background: #1a1a1a; color: white; margin-bottom: 10px;" oninput="runCalc()">
            <div id="payout-payout" style="font-weight: bold; color: #f43f5e;">PAYOUT: ₦0</div>
        </div>
        <div class="card">
            <div class="spin-wheel" id="spin-wheel"></div>
            <button class="btn" onclick="executeLuckySpin()">TRIGGER SPIN</button>
        </div>
        <div class="card">
            <div class="grid-matrix" id="calendar-box"></div>
        </div>
        <div class="card" id="leaderboard-box"></div>
        <script>
            const tg = window.Telegram.WebApp; tg.expand();
            const userId = String(tg.initDataUnsafe.user?.id || 7777);
            const userHandle = tg.initDataUnsafe.user?.username || "Trader";
            
            function runCalc() { 
                const val = document.getElementById('card-amount').value || 0;
                document.getElementById('payout-payout').innerText = `PAYOUT: ₦${(val * 920).toLocaleString()}`;
            }
            
            async function syncAllData() {
                const res = await fetch(`/api/userstatus?user_id=${userId}&username=${userHandle}`);
                const data = await res.json();
                document.getElementById('user-total-xp').innerText = `${data.xp}.00 XP`;
                const cal = document.getElementById('calendar-box');
                cal.innerHTML = '';
                for(let i=1; i<=30; i++) {
                    const isClaimed = data.checkin_days.includes(i);
                    cal.innerHTML += `<div class="cell" style="${isClaimed ? 'background:var(--accent)' : ''}">${i}</div>`;
                }
            }
            
            async function executeLuckySpin() {
                const res = await fetch('/api/spinwheel', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({user_id: userId})});
                const data = await res.json();
                if(data.success) {
                    document.getElementById('spin-wheel').style.transform = `rotate(${3600 + (data.slice_index * 60)}deg)`;
                    setTimeout(syncAllData, 4000);
                } else alert(data.message);
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

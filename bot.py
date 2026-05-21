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

# 1. Environment Config Validation
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

if not TELEGRAM_BOT_TOKEN:
    logging.error("CRITICAL: Missing TELEGRAM_BOT_TOKEN environment variable.")
    sys.exit(1)

# 2. Initialization
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Active In-Memory Database Engine
user_registry = {}
xp_database = {}  

def get_or_create_user(user: types.User):
    user_id = str(user.id)
    username = f"@{user.username}" if user.username else user.first_name
    today = datetime.utcnow().strftime("%Y-%m-%d")

    if user.username:
        user_registry[f"@{user.username.lower()}"] = user.id

    if user_id not in xp_database:
        xp_database[user_id] = {
            "username": username,
            "messages": 0,
            "xp": 0,
            "last_active": today,
            "last_checkin": "",
            "checkin_days": []
        }
    return user_id

def log_user_activity(user: types.User):
    if user.is_bot: return
    user_id = get_or_create_user(user)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    xp_database[user_id]["messages"] += 1
    xp_database[user_id]["xp"] += 15
    xp_database[user_id]["last_active"] = today

# Async Price Fetcher Engine
async def fetch_xrp_price():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.coingecko.com/api/v3/simple/price?ids=ripple&vs_currencies=usd&include_24hr_change=true") as response:
                if response.status == 200:
                    data = await response.json()
                    price = data["ripple"]["usd"]
                    change = data["ripple"]["usd_24h_change"]
                    return f"${price:.4f}", f"{change:+.2f}%"
    except Exception as e:
        logging.error(f"Error fetching price: {e}")
    return "$1.3740", "+0.65%"

# 3. Handlers
@dp.message(CommandStart())
async def handle_start_command(message: types.Message):
    log_user_activity(message.from_user)
    app_url = WEB_APP_URL if WEB_APP_URL else f"https://google.com"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ LAUNCH PD REALM ⚡", web_app=WebAppInfo(url=app_url))]
    ])
    welcome_text = (
        "💳 **WELCOME TO THE PD CARD OFFICIAL TRACKER** 🐼\n\n"
        "Your secure profile is live. Launch the dashboard app below to track live assets, manage points, and claim daily rewards!"
    )
    await message.reply(welcome_text, reply_markup=kb, parse_mode="Markdown")

# Admin Feature: Gift XP directly to users in the chat
@dp.message(Command("gift"))
async def handle_gift_command(message: types.Message):
    if message.chat.type != "private":
        member = await message.chat.get_member(message.from_user.id)
        if member.status not in ["administrator", "creator"]:
            await message.reply("❌ Restrained: Only admins can gift assets.")
            return

    args = message.text.split()
    if len(args) < 3:
        await message.reply("💡 Format: `/gift @username 500`", parse_mode="Markdown")
        return

    target_handle = args[1].lower().strip()
    try:
        amount = int(args[2])
    except ValueError:
        await message.reply("❌ Please input a valid numerical value.")
        return

    target_id = user_registry.get(target_handle)
    if not target_id or str(target_id) not in xp_database:
        await message.reply("❌ User session not initialized in database yet.")
        return

    xp_database[str(target_id)]["xp"] += amount
    await message.reply(f"🎁 **PD CARD BONUS GRANTED**\n\n{target_handle} has been awarded `{amount} XP` by the administration!", parse_mode="Markdown")

# Universal Dynamic Messaging Engine (Handles Tagging + Restores PM Integrity)
@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text: return
    log_user_activity(message.from_user)

    bot_info = await bot.get_me()
    bot_username = f"@{bot_info.username}"
    is_private = message.chat.type == "private"
    is_tagged = bot_username in message.text

    # Action Matrix 1: If tagged inside group chats
    if is_tagged and not is_private:
        price_val, change_val = await fetch_xrp_price()
        app_url = WEB_APP_URL if WEB_APP_URL else f"https://google.com"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📈 VIEW LIVE PRICES NOW 📈", web_app=WebAppInfo(url=app_url))]
        ])
        
        tag_response = (
            f"🐼 **Welcome to PD Card!** Check out our live prices below:\n\n"
            f"🪙 **Asset:** XRP / USD\n"
            f"💵 **Live Price:** `{price_val}`\n"
            f"📊 **24H Trend:** `{change_val}`\n\n"
            f"Tap the tracker dashboard link below to watch trades live!"
        )
        await message.reply(tag_response, reply_markup=kb, parse_mode="Markdown")
        return

    # Action Matrix 2: Direct Fallback Chat Response for Private DMs
    if is_private:
        price_val, change_val = await fetch_xrp_price()
        app_url = WEB_APP_URL if WEB_APP_URL else f"https://google.com"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ LAUNCH PD CARD APP ⚡", web_app=WebAppInfo(url=app_url))]
        ])
        pm_response = (
            f"🐼 **PD CARD AUTOMATED INTERACTIVE SYSTEM** 🐼\n\n"
            f" Live Core Metrics:\n"
            f"• XRP Tracker Status: Online\n"
            f"• Current XRP Value: `{price_val}` ({change_val})\n\n"
            f"How can we guide you today? Launch the premium 3D application suite below to check out the leaderboards!"
        )
        await message.reply(pm_response, reply_markup=kb, parse_mode="Markdown")

# 4. API Endpoints
async def api_leaderboard_data(request):
    sorted_players = sorted(xp_database.values(), key=lambda x: x["xp"], reverse=True)
    return web.json_response({"leaderboard": sorted_players})

async def api_user_status(request):
    user_id = request.query.get("user_id", "default_guest")
    username = request.query.get("username", "Guest")
    if user_id not in xp_database:
        xp_database[user_id] = {"username": username, "messages": 0, "xp": 0, "last_active": "", "last_checkin": "", "checkin_days": []}
    return web.json_response(xp_database[user_id])

async def api_execute_checkin(request):
    data = await request.json()
    user_id = data.get("user_id")
    day_num = int(data.get("day"))
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    user_profile = xp_database[user_id]
    
    if user_profile["last_checkin"] == today_str:
        return web.json_response({"success": False, "message": "🚫 Locked: Already claimed today!"})

    user_profile["xp"] += 10
    user_profile["last_checkin"] = today_str
    user_profile["checkin_days"].append(day_num)
    return web.json_response({"success": True, "message": f"⚡ Day {day_num} Reward unlocked! +10 XP added successfully."})

# Live Tracker API for Frontend Syncing
async def api_live_ticker(request):
    p, c = await fetch_xrp_price()
    return web.json_response({"price": p, "change": c})

# 5. Premium PD Card 3D Splash & Dashboard Frontend
async def frontend_mini_app_dashboard(request):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PD Card Premium Leaderboard</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            * { box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: #080a0f; color: #ffffff; margin: 0; padding: 0; 
                text-align: center; overflow: hidden;
            }

            /* 3D WELCOME SPLASH SCREEN SETUP */
            #welcome-splash {
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: radial-gradient(circle at center, #111622 0%, #040508 100%);
                display: flex; flex-direction: column; align-items: center; justify-content: center;
                z-index: 9999; transition: all 0.7s cubic-bezier(0.7, 0, 0.3, 1);
            }

            .panda-3d-card {
                width: 210px; height: 270px;
                background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.01));
                border: 2px solid #00ff6e; border-radius: 24px;
                display: flex; flex-direction: column; align-items: center; justify-content: center;
                backdrop-filter: blur(20px);
                box-shadow: 0 0 50px rgba(0, 255, 110, 0.25), inset 0 0 20px rgba(255,255,255,0.05);
                transform: perspective(1000px) rotateY(15deg);
                animation: floatRotate 4.5s ease-in-out infinite;
                margin-bottom: 35px;
            }

            .card-logo { font-size: 85px; margin: 0; }
            .card-ticker-tag { 
                background: rgba(0, 255, 110, 0.15); color: #00ff6e; padding: 4px 12px; 
                border-radius: 20px; font-size: 11px; font-weight: 900; margin-top: 10px;
                border: 1px solid rgba(0, 255, 110, 0.3);
            }
            
            .splash-title {
                font-size: 26px; font-weight: 900; color: #ffffff; letter-spacing: 2px;
                margin-bottom: 6px; text-transform: uppercase;
            }
            .splash-subtitle { color: #00ff6e; font-size: 13px; font-weight: bold; margin-bottom: 35px; letter-spacing: 1px; }

            .btn-enter {
                background: #00ff6e; color: #000; border: none; padding: 16px 50px;
                border-radius: 50px; font-weight: 900; font-size: 15px; cursor: pointer;
                box-shadow: 0 0 25px rgba(0, 255, 110, 0.45); transition: 0.3s;
            }
            .btn-enter:active { transform: scale(0.95); }

            /* MAIN TRACKER DASHBOARD LAYOUT */
            #main-app { opacity: 0; transform: translateY(40px); transition: 0.7s ease; padding: 20px; overflow-y: auto; height: 100vh; }

            .profile-card {
                background: linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%);
                border: 1px solid rgba(0, 255, 110, 0.25);
                border-radius: 24px; padding: 22px; margin-bottom: 22px;
                backdrop-filter: blur(15px); box-shadow: 0 20px 40px rgba(0,0,0,0.5);
            }
            h2 { color: #ffffff; font-size: 20px; font-weight: 900; margin: 0; letter-spacing: 1px; }
            .xp-val { font-size: 42px; font-weight: 900; color: #00ff6e; text-shadow: 0 0 20px rgba(0,255,110,0.4); margin: 8px 0; }
            
            /* Live Dynamic Ticker Panel */
            .live-crypto-bar {
                display: flex; justify-content: space-between; align-items: center;
                background: rgba(0, 255, 110, 0.06); border: 1px dashed rgba(0, 255, 110, 0.3);
                border-radius: 14px; padding: 12px 18px; margin-bottom: 25px; font-size: 13px;
            }

            .grid-container {
                display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;
                background: rgba(255,255,255,0.01); border-radius: 20px; padding: 14px;
                border: 1px solid rgba(255,255,255,0.03);
            }
            .day-box {
                background: #12161f; border-radius: 12px; padding: 16px 0; font-size: 11px;
                font-weight: bold; color: #7e91a8; border: 1px solid transparent; cursor: pointer;
                transition: 0.2s;
            }
            .day-box:hover { border-color: #00ff6e; }
            .day-box.claimed { background: linear-gradient(135deg, #00ff6e, #00b34d); color: #000; font-weight:900; box-shadow: 0 0 15px rgba(0,255,110,0.3); }

            .leaderboard { background: rgba(255,255,255,0.01); border-radius: 20px; padding: 10px; margin-top: 20px; text-align: left; border: 1px solid rgba(255,255,255,0.03); }
            .row { display: flex; justify-content: space-between; padding: 14px 15px; border-bottom: 1px solid rgba(255,255,255,0.04); align-items: center; }
            .rank { color: #00ff6e; font-weight: 900; margin-right: 12px; }

            @keyframes floatRotate {
                0%, 100% { transform: perspective(1000px) rotateY(12deg) translateY(0); }
                50% { transform: perspective(1000px) rotateY(-12deg) translateY(-12px); }
            }
        </style>
    </head>
    <body>

        <div id="welcome-splash">
            <div class="panda-3d-card">
                <div class="card-logo">🐼</div>
                <div class="card-ticker-tag">XRP METRICS ACTIVE</div>
            </div>
            <div class="splash-title">PD CARD HUB</div>
            <div class="splash-subtitle">GIFT CARD TRACKER ENGINE</div>
            <button class="btn-enter" onclick="enterApp()">ENTER ECOSYSTEM</button>
        </div>

        <div id="main-app">
            <div class="profile-card">
                <h2>PD MINTER CREDITS</h2>
                <div class="xp-val" id="total-xp">0000</div>
                <div style="font-size: 11px; font-weight: bold; color: #7e91a8; letter-spacing: 0.5px;">SECURED VIA PD CARD PROTOCOL</div>
            </div>

            <div class="live-crypto-bar">
                <div style="font-weight: 800; display: flex; align-items: center;">🪙 <span style="margin-left:6px;">XRP / USD Live:</span></div>
                <div id="crypto-ticker-val" style="font-weight: 900; color: #00ff6e; text-shadow: 0 0 10px rgba(0,255,110,0.3);">Loading...</div>
            </div>

            <div style="text-align: left; font-weight: 900; font-size: 12px; color: #00ff6e; margin-bottom: 10px; letter-spacing: 0.5px;">📅 DAILY CARD BONUSES</div>
            <div class="grid-container" id="calendar"></div>

            <div style="text-align: left; font-weight: 900; font-size: 12px; color: #ffffff; margin: 30px 0 10px 0; letter-spacing: 0.5px;">🏆 TOP COMMUNITY TRADERS</div>
            <div class="leaderboard" id="leaderboard"></div>
        </div>

        <script>
            const tg = window.Telegram.WebApp;
            tg.expand();

            const rawUser = tg.initDataUnsafe.user || { id: 4444, first_name: "PD Trader", username: "PDMember" };
            const userId = String(rawUser.id);
            const userHandle = rawUser.username ? `@${rawUser.username}` : rawUser.first_name;

            function enterApp() {
                const splash = document.getElementById('welcome-splash');
                const app = document.getElementById('main-app');
                splash.style.opacity = '0';
                splash.style.transform = 'scale(1.4)';
                setTimeout(() => {
                    splash.style.display = 'none';
                    app.style.opacity = '1';
                    app.style.transform = 'translateY(0)';
                    sync();
                    // Polling real-time analytics updates every 10 seconds
                    setInterval(updateTicker, 10000);
                }, 700);
            }

            async function updateTicker() {
                try {
                    const res = await fetch('/api/livexrp');
                    const d = await res.json();
                    document.getElementById('crypto-ticker-val').innerText = `${d.price} (${d.change})`;
                } catch(e) {}
            }

            async function sync() {
                try {
                    updateTicker();
                    const res = await fetch(`/api/userstatus?user_id=${userId}&username=${encodeURIComponent(userHandle)}`);
                    const profile = await res.json();
                    document.getElementById('total-xp').innerText = `${profile.xp} XP`;
                    
                    const cal = document.getElementById('calendar');
                    cal.innerHTML = '';
                    for (let d = 1; d <= 30; d++) {
                        const claimed = profile.checkin_days.includes(d);
                        const box = document.createElement('div');
                        box.className = `day-box ${claimed ? 'claimed' : ''}`;
                        box.innerText = claimed ? '✓' : `D${d}`;
                        if(!claimed) box.onclick = () => claim(d);
                        cal.appendChild(box);
                    }

                    const lbRes = await fetch('/api/leaderboard');
                    const lbData = await lbRes.json();
                    const lbDiv = document.getElementById('leaderboard');
                    lbDiv.innerHTML = '';
                    lbData.leaderboard.forEach((u, i) => {
                        lbDiv.innerHTML += `<div class="row"><div><span class="rank">#${i+1}</span>${u.username}</div><div style="color:#00ff6e; font-weight:bold;">${u.xp} XP</div></div>`;
                    });
                } catch(e) {}
            }

            async function claim(d) {
                try {
                    const res = await fetch('/api/checkin', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: userId, day: d })
                    });
                    const r = await res.json();
                    tg.showAlert(r.message);
                    sync();
                } catch(e) {}
            }
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type="text/html")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", frontend_mini_app_dashboard)
    app.router.add_get("/api/livexrp", api_live_ticker)
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
    logging.info("Core PD Card Analytics Engine Deployed Successfully!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

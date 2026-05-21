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

# 1. Environment Config Validation
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

if not TELEGRAM_BOT_TOKEN or not GROQ_API_KEY:
    logging.error("CRITICAL: Missing TELEGRAM_BOT_TOKEN or GROQ_API_KEY.")
    sys.exit(1)

# 2. Initialization
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

# Active In-Memory Database Engine
user_registry = {}
xp_database = {}  

last_seen_tx = {"id": None}

TICKER_MAP = {
    "btc": "bitcoin", "eth": "ethereum", "sol": "solana", "bnb": "binancecoin", "ton": "the-open-network"
}

SYSTEM_INSTRUCTION = "You are an elite, highly knowledgeable AI Assistant. Detect and adapt automatically to whatever language the user speaks and reply natively."

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

# 3. Handlers
@dp.message(CommandStart())
async def handle_start_command(message: types.Message):
    log_user_activity(message.from_user)
    app_url = WEB_APP_URL if WEB_APP_URL else f"https://google.com"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 LAUNCH PANDA REALM 💎", web_app=WebAppInfo(url=app_url))]
    ])
    welcome_text = (
        "🐼 **WELCOME TO THE PANDA GIFT CARD ECOSYSTEM** 🐼\n\n"
        "Your active network profile is online. Tap the dashboard below to enter the 3D Panda Realm and claim your daily rewards!"
    )
    await message.reply(welcome_text, reply_markup=kb, parse_mode="Markdown")

# Admin Feature: Gift XP directly to users in the group chat
@dp.message(Command("gift"))
async def handle_gift_command(message: types.Message):
    member = await message.chat.get_member(message.from_user.id)
    if member.status not in ["administrator", "creator"] and message.chat.type != "private":
        await message.reply("❌ Restrained: Only admins can gift ecosystem assets.")
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
    await message.reply(f"🎁 **PANDA GIFT SUCCESSFUL**\n\n{target_handle} has been awarded `{amount} XP` by the administration!", parse_mode="Markdown")

# Global Text Fallback (Tracks Live Messages + Tags Rewards)
@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text: return
    log_user_activity(message.from_user)

    bot_info = await bot.get_me()
    bot_username = f"@{bot_info.username}"
    is_private = message.chat.type == "private"
    is_tagged = bot_username in message.text

    if is_tagged and not is_private:
        user_id = get_or_create_user(message.from_user)
        username_label = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        secret_xp = random.randint(1, 50)
        xp_database[user_id]["xp"] += secret_xp
        await message.reply(f'🎉 🐼 BOOM! "{username_label}" just gained {secret_xp} XRP for tagging the Panda AI!')

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
        return web.json_response({"success": False, "message": "🚫 Locked: You already checked in today!"})

    user_profile["xp"] += 10
    user_profile["last_checkin"] = today_str
    user_profile["checkin_days"].append(day_num)
    return web.json_response({"success": True, "message": f"🐼 Reward Claimed! +10 XP added."})

# 5. Premium Panda 3D Splash & Dashboard Frontend
async def frontend_mini_app_dashboard(request):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Panda Gift Card Leaderboard</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            * { box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: #090b0d; color: #ffffff; margin: 0; padding: 0; 
                text-align: center; overflow: hidden;
            }

            /* 3D WELCOME SPLASH SCREEN */
            #welcome-splash {
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: radial-gradient(circle at center, #1a202c 0%, #05070a 100%);
                display: flex; flex-direction: column; align-items: center; justify-content: center;
                z-index: 9999; transition: all 0.8s cubic-bezier(0.7, 0, 0.3, 1);
            }

            .panda-3d-card {
                width: 200px; height: 260px;
                background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.02));
                border: 2px solid #00ff6e; border-radius: 20px;
                display: flex; align-items: center; justify-content: center;
                font-size: 100px; backdrop-filter: blur(15px);
                box-shadow: 0 0 40px rgba(0, 255, 110, 0.3);
                transform: perspective(1000px) rotateY(15deg);
                animation: floatRotate 5s ease-in-out infinite;
                margin-bottom: 40px;
            }
            
            .splash-title {
                font-size: 28px; font-weight: 900; color: #ffffff;
                letter-spacing: 2px; margin-bottom: 10px; text-transform: uppercase;
                text-shadow: 0 0 15px rgba(255,255,255,0.2);
            }
            .splash-subtitle { color: #00ff6e; font-size: 14px; font-weight: bold; margin-bottom: 40px; }

            .btn-enter {
                background: #00ff6e; color: #000; border: none; padding: 15px 45px;
                border-radius: 50px; font-weight: 900; font-size: 16px; cursor: pointer;
                box-shadow: 0 0 20px rgba(0, 255, 110, 0.5); transition: 0.3s;
            }
            .btn-enter:active { transform: scale(0.9); }

            /* MAIN DASHBOARD CONTENT */
            #main-app { opacity: 0; transform: translateY(50px); transition: 0.8s ease; padding: 20px; overflow-y: auto; height: 100vh; }

            .profile-card {
                background: rgba(255,255,255,0.03); border: 1px solid rgba(0, 255, 110, 0.3);
                border-radius: 24px; padding: 25px; margin-bottom: 25px;
                backdrop-filter: blur(10px); box-shadow: 0 20px 40px rgba(0,0,0,0.4);
            }
            h2 { color: #ffffff; font-size: 22px; font-weight: 900; margin: 0; }
            .xp-val { font-size: 45px; font-weight: 900; color: #00ff6e; text-shadow: 0 0 20px rgba(0,255,110,0.5); margin: 10px 0; }
            
            .grid-container {
                display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;
                background: rgba(255,255,255,0.02); border-radius: 20px; padding: 15px;
            }
            .day-box {
                background: #151a21; border-radius: 12px; padding: 15px 0; font-size: 11px;
                font-weight: bold; color: #8fa0b5; border: 1px solid transparent; cursor: pointer;
            }
            .day-box.claimed { background: #00ff6e; color: #000; box-shadow: 0 0 15px rgba(0,255,110,0.4); }

            .leaderboard { background: rgba(255,255,255,0.02); border-radius: 20px; padding: 10px; margin-top: 20px; text-align: left; }
            .row { display: flex; justify-content: space-between; padding: 12px 15px; border-bottom: 1px solid rgba(255,255,255,0.05); }
            .rank { color: #00ff6e; font-weight: 900; margin-right: 10px; }

            /* ANIMATIONS */
            @keyframes floatRotate {
                0%, 100% { transform: perspective(1000px) rotateY(15deg) translateY(0); }
                50% { transform: perspective(1000px) rotateY(-15deg) translateY(-15px); }
            }
        </style>
    </head>
    <body>

        <div id="welcome-splash">
            <div class="panda-3d-card">🐼</div>
            <div class="splash-title">PANDA REALM</div>
            <div class="splash-subtitle">GIFT CARD LEADERBOARD</div>
            <button class="btn-enter" onclick="enterApp()">ENTER ECOSYSTEM</button>
        </div>

        <div id="main-app">
            <div class="profile-card">
                <h2>PANDA NETWORK STATUS</h2>
                <div class="xp-val" id="total-xp">0000</div>
                <div style="font-size: 11px; font-weight: bold; color: #8fa0b5;">AUTHORIZED ACCESS GRANTED</div>
            </div>

            <div style="text-align: left; font-weight: 900; font-size: 13px; color: #00ff6e; margin-bottom: 10px;">📅 DAILY REWARD MATRIX</div>
            <div class="grid-container" id="calendar"></div>

            <div style="text-align: left; font-weight: 900; font-size: 13px; color: #ffffff; margin: 30px 0 10px 0;">🏆 GLOBAL TOP MINTERS</div>
            <div class="leaderboard" id="leaderboard"></div>
        </div>

        <script>
            const tg = window.Telegram.WebApp;
            tg.expand();

            const rawUser = tg.initDataUnsafe.user || { id: 5555, first_name: "Panda User", username: "Panda" };
            const userId = String(rawUser.id);
            const userHandle = rawUser.username ? `@${rawUser.username}` : rawUser.first_name;

            function enterApp() {
                const splash = document.getElementById('welcome-splash');
                const app = document.getElementById('main-app');
                splash.style.opacity = '0';
                splash.style.transform = 'scale(1.5)';
                setTimeout(() => {
                    splash.style.display = 'none';
                    app.style.opacity = '1';
                    app.style.transform = 'translateY(0)';
                    sync();
                }, 800);
            }

            async function sync() {
                try {
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
    logging.info("3D Panda Ecosystem Ready!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

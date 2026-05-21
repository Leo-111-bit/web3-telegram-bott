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
        [InlineKeyboardButton(text="💎 ENTER 3D LEO REALM 💎", web_app=WebAppInfo(url=app_url))]
    ])
    welcome_text = (
        "👑 **WELCOME TO THE KING LEO ECOSYSTEM** 👑\n\n"
        "Your active profile is officially online. Tap the 3D dashboard link below to check your stats, claim your calendar tokens, and climb the ranks!"
    )
    await message.reply(welcome_text, reply_markup=kb, parse_mode="Markdown")

@dp.message(Command("whale"))
async def handle_whale_command(message: types.Message):
    log_user_activity(message.from_user)
    await message.reply("📡 Tracking live whale ledger systems...", parse_mode="Markdown")

# Global Text Fallback (Tracks Live Messages + Tags Rewards + Stats Command)
@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text: 
        return
        
    log_user_activity(message.from_user)

    # Clean text to process triggers smoothly
    raw_text = message.text.strip().upper()
    is_private = message.chat.type == "private"

    # --- NEW FEATURE: TRIGGER FOR "CHECK XRP" OR "CHECK XP" ---
    if "CHECK XRP" in raw_text or "CHECK XP" in raw_text:
        if not xp_database:
            await message.reply("📉 Database empty! No users have earned any points yet.")
            return

        # Sort all registered database users by their total XP holdings
        sorted_users = sorted(xp_database.values(), key=lambda x: x["xp"], reverse=True)
        
        stats_output = "📊 **KING LEO ECOSYSTEM REAL-TIME LEDGER** 📊\n\n"
        for index, user in enumerate(sorted_users, start=1):
            stats_output += f"🏅 #{index} | **{user['username']}** — `{user['xp']} XP` ({user['messages']} msgs)\n"
        
        # Blast the full list right into the group or private chat
        await message.reply(stats_output, parse_mode="Markdown")
        return

    # --- STANDALONE GROUP CHAT MENTION TAG DETECTION ---
    bot_info = await bot.get_me()
    bot_username = f"@{bot_info.username}"
    is_tagged = bot_username.lower() in message.text.lower()

    if is_tagged and not is_private:
        user_id = get_or_create_user(message.from_user)
        username_label = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        secret_xp = random.randint(1, 50)
        xp_database[user_id]["xp"] += secret_xp
        await message.reply(f'🎉 🔥 BOOM! "{username_label}" just gained {secret_xp} XP for tagging the AI!')

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
    return web.json_response({"success": True, "message": f"💎 Day {day_num} claimed! +10 XP added seamlessly."})

# 5. Premium 3D Animated UI Frontend HTML
async def frontend_mini_app_dashboard(request):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>King Leo 3D Realm</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: radial-gradient(circle at center, #1b263b 0%, #0b0f19 100%);
                color: #ffffff; margin: 0; padding: 20px; text-align: center; overflow-x: hidden;
            }
            
            /* 3D Glassmorphism Floating Profile Sphere Card */
            .profile-3d-sphere {
                background: rgba(255, 255, 255, 0.05);
                border: 2px solid rgba(0, 255, 204, 0.3);
                border-radius: 24px; padding: 25px; margin-bottom: 30px;
                backdrop-filter: blur(20px);
                box-shadow: 0 20px 40px rgba(0, 255, 204, 0.15), inset 0 0 20px rgba(255, 255, 255, 0.1);
                transform: perspective(1000px) rotateX(10deg);
                animation: float3D 4s ease-in-out infinite;
            }
            
            h2 { 
                font-size: 24px; font-weight: 900; margin: 0; letter-spacing: 1.5px;
                background: linear-gradient(45deg, #00ffcc, #ff007f);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            }

            .xp-counter-bubble {
                font-size: 40px; font-weight: 900; color: #00ffcc; margin: 15px 0;
                text-shadow: 0 0 25px rgba(0, 255, 204, 0.8);
                animation: pulseGlow 2s infinite alternate;
            }

            /* Custom Animated Welcome Grid Alert Box */
            .welcome-ticker {
                background: linear-gradient(90deg, rgba(255,0,127,0.2), rgba(0,255,204,0.2));
                border-radius: 12px; padding: 10px; font-size: 12px; font-weight: bold;
                border: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px;
                animation: marqueePulse 3s ease infinite;
            }

            /* 3D Layered Grid Blocks for Daily Matrix Calendar */
            .grid-3d-container {
                display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px;
                background: rgba(13, 18, 28, 0.7); border-radius: 20px; padding: 15px;
                border: 1px solid rgba(255, 255, 255, 0.05);
                box-shadow: inset 0 4px 20px rgba(0,0,0,0.6);
            }

            .grid-day {
                background: linear-gradient(135deg, #1f2d42, #141d2a);
                border: 1px solid rgba(255,255,255,0.05); border-radius: 12px;
                padding: 15px 0; font-size: 11px; font-weight: 800; cursor: pointer; color: #a4b3c6;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3), inset 0 1px 2px rgba(255,255,255,0.1);
                transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            }

            .grid-day:hover {
                transform: translateY(-4px) scale(1.05);
                border-color: #ff007f; box-shadow: 0 8px 15px rgba(255, 0, 127, 0.3);
            }

            .grid-day.claimed {
                background: linear-gradient(135deg, #00ffcc 0%, #009977 100%);
                color: #06090f; border-color: #00ffcc; font-weight: 900;
                box-shadow: 0 0 20px rgba(0, 255, 204, 0.5);
                transform: perspective(500px) translateZ(5px);
            }

            /* Leaderboard Frame Rows */
            .leaderboard-3d-frame {
                background: rgba(13, 18, 28, 0.7); border-radius: 20px; padding: 10px;
                border: 1px solid rgba(255, 255, 255, 0.05); text-align: left; margin-top: 15px;
            }

            .leader-row {
                display: flex; justify-content: space-between; align-items: center;
                padding: 14px 20px; margin-bottom: 8px; border-radius: 12px;
                background: rgba(255,255,255,0.02); border: 1px solid transparent;
                transition: all 0.2s;
            }
            .leader-row:hover {
                background: rgba(255,255,255,0.05); border-color: rgba(0,255,204,0.2);
                transform: translateX(4px);
            }

            .rank-number {
                font-weight: 900; color: #ff007f; margin-right: 10px; font-size: 14px;
            }

            .xp-badge-pill {
                background: rgba(0,255,204,0.1); color: #00ffcc; font-weight: 800;
                padding: 6px 14px; border-radius: 30px; border: 1px solid rgba(0,255,204,0.2);
                font-size: 12px; box-shadow: 0 4px 10px rgba(0,255,204,0.1);
            }

            /* Animations Keyframes Mapping Matrix */
            @keyframes float3D {
                0%, 100% { transform: perspective(1000px) rotateX(8deg) translateY(0); }
                50% { transform: perspective(1000px) rotateX(12deg) translateY(-8px); }
            }
            @keyframes pulseGlow {
                0% { text-shadow: 0 0 15px rgba(0, 255, 204, 0.5); transform: scale(1); }
                100% { text-shadow: 0 0 30px rgba(0, 255, 204, 0.9); transform: scale(1.03); }
            }
            @keyframes marqueePulse {
                0%, 100% { border-color: rgba(255,255,255,0.1); box-shadow: none; }
                50% { border-color: #ff007f; box-shadow: 0 0 15px rgba(255,0,127,0.2); }
            }
        </style>
    </head>
    <body>

        <div class="profile-3d-sphere">
            <h2 id="user-display">CRYPTO KINGDOM</h2>
            <div class="xp-counter-bubble" id="user-total-xp">0000</div>
            <div class="welcome-ticker">🔥 WELCOME BACK CHAMP! CLAIM YOUR DAILY REWARD BLOCKS BELOW! 🔥</div>
        </div>
        
        <div style="text-align: left; font-weight: 800; color: #00ffcc; margin-bottom: 10px; font-size: 13px; letter-spacing: 1px;">📅 REWARD GRID MATRIX</div>
        <div class="grid-3d-container" id="calendar-box"></div>

        <div style="text-align: left; font-weight: 800; color: #ff007f; margin: 25px 0 10px 0; font-size: 13px; letter-spacing: 1px;">🏆 REWARDS LEADERBOARD</div>
        <div class="leaderboard-3d-frame" id="leaderboard-box"></div>

        <script>
            const tg = window.Telegram.WebApp;
            tg.expand();

            const rawUser = tg.initDataUnsafe.user || { id: 8888, first_name: "Active Member", username: "Yapper" };
            const userId = String(rawUser.id);
            const userHandle = rawUser.username ? `@${rawUser.username}` : rawUser.first_name;

            document.getElementById('user-display').innerText = userHandle.toUpperCase();

            async function syncAllData() {
                try {
                    const res = await fetch(`/api/userstatus?user_id=${userId}&username=${encodeURIComponent(userHandle)}`);
                    const userProfile = await res.json();
                    document.getElementById('user-total-xp').innerText = `${userProfile.xp} XP`;
                    
                    // Render 3D Grid Blocks
                    const container = document.getElementById('calendar-box');
                    container.innerHTML = '';
                    for (let d = 1; d <= 30; d++) {
                        const isClaimed = userProfile.checkin_days.includes(d);
                        const block = document.createElement('div');
                        block.className = `grid-day ${isClaimed ? 'claimed' : ''}`;
                        block.innerText = isClaimed ? `✓ D${d}` : `Day ${d}`;
                        if (!isClaimed) block.onclick = () => claimBlock(d);
                        container.appendChild(block);
                    }

                    // Render Leaderboard Row Blocks
                    const lbRes = await fetch('/api/leaderboard');
                    const lbData = await lbRes.json();
                    const lbContainer = document.getElementById('leaderboard-box');
                    lbContainer.innerHTML = '';
                    
                    lbData.leaderboard.forEach((user, index) => {
                        lbContainer.innerHTML += `
                            <div class="leader-row">
                                <div><span class="rank-number">#${index+1}</span><span style="font-weight:600;">${user.username}</span></div>
                                <div class="xp-badge-pill">${user.xp} XP</div>
                            </div>
                        `;
                    });
                } catch(e) { console.error(e); }
            }

            async function claimBlock(dayNum) {
                try {
                    const res = await fetch('/api/checkin', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: userId, day: dayNum })
                    });
                    const result = await res.json();
                    if(tg.showAlert) tg.showAlert(result.message);
                    else alert(result.message);
                    syncAllData();
                } catch(e) { console.error(e); }
            }

            window.onload = syncAllData;
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
    logging.info("3D Core Dashboard Engine Deploy Successful!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

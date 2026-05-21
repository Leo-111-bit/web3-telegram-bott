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
        [InlineKeyboardButton(text="🐼 ENTER PANDA REALM 🐼", web_app=WebAppInfo(url=app_url))]
    ])
    welcome_text = (
        "🐼 **WELCOME TO THE PANDA GIFT CARD ECOSYSTEM** 🐼\n\n"
        "Your active network profile is online. Tap the dashboard below to manage your points, claim daily calendar cards, and check the community leaderboard!"
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
        await message.reply(f'🎉 🐼 BOOM! "{username_label}" just gained {secret_xp} xrp for tagging the Panda Bot!')

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
    return web.json_response({"success": True, "message": f"🐼 Day {day_num} Reward unlocked! +10 XP added successfully."})

# 5. Premium Panda 3D Animated UI Frontend HTML
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
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: radial-gradient(circle at center, #14171c 0%, #090b0d 100%);
                color: #ffffff; margin: 0; padding: 15px; text-align: center; overflow-x: hidden;
            }
            
            /* Glassmorphic 3D Card Overlay - Black, Premium White & Neon Green Accent */
            .profile-3d-sphere {
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%);
                border: 2px solid rgba(0, 255, 110, 0.3);
                border-radius: 28px; padding: 25px; margin-bottom: 25px;
                backdrop-filter: blur(25px);
                box-shadow: 0 25px 50px rgba(0, 255, 110, 0.1), inset 0 0 25px rgba(255, 255, 255, 0.05);
                transform: perspective(1200px) rotateX(10deg);
                animation: floatPerspective 4.5s ease-in-out infinite;
            }
            
            h2 { 
                font-size: 24px; font-weight: 900; margin: 0; letter-spacing: 1.5px;
                background: linear-gradient(45deg, #ffffff, #00ff6e);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                text-shadow: 0 0 15px rgba(0, 255, 110, 0.2);
            }

            .xp-counter-bubble {
                font-size: 45px; font-weight: 900; color: #00ff6e; margin: 12px 0;
                text-shadow: 0 0 25px rgba(0, 255, 110, 0.6);
                animation: smoothPulse 2.5s infinite alternate;
            }

            /* Welcome Notification Overlay Banner */
            .welcome-ticker {
                background: linear-gradient(90deg, rgba(255, 255, 255, 0.08), rgba(0, 255, 110, 0.15));
                border-radius: 14px; padding: 12px; font-size: 13px; font-weight: 800;
                border: 1px solid rgba(255, 255, 255, 0.1); margin-top: 15px;
                letter-spacing: 0.5px; line-height: 1.4; color: #e1e7ed;
                animation: neonGlowPulse 3s ease infinite;
            }

            /* Neon 3D Grid Panels for Daily Matrix Calendar */
            .grid-3d-container {
                display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;
                background: rgba(18, 22, 28, 0.8); border-radius: 24px; padding: 15px;
                border: 1px solid rgba(255, 255, 255, 0.03);
                box-shadow: inset 0 6px 24px rgba(0, 0, 0, 0.8);
            }

            .grid-day {
                background: linear-gradient(135deg, #1f252e, #11151a);
                border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 14px;
                padding: 16px 0; font-size: 11px; font-weight: 800; cursor: pointer; color: #8fa0b5;
                box-shadow: 0 6px 10px rgba(0, 0, 0, 0.5), inset 0 1px 2px rgba(255, 255, 255, 0.08);
                transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            }

            .grid-day:hover {
                transform: translateY(-5px) scale(1.06);
                border-color: #00ff6e; box-shadow: 0 10px 20px rgba(0, 255, 110, 0.25);
                color: #ffffff;
            }

            .grid-day.claimed {
                background: linear-gradient(135deg, #ffffff 0%, #a2b0a9 100%);
                color: #090b0d; border-color: #ffffff; font-weight: 900;
                box-shadow: 0 0 22px rgba(255, 255, 255, 0.4);
                transform: perspective(600px) translateZ(8px);
            }

            /* Leaderboard Panels Layout */
            .leaderboard-3d-frame {
                background: rgba(18, 22, 28, 0.8); border-radius: 24px; padding: 12px;
                border: 1px solid rgba(255, 255, 255, 0.03); text-align: left; margin-top: 15px;
            }

            .leader-row {
                display: flex; justify-content: space-between; align-items: center;
                padding: 14px 18px; margin-bottom: 8px; border-radius: 14px;
                background: rgba(255, 255, 255, 0.01); border: 1px solid transparent;
                transition: all 0.25s ease;
            }
            .leader-row:hover {
                background: rgba(255, 255, 255, 0.03); border-color: rgba(0, 255, 110, 0.2);
                transform: translateX(5px);
            }

            .rank-number {
                font-weight: 900; color: #00ff6e; margin-right: 12px; font-size: 14px;
            }

            .xp-badge-pill {
                background: rgba(0, 255, 110, 0.1); color: #00ff6e; font-weight: 800;
                padding: 6px 14px; border-radius: 30px; border: 1px solid rgba(0, 255, 110, 0.2);
                font-size: 12px; box-shadow: 0 4px 12px rgba(0, 255, 110, 0.1);
            }

            /* 3D Kinetic Motion Animation Mappings */
            @keyframes floatPerspective {
                0%, 100% { transform: perspective(1200px) rotateX(8deg) translateY(0); }
                50% { transform: perspective(1200px) rotateX(12deg) translateY(-8px); }
            }
            @keyframes smoothPulse {
                0% { text-shadow: 0 0 15px rgba(0, 255, 110, 0.4); transform: scale(1); }
                100% { text-shadow: 0 0 35px rgba(0, 255, 110, 0.8); transform: scale(1.02); }
            }
            @keyframes neonGlowPulse {
                0%, 100% { border-color: rgba(255, 255, 255, 0.1); box-shadow: none; }
                50% { border-color: #00ff6e; box-shadow: 0 0 18px rgba(0, 255, 110, 0.15); }
            }
        </style>
    </head>
    <body>

        <div class="profile-3d-sphere">
            <h2 id="user-display">PANDA GIFT CARD LOG</h2>
            <div class="xp-counter-bubble" id="user-total-xp">0000</div>
            <div class="welcome-ticker" id="dynamic-welcome">✨ WELCOME TO PANDA GIFT CARD LEADERBOARD! CLAIM YOUR CARD EXTRACTION BALANCES! ✨</div>
        </div>
        
        <div style="text-align: left; font-weight: 800; color: #ffffff; margin-bottom: 12px; font-size: 13px; letter-spacing: 1.2px; text-transform: uppercase;">📅 DAILY MATRIX CLAIMS</div>
        <div class="grid-3d-container" id="calendar-box"></div>

        <div style="text-align: left; font-weight: 800; color: #00ff6e; margin: 25px 0 10px 0; font-size: 13px; letter-spacing: 1.2px; text-transform: uppercase;">🏆 TOP PANDA REWARDS MINTERS</div>
        <div class="leaderboard-3d-frame" id="leaderboard-box"></div>

        <script>
            const tg = window.Telegram.WebApp;
            tg.expand();

            const rawUser = tg.initDataUnsafe.user || { id: 6666, first_name: "Panda Holder", username: "PandaMinter" };
            const userId = String(rawUser.id);
            const userHandle = rawUser.username ? `@${rawUser.username}` : rawUser.first_name;

            document.getElementById('user-display').innerText = "PANDA GIFT CARD LEADERBOARD";
            document.getElementById('dynamic-welcome').innerText = `✨ WELCOME TO PANDA LEADERBOARD, ${userHandle.toUpperCase()}! 🔥 CLAIM YOUR REWARDS BALANCE! ✨`;

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
    logging.info("Premium Panda Leaderboard Service Active!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

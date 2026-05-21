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
    username = f"@{user.username}" if user.username else user.first_name
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    if user.username:
        user_registry[f"@{user.username.lower()}"] = user.id

    if user_id not in xp_database:
        xp_database[user_id] = {
            "username": username,
            "messages": 0,
            "xp": 0,
            "last_active": today,
            "last_checkin": "",
            "checkin_days": [],
            "last_tag_claim": ""  # Tracks the exact date of their last tag reward
        }
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

# PRIVATE CHAT (DM): Correct Welcome Card Routing with Panda Style
@dp.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def handle_start_command_private(message: types.Message):
    log_user_activity(message.from_user)
    app_url = WEB_APP_URL if WEB_APP_URL else f"https://google.com"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐼 WELCOME TO PD CARD 🐼", web_app=WebAppInfo(url=app_url))]
    ])
    
    welcome_text = (
        "🐼 **WELCOME TO PD CARD** 🐼\n\n"
        "Your global gift card premium index profile is live! Tap the digital voucher dashboard button below to sync your profile, claim daily bonus allocations, and view the trading desk leaderboard."
    )
    await message.reply(welcome_text, reply_markup=kb, parse_mode="Markdown")

@dp.message(Command("whale"))
async def handle_whale_command(message: types.Message):
    log_user_activity(message.from_user)
    await message.reply("📡 Tracking live gift card allocation ledgers...", parse_mode="Markdown")

# GLOBAL MESSAGE HANDLER: Handles Leaderboard & Group Mentions
@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text: 
        return
        
    log_user_activity(message.from_user)

    raw_text = message.text.strip().upper()
    is_private = message.chat.type == ChatType.PRIVATE

    # --- TRIGGER FOR "CHECK XRP" OR "CHECK XP" ---
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

    # --- STANDALONE GROUP CHAT MENTION TAG DETECTION (WITH 24H LOCK) ---
    bot_info = await bot.get_me()
    bot_username = f"@{bot_info.username}"
    is_tagged = bot_username.lower() in message.text.lower()

    if is_tagged and not is_private:
        # 24-HOUR STALE MESSAGE GATE
        now = datetime.datetime.now(datetime.timezone.utc)
        time_difference = (now - message.date).total_seconds()
        if time_difference > 86400:
            return  # Drop old messages or system sync delays

        user_id = get_or_create_user(message.from_user)
        username_label = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        today_str = now.strftime("%Y-%m-%d")
        
        user_profile = xp_database[user_id]
        
        # Check if they already claimed the tag reward today (24h lapse)
        if user_profile.get("last_tag_claim") == today_str:
            await message.reply(f"🐼 Welcome back to the counter, {username_label}! Your daily mention allocation is locked. Let's trade gift cards! 💳")
        else:
            secret_xp = random.randint(20, 50)
            user_profile["xp"] += secret_xp
            user_profile["last_tag_claim"] = today_str  # Lock it until next UTC date roll
            
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
    if user_id not in xp_database:
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        xp_database[user_id] = {"username": username, "messages": 0, "xp": 0, "last_active": today, "last_checkin": "", "checkin_days": [], "last_tag_claim": ""}
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

# ==========================================
# 5. PREMIUM 3D PANDA WEB APP UI
# ==========================================
async def frontend_mini_app_dashboard(request):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PD Card - Premium Trading Desk</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: radial-gradient(circle at center, #14121f 0%, #08070d 100%);
                color: #ffffff; margin: 0; padding: 20px; text-align: center; overflow-x: hidden;
            }
            
            /* 3D Premium Holographic Gift Card Container */
            .giftcard-3d-frame {
                background: linear-gradient(135deg, rgba(30, 27, 54, 0.8) 0%, rgba(15, 12, 28, 0.9) 100%);
                border: 2px solid rgba(168, 85, 247, 0.4);
                border-radius: 20px; padding: 25px; margin-bottom: 30px;
                position: relative; overflow: hidden;
                box-shadow: 0 25px 50px -12px rgba(168, 85, 247, 0.25), inset 0 1px 1px rgba(255,255,255,0.1);
                transform: perspective(1000px) rotateX(12deg) rotateY(-5deg);
                transition: transform 0.3s ease;
            }

            .giftcard-3d-frame::before {
                content: ''; position: absolute; top: -50%; left: -50%;
                width: 200%; height: 200%;
                background: linear-gradient(45deg, transparent, rgba(255,255,255,0.1), transparent);
                transform: rotate(45deg); animation: holoShine 6s infinite linear;
            }
            
            .brand-logo-text { 
                font-size: 26px; font-weight: 900; margin: 0; letter-spacing: 2px; text-align: left;
                background: linear-gradient(90deg, #a855f7, #f43f5e);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            }

            .panda-badge {
                position: absolute; top: 20px; right: 20px; font-size: 32px;
                filter: drop-shadow(0 0 10px rgba(168, 85, 247, 0.6));
            }

            .voucher-balance-display {
                font-size: 45px; font-weight: 900; color: #ffffff; margin: 25px 0 10px 0;
                text-align: left; font-family: monospace; letter-spacing: -1px;
                text-shadow: 0 0 20px rgba(168, 85, 247, 0.4);
            }

            .card-meta-row {
                display: flex; justify-content: space-between; font-size: 11px;
                color: #a78bfa; font-weight: bold; letter-spacing: 1px; text-transform: uppercase;
                border-top: 1px solid rgba(255,255,255,0.08); padding-top: 15px; margin-top: 15px;
            }

            /* Custom Ticker Marquee Bar */
            .ticker-banner {
                background: rgba(15, 12, 28, 0.6); border-radius: 12px; padding: 10px;
                font-size: 11px; font-weight: 700; color: #f43f5e;
                border: 1px dashed rgba(244, 63, 94, 0.3); margin-bottom: 25px;
            }

            /* Gift Card Voucher Daily Checkin Grid Layout */
            .voucher-grid-matrix {
                display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
                background: rgba(15, 12, 28, 0.8); border-radius: 16px; padding: 15px;
                border: 1px solid rgba(255, 255, 255, 0.03);
            }

            .voucher-ticket {
                background: #1e1b36; border: 1px solid rgba(255,255,255,0.05); border-radius: 10px;
                padding: 12px 0; font-size: 11px; font-weight: 800; cursor: pointer; color: #94a3b8;
                position: relative; transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            }

            .voucher-ticket:hover {
                transform: scale(1.05) translateZ(10px);
                border-color: #a855f7; box-shadow: 0 10px 15px -3px rgba(168, 85, 247, 0.4);
            }

            .voucher-ticket::before, .voucher-ticket::after {
                content: ''; position: absolute; width: 8px; height: 8px;
                background: #08070d; border-radius: 50%; top: 50%; transform: translateY(-50%);
            }
            .voucher-ticket::before { left: -5px; }
            .voucher-ticket::after { right: -5px; }

            .voucher-ticket.redeemed {
                background: linear-gradient(135deg, #f43f5e 0%, #a855f7 100%);
                color: #ffffff; border-color: transparent; font-weight: 900;
                box-shadow: 0 0 15px rgba(168, 85, 247, 0.4);
            }

            /* Leaderboard Configurations */
            .desk-leaderboard-frame {
                background: rgba(15, 12, 28, 0.8); border-radius: 16px; padding: 10px;
                border: 1px solid rgba(255, 255, 255, 0.03); text-align: left; margin-top: 15px;
            }

            .leader-desk-row {
                display: flex; justify-content: space-between; align-items: center;
                padding: 12px 16px; margin-bottom: 6px; border-radius: 10px;
                background: rgba(255,255,255,0.01); border-left: 3px solid transparent;
            }
            .leader-desk-row:hover {
                background: rgba(255,255,255,0.03); border-left-color: #a855f7;
            }

            .rank-index {
                font-weight: 900; color: #f43f5e; margin-right: 8px;
            }

            .credit-score-badge {
                background: rgba(168, 85, 247, 0.15); color: #c084fc; font-weight: 800;
                padding: 4px 12px; border-radius: 8px; font-size: 12px; border: 1px solid rgba(168, 85, 247, 0.2);
            }

            @keyframes holoShine {
                0% { transform: translate(-30%, -30%) rotate(45deg); }
                100% { transform: translate(30%, 30%) rotate(45deg); }
            }
        </style>
    </head>
    <body>

        <div class="giftcard-3d-frame" id="main-card">
            <div class="brand-logo-text">PD CARD</div>
            <div class="panda-badge">🐼</div>
            <div class="voucher-balance-display" id="user-total-xp">00.00 XP</div>
            
            <div class="card-meta-row">
                <div id="user-display">TRADER INDEX</div>
                <div>SECURE VOUCHER WALLET</div>
            </div>
        </div>
        
        <div class="ticker-banner">⚡ SECURE GIFT CARD EXCHANGE DESK • DAILY ALLOCATIONS LIVE ⚡</div>

        <div style="text-align: left; font-weight: 800; color: #a855f7; margin-bottom: 12px; font-size: 13px; letter-spacing: 1px;">🎫 REDEEM DAY COUPONS</div>
        <div class="voucher-grid-matrix" id="calendar-box"></div>

        <div style="text-align: left; font-weight: 800; color: #f43f5e; margin: 25px 0 12px 0; font-size: 13px; letter-spacing: 1px;">🏆 GLOBAL DESK INDEX</div>
        <div class="desk-leaderboard-frame" id="leaderboard-box"></div>

        <script>
            const tg = window.Telegram.WebApp;
            tg.expand();

            const card = document.getElementById('main-card');
            document.addEventListener('mousemove', (e) => {
                const xAxis = (window.innerWidth / 2 - e.pageX) / 25;
                const yAxis = (window.innerHeight / 2 - e.pageY) / 25;
                card.style.transform = `perspective(1000px) rotateY(${xAxis}deg) rotateX(${yAxis}deg)`;
            });

            const rawUser = tg.initDataUnsafe.user || { id: 7777, first_name: "Active Trader", username: "Panda_X" };
            const userId = String(rawUser.id);
            const userHandle = rawUser.username ? `@${rawUser.username}` : rawUser.first_name;

            document.getElementById('user-display').innerText = userHandle.toUpperCase();

            async function syncAllData() {
                try {
                    const res = await fetch(`/api/userstatus?user_id=${userId}&username=${encodeURIComponent(userHandle)}`);
                    const userProfile = await res.json();
                    document.getElementById('user-total-xp').innerText = `${userProfile.xp}.00 XP`;
                    
                    const container = document.getElementById('calendar-box');
                    container.innerHTML = '';
                    for (let d = 1; d <= 24; d++) {
                        const isClaimed = userProfile.checkin_days.includes(d);
                        const coupon = document.createElement('div');
                        coupon.className = `voucher-ticket ${isClaimed ? 'redeemed' : ''}`;
                        coupon.innerText = isClaimed ? `CLAIMED` : `COUPON 0${d}`;
                        if (!isClaimed) coupon.onclick = () => claimCoupon(d);
                        container.appendChild(coupon);
                    }

                    const lbRes = await fetch('/api/leaderboard');
                    const lbData = await lbRes.json();
                    const lbContainer = document.getElementById('leaderboard-box');
                    lbContainer.innerHTML = '';
                    
                    lbData.leaderboard.forEach((user, index) => {
                        lbContainer.innerHTML += `
                            <div class="leader-desk-row">
                                <div><span class="rank-index">#${index+1}</span><span style="font-weight:600;">${user.username}</span></div>
                                <div class="credit-score-badge">${user.xp} XP</div>
                            </div>
                        `;
                    });
                } catch(e) { console.error(e); }
            }

            async function claimCoupon(dayNum) {
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
    logging.info("PD Card Trading Engine Deploy Successful!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

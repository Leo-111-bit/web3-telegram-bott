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
            "last_wheel_spin": ""  # Added to track daily lucky dip wheel spin
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
# 5. PREMIUM 3D PANDA WEB APP UI WITH CALCULATOR & SPIN WHEEL
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
            .giftcard-3d-frame {
                background: linear-gradient(135deg, rgba(30, 27, 54, 0.8) 0%, rgba(15, 12, 28, 0.9) 100%);
                border: 2px solid rgba(168, 85, 247, 0.4);
                border-radius: 20px; padding: 25px; margin-bottom: 25px;
                position: relative; overflow: hidden;
                box-shadow: 0 25px 50px -12px rgba(168, 85, 247, 0.25), inset 0 1px 1px rgba(255,255,255,0.1);
                transform: perspective(1000px) rotateX(8deg);
            }
            .brand-logo-text { 
                font-size: 26px; font-weight: 900; margin: 0; letter-spacing: 2px; text-align: left;
                background: linear-gradient(90deg, #a855f7, #f43f5e); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            }
            .panda-badge { position: absolute; top: 20px; right: 20px; font-size: 32px; filter: drop-shadow(0 0 10px rgba(168, 85, 247, 0.6)); }
            .voucher-balance-display {
                font-size: 45px; font-weight: 900; color: #ffffff; margin: 25px 0 10px 0;
                text-align: left; font-family: monospace; text-shadow: 0 0 20px rgba(168, 85, 247, 0.4);
            }
            .card-meta-row { display: flex; justify-content: space-between; font-size: 11px; color: #a78bfa; font-weight: bold; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 15px; margin-top: 15px; }
            .ticker-banner { background: rgba(15, 12, 28, 0.6); border-radius: 12px; padding: 10px; font-size: 11px; font-weight: 700; color: #f43f5e; border: 1px dashed rgba(244, 63, 94, 0.3); margin-bottom: 25px; }
            
            /* Section Panel Framework Style */
            .feature-section-panel {
                background: rgba(15, 12, 28, 0.8); border-radius: 18px; padding: 20px; margin-bottom: 25px;
                border: 1px solid rgba(255, 255, 255, 0.04); text-align: left;
            }
            .section-header-title { font-weight: 800; color: #a855f7; margin-bottom: 15px; font-size: 14px; letter-spacing: 1px; text-transform: uppercase; display: flex; align-items: center; gap: 8px; }
            
            /* feature 1: Rate Calculator Layout styling */
            .calc-input-box { width: 100%; padding: 12px; background: #1e1b36; border: 1px solid rgba(168,85,247,0.3); border-radius: 10px; color: white; font-size: 15px; margin-bottom: 15px; box-sizing: border-box; }
            .calc-output-payout { background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.3); padding: 15px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: 900; color: #f43f5e; }

            /* feature 2: 3D Wheel of Fortune Layout components */
            .wheel-outer-wrapper { display: flex; flex-direction: column; align-items: center; position: relative; margin: 15px 0; }
            .wheel-spinner-canvas {
                width: 260px; height: 260px; border-radius: 50%; border: 6px solid #a855f7;
                background: conic-gradient(#1e1b36 0deg 60deg, #f43f5e 60deg 120deg, #2e2a54 120deg 180deg, #a855f7 180deg 240deg, #121024 240deg 300deg, #ec4899 300deg 360deg);
                box-shadow: 0 0 30px rgba(168, 85, 247, 0.4); transition: transform 4s cubic-bezier(0.1, 0.8, 0.25, 1); position: relative;
            }
            .wheel-pin-indicator { width: 0; height: 0; border-left: 15px solid transparent; border-right: 15px solid transparent; border-top: 25px solid #ffffff; position: absolute; top: -10px; z-index: 10; filter: drop-shadow(0 4px 5px rgba(0,0,0,0.5)); }
            .spin-trigger-btn { margin-top: 20px; width: 80%; background: linear-gradient(90deg, #a855f7, #f43f5e); border: none; padding: 12px; border-radius: 12px; color: white; font-weight: 900; font-size: 14px; cursor: pointer; box-shadow: 0 5px 15px rgba(244,63,94,0.4); }

            /* 30 Days Coupon Grid Matrix configuration */
            .voucher-grid-matrix { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
            .voucher-ticket { background: #1e1b36; border: 1px solid rgba(255,255,255,0.05); border-radius: 10px; padding: 14px 0; font-size: 11px; font-weight: 800; cursor: pointer; color: #94a3b8; text-align: center; position: relative; transition: all 0.2s ease; }
            .voucher-ticket:hover { transform: scale(1.05); border-color: #a855f7; }
            .voucher-ticket::before, .voucher-ticket::after { content: ''; position: absolute; width: 6px; height: 6px; background: #08070d; border-radius: 50%; top: 50%; transform: translateY(-50%); }
            .voucher-ticket::before { left: -4px; }
            .voucher-ticket::after { right: -4px; }
            .voucher-ticket.redeemed { background: linear-gradient(135deg, #f43f5e 0%, #a855f7 100%); color: #ffffff; border-color: transparent; font-weight: 900; box-shadow: 0 0 10px rgba(168, 85, 247, 0.3); }
            
            .leader-desk-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; margin-bottom: 6px; border-radius: 10px; background: rgba(255,255,255,0.01); }
            .rank-index { font-weight: 900; color: #f43f5e; margin-right: 8px; }
            .credit-score-badge { background: rgba(168, 85, 247, 0.15); color: #c084fc; font-weight: 800; padding: 4px 12px; border-radius: 8px; font-size: 12px; border: 1px solid rgba(168, 85, 247, 0.2); }
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
        <div class="ticker-banner">⚡ SECURE GIFT CARD EXCHANGE DESK • PREMIUM ALLOCATIONS ENGAGED ⚡</div>

        <div class="feature-section-panel">
            <div class="section-header-title">📈 Live Voucher Rate Index</div>
            <select class="calc-input-box" id="card-type" onchange="runCalculation()">
                <option value="920">Apple iTunes Gift Card (Premium) - ₦920/$</option>
                <option value="950">Razer Gold Allocation Voucher - ₦950/$</option>
                <option value="890">Steam Wallet Code Index - ₦890/$</option>
                <option value="870">Vanilla Visa / Amex Protocol - ₦870/$</option>
            </select>
            <input type="number" class="calc-input-box" id="card-amount" placeholder="Enter Card Value Amount ($)" value="100" oninput= "runCalculation()">
            <div class="calc-output-payout" id="payout-payout">ESTIMATED PAYOUT: ₦95,000</div>
        </div>

        <div class="feature-section-panel" style="text-align: center;">
            <div class="section-header-title" style="justify-content: center;">🎡 Lucky Panda Spin Wheel</div>
            <div class="wheel-outer-wrapper">
                <div class="wheel-pin-indicator"></div>
                <div class="wheel-spinner-canvas" id="spin-wheel"></div>
            </div>
            <button class="spin-trigger-btn" onclick="executeLuckySpin()">TRIGGER COOLDOWN SPIN</button>
        </div>

        <div class="feature-section-panel">
            <div class="section-header-title">🎫 30-Day Allocation Grid Matrix</div>
            <div class="voucher-grid-matrix" id="calendar-box"></div>
        </div>

        <div class="feature-section-panel">
            <div class="section-header-title">🏆 Global Trading Desk Index</div>
            <div id="leaderboard-box"></div>
        </div>

        <script>
            const tg = window.Telegram.WebApp;
            tg.expand();

            const rawUser = tg.initDataUnsafe.user || { id: 7777, first_name: "Active Trader" };
            const userId = String(rawUser.id);
            let userHandle = rawUser.username ? `@${rawUser.username}` : (rawUser.first_name || "Trader");

            document.getElementById('user-display').innerText = userHandle.toUpperCase();

            function runCalculation() {
                const rate = parseFloat(document.getElementById('card-type').value);
                const amt = parseFloat(document.getElementById('card-amount').value) || 0;
                const calculation = rate * amt;
                document.getElementById('payout-payout').innerText = `ESTIMATED PAYOUT: ₦${calculation.toLocaleString()}`;
            }

            async function executeLuckySpin() {
                try {
                    const res = await fetch('/api/spinwheel', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: userId })
                    });
                    const result = await res.json();
                    if (!result.success) {
                        if(tg.showAlert) tg.showAlert(result.message); else alert(result.message);
                        return;
                    }
                    
                    // 3D Matrix Spin Canvas Rotation Angles Execution
                    const targetDegrees = (result.slice_index * 60) + 1440 + Math.floor(Math.random() * 30);
                    const wheel = document.getElementById('spin-wheel');
                    wheel.style.transform = `rotate(-${targetDegrees}deg)`;
                    
                    setTimeout(() => {
                        if(tg.showAlert) tg.showAlert(result.message); else alert(result.message);
                        syncAllData();
                    }, 4100);
                } catch(e) { console.error(e); }
            }

            async function syncAllData() {
                try {
                    const res = await fetch(`/api/userstatus?user_id=${userId}&username=${encodeURIComponent(userHandle)}`);
                    const userProfile = await res.json();
                    document.getElementById('user-total-xp').innerText = `${userProfile.xp}.00 XP`;
                    
                    const container = document.getElementById('calendar-box');
                    container.innerHTML = '';
                    
                    // Render Expanded 30-Day Sequence Configuration
                    for (let d = 1; d <= 30; d++) {
                        const isClaimed = userProfile.checkin_days.includes(d);
                        const coupon = document.createElement('div');
                        coupon.className = `voucher-ticket ${isClaimed ? 'redeemed' : ''}`;
                        coupon.innerText = isClaimed ? `✓ D${d}` : `DAY ${d}`;
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
                    if(tg.showAlert) tg.showAlert(result.message); else alert(result.message);
                    syncAllData();
                } catch(e) { console.error(e); }
            }

            window.onload = () => { syncAllData(); runCalculation(); };
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
    app.router.add_post("/api/spinwheel", api_execute_spin) # Hook up the spin handler endpoint
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

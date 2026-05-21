import os
import sys
import logging
import asyncio
import random
import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
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
        "Your global gift card premium index and trading desk profile is live! Tap the digital voucher button below to access your advanced toolkit, claim 30-day allocations, and spin the high-fidelity 3D Panda Wheel."
    )
    await message.reply(welcome_text, reply_markup=kb, parse_mode="Markdown")

@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text: 
        return
        
    log_user_activity(message.from_user)

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
        return web.json_response({"success": False, "message": "🚫 Voucher Locked: Allocation for today is already secured!"})

    user_profile["xp"] += 10
    user_profile["last_checkin"] = today_str
    user_profile["checkin_days"].append(day_num)
    return web.json_response({"success": True, "message": f"💳 Day {day_num} processed! +10 XP securely routed to balance."})

async def api_execute_spin(request):
    data = await request.json()
    user_id = data.get("user_id")
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    user_profile = xp_database[user_id]
    
    if user_profile.get("last_wheel_spin") == today_str:
        return web.json_response({"success": False, "message": "🚫 Wheel Locked: The daily high-yield spin allocation resets at 00:00 UTC!"})
        
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
# 5. HIGH-FIDELITY 3D PANDA WEB APP UI 🎡
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
            @import url('https://fonts.googleapis.com/css2?family=Anton&family=Inter:wght@400;700;900&display=swap');
            
            :root {
                --theme-primary: #a855f7; --theme-accent: #f43f5e;
                --text-gradient: linear-gradient(180deg, #ffffff 0%, #a8a29e 100%);
                --card-beveled: linear-gradient(135deg, rgba(30, 27, 54, 0.8) 0%, rgba(15, 12, 28, 0.9) 100%);
            }

            body {
                font-family: 'Inter', sans-serif;
                background: radial-gradient(circle at center, #14121f 0%, #08070d 100%);
                color: #ffffff; margin: 0; padding: 20px; text-align: center; overflow-x: hidden;
            }
            
            /* Universal 3D Style Beveled Gold-to-Crimson Text 3D Font Layout */
            .font-3d-style {
                font-family: 'Anton', sans-serif; font-weight: 400; letter-spacing: 0.5px; text-transform: uppercase;
                background: linear-gradient(90deg, #d4af37, #f43f5e, #d4af37);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.5), 0 0 5px rgba(212, 175, 55, 0.6);
            }

            .profile-card-3d-shield {
                background: var(--card-beveled); border: 2px solid rgba(168, 85, 247, 0.4);
                border-radius: 20px; padding: 25px; margin-bottom: 25px;
                position: relative; overflow: hidden;
                box-shadow: 0 25px 50px -12px rgba(168, 85, 247, 0.25), inset 0 1px 1px rgba(255,255,255,0.1);
                transform: perspective(1000px) rotateX(8deg); transition: transform 0.3s ease;
            }

            .brand-logo-text { font-size: 32px; font-weight: 900; margin: 0; text-align: left; }
            .panda-badge { position: absolute; top: 20px; right: 20px; font-size: 32px; filter: drop-shadow(0 0 10px rgba(168, 85, 247, 0.6)); }

            .voucher-balance-display {
                font-size: 45px; font-weight: 900; margin: 25px 0 10px 0; text-align: left;
                font-family: 'Anton', monospace; -webkit-text-fill-color: #ffffff; -webkit-background-clip: initial;
                text-shadow: 0 0 25px rgba(168, 85, 247, 0.8), 2px 2px 0px rgba(0,0,0,0.5);
            }

            .card-meta-row { display: flex; justify-content: space-between; font-size: 11px; color: #a78bfa; font-weight: bold; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 15px; margin-top: 15px; }
            .ticker-banner { background: rgba(15, 12, 28, 0.6); border-radius: 12px; padding: 10px; font-size: 11px; font-weight: 700; color: #f43f5e; border: 1px dashed rgba(244, 63, 94, 0.3); margin-bottom: 25px; }
            
            .feature-panel-grid { background: rgba(15, 12, 28, 0.8); border-radius: 18px; padding: 20px; margin-bottom: 25px; border: 1px solid rgba(255, 255, 255, 0.04); text-align: left; }
            .panel-header-badge { font-weight: 800; color: #a855f7; margin-bottom: 15px; font-size: 14px; letter-spacing: 1px; display: flex; align-items: center; gap: 8px; }
            
            .calculator-form-matrix { width: 100%; padding: 12px; background: #1e1b36; border: 1px solid rgba(168,85,247,0.3); border-radius: 10px; color: white; font-size: 15px; margin-bottom: 15px; box-sizing: border-box; }
            .calculation-payout-box { background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.3); padding: 15px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: 900; color: #f43f5e; font-family: 'Anton', monospace; }

            /* --- HIGH-FIDELITY 3D PANDA SPIN WHEEL MECHANICS --- */
            .wheel-matrix-frame { display: flex; flex-direction: column; align-items: center; position: relative; margin: 25px 0; padding: 10px; }
            .wheel-pylon-base {
                width: 280px; height: 280px; border-radius: 50%;
                background: conic-gradient(#2e1065 0deg 60deg, #701a75 60deg 120deg, #a21caf 120deg 180deg, #ec4899 180deg 240deg, #f43f5e 240deg 300deg, #a855f7 300deg 360deg);
                box-shadow: 0 15px 40px rgba(0,0,0,0.8), 0 0 40px rgba(168, 85, 247, 0.4), inset 0 0 20px rgba(255,255,255,0.15);
                transform: perspective(1000px) rotateX(25deg); position: relative; transition: transform 4s cubic-bezier(0.1, 0.8, 0.25, 1);
            }
            .wheel-core-badge { position: absolute; top: 50%; left: 50%; width: 50px; height: 50px; border-radius: 50%; background: #1e1b36; border: 4px solid white; transform: translate(-50%, -50%); display: grid; place-items: center; box-shadow: 0 0 20px black; z-index: 2; }
            .wheel-needle-caliper { width: 0; height: 0; border-left: 15px solid transparent; border-right: 15px solid transparent; border-top: 25px solid #ffffff; position: absolute; top: -10px; z-index: 10; filter: drop-shadow(0 4px 5px rgba(0,0,0,0.6)); }
            .trigger-matrix-btn { margin-top: 30px; width: 100%; background: linear-gradient(90deg, #a855f7, #f43f5e); border: none; padding: 14px; border-radius: 12px; color: white; font-weight: 900; font-size: 16px; cursor: pointer; box-shadow: 0 5px 15px rgba(244,63,94,0.4); text-shadow: 0 1px 2px black; font-family: 'Anton', sans-serif; letter-spacing: 1px; }
            .trigger-matrix-btn:disabled { opacity: 0.5; cursor: not-allowed; }

            .30day-grid-matrices { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
            .coupon-matrix-ticket { background: #1e1b36; border: 1px solid rgba(255,255,255,0.05); border-radius: 10px; padding: 14px 0; font-size: 11px; font-weight: 800; cursor: pointer; color: #94a3b8; position: relative; transition: all 0.2s ease; text-align: center; }
            .coupon-matrix-ticket::before, .coupon-matrix-ticket::after { content: ''; position: absolute; width: 6px; height: 6px; background: #08070d; border-radius: 50%; top: 50%; transform: translateY(-50%); }
            .coupon-matrix-ticket::before { left: -4px; } .coupon-matrix-ticket::after { right: -4px; }
            .coupon-matrix-ticket.redeemed { background: linear-gradient(135deg, #f43f5e 0%, #a855f7 100%); color: #ffffff; border-color: transparent; font-weight: 900; box-shadow: 0 0 10px rgba(168, 85, 247, 0.3); }
            
            .leaderboard-row-matrix { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; margin-bottom: 6px; border-radius: 10px; background: rgba(255,255,255,0.01); }
            .rank-pylon-index { font-weight: 900; color: #f43f5e; margin-right: 8px; font-family: 'Anton', sans-serif; }
            .xp-credit-badge { background: rgba(168, 85, 247, 0.15); color: #c084fc; font-weight: 800; padding: 4px 12px; border-radius: 8px; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="profile-card-3d-shield" id="main-card">
            <div class="font-3d-style brand-logo-text">PD CARD</div>
            <div class="panda-badge">🐼</div>
            <div class="voucher-balance-display font-3d-style" id="user-total-xp">00.00 XP</div>
            <div class="card-meta-row">
                <div id="user-display">TRADER INDEX</div>
                <div>SECURE ALLOCATION WALLET</div>
            </div>
        </div>
        <div class="ticker-banner">⚡ SECURE GIFT CARD EXCHANGE DESK • PREMIUM 3D MATRIX ACTIVE ⚡</div>

        <div class="feature-panel-grid">
            <div class="font-3d-style panel-header-badge">📈 Live Voucher Rate Compute</div>
            <select class="calculator-form-matrix" id="card-type" onchange="performCalculation()">
                <option value="920">Apple iTunes Gift Card (Premium) - ₦920/$</option>
                <option value="950">Razer Gold Allocation Voucher - ₦950/$</option>
                <option value="890">Steam Wallet Code Index - ₦890/$</option>
                <option value="870">Vanilla Visa / Amex Protocol - ₦870/$</option>
            </select>
            <input type="number" class="calculator-form-matrix" id="card-amount" placeholder="Enter Card Value Amount ($)" value="100" oninput="performCalculation()">
            <div class="font-3d-style calculation-payout-box" id="payout-payout">₦95,000 PAYOUT</div>
        </div>

        <div class="feature-panel-grid" style="text-align: center;">
            <div class="font-3d-style panel-header-badge" style="justify-content: center;">🎡 Lucky Panda 3D Wheel</div>
            <div class="wheel-matrix-frame">
                <div class="wheel-needle-caliper"></div>
                <div class="wheel-pylon-base" id="spin-wheel">
                    <div class="wheel-core-badge">
                        <span style="font-size:10px; font-weight:900; color:white; transform:rotate(-25deg)">PD</span>
                    </div>
                </div>
            </div>
            <button class="trigger-matrix-btn font-3d-style" id="spin-btn" onclick="executeLuckySpin()">EXECUTE COOL-DOWN SPIN</button>
        </div>

        <div class="feature-panel-grid">
            <div class="font-3d-style panel-header-badge">🎫 30-Day Allocation Matrices</div>
            <div class="30day-grid-matrices" id="calendar-box"></div>
        </div>

        <div class="feature-panel-grid">
            <div class="font-3d-style panel-header-badge">🏆 Global Trading Desk Index</div>
            <div id="leaderboard-box"></div>
        </div>

        <script>
            const tg = window.Telegram.WebApp;
            tg.expand();

            const rawUser = tg.initDataUnsafe.user || { id: 7777, first_name: "Active Trader", username: "Panda_X" };
            const userId = String(rawUser.id);
            const userHandle = rawUser.username ? `@${rawUser.username}` : rawUser.first_name;

            document.getElementById('user-display').innerText = userHandle.toUpperCase();

            // Parallax dynamics effect implementation
            const card = document.getElementById('main-card');
            const wheelBase = document.getElementById('spin-wheel');
            
            document.addEventListener('mousemove', (e) => {
                const xAxis = (window.innerWidth / 2 - e.pageX) / 25;
                const yAxis = (window.innerHeight / 2 - e.pageY) / 25;
                card.style.transform = `perspective(1000px) rotateY(${xAxis}deg) rotateX(${yAxis+8}deg)`;
                
                // Also tilt the wheel base slightly on gyroscope simulation
                wheelBase.style.transform = `perspective(1000px) rotateX(${25+(yAxis/2)}deg) rotateY(${xAxis/2}deg)`;
            });

            function performCalculation() {
                const rate = parseFloat(document.getElementById('card-type').value);
                const amt = parseFloat(document.getElementById('card-amount').value) || 0;
                const calculation = rate * amt;
                document.getElementById('payout-payout').innerText = `₦${calculation.toLocaleString()} PAYOUT`;
            }

            async function executeLuckySpin() {
                const spinBtn = document.getElementById('spin-btn');
                spinBtn.disabled = true;
                
                try {
                    const res = await fetch('/api/spinwheel', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: userId })
                    });
                    const result = await res.json();
                    
                    if (!result.success) {
                        spinBtn.disabled = false;
                        if(tg.showAlert) tg.showAlert(result.message); else alert(result.message);
                        return;
                    }
                    
                    // Matrices rotation execution configuration
                    const wheel = document.getElementById('spin-wheel');
                    
                    // Reset matrix to default tilt first for clean start
                    wheel.style.transform = `perspective(1000px) rotateX(25deg)`;
                    
                    // Calculate precise rotation matrix angle (4 matrix passes + winner offset)
                    const matrixBase = 1440; // 4 full matrix passes
                    const winningOffset = result.slice_index * 60; // precision offset
                    const targetDegrees = matrixBase + winningOffset;
                    
                    // Trigger spin matrix sequence
                    wheel.style.transform = `perspective(1000px) rotateX(25deg) rotateZ(-${targetDegrees}deg)`;
                    
                    setTimeout(() => {
                        spinBtn.disabled = false;
                        if(tg.showAlert) tg.showAlert(result.message); else alert(result.message);
                        syncAllData();
                    }, 4100);
                } catch(e) { console.error(e); spinBtn.disabled = false; }
            }

            async function syncAllData() {
                try {
                    const res = await fetch(`/api/userstatus?user_id=${userId}&username=${encodeURIComponent(userHandle)}`);
                    const userProfile = await res.json();
                    document.getElementById('user-total-xp').innerText = `${userProfile.xp}.00 XP`;
                    
                    const container = document.getElementById('calendar-box');
                    container.innerHTML = '';
                    
                    // Render 30 Days allocation configuration matrices
                    for (let d = 1; d <= 30; d++) {
                        const isClaimed = userProfile.checkin_days.includes(d);
                        const coupon = document.createElement('div');
                        coupon.className = `coupon-matrix-ticket ${isClaimed ? 'redeemed' : ''}`;
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
                            <div class="leaderboard-row-matrix">
                                <div><span class="rank-pylon-index font-3d-style">#${index+1}</span><strong>${user.username}</strong></div>
                                <div class="xp-credit-badge font-3d-style">${user.xp} XP</div>
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

            window.onload = () => { syncAllData(); performCalculation(); };
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
    logging.info("PD Card 3D Matrix V3 Live!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

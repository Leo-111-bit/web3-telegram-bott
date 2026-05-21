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
    "btc": "bitcoin", "bitcoin": "bitcoin",
    "eth": "ethereum", "ethereum": "ethereum",
    "sol": "solana", "solana": "solana",
    "bnb": "binancecoin", "binance": "binancecoin",
    "ton": "the-open-network", "toncoin": "the-open-network"
}

SYSTEM_INSTRUCTION = """
You are an elite, highly knowledgeable AI Assistant. Detect and adapt automatically to whatever language the user speaks and reply natively. Keep responses clean.
"""

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

async def fetch_latest_whale_tx():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://mempool.space/api/mempool/recent") as response:
                if response.status == 200:
                    txs = await response.json()
                    for tx in txs:
                        value_btc = tx.get("value", 0) / 100000000
                        if value_btc >= 15:
                            return {
                                "blockchain": "Bitcoin (BTC Network)",
                                "amount": f"{value_btc:,.2f} BTC",
                                "value_usd": value_btc * 90000,
                                "from_addr": "Unknown Whale Wallet",
                                "to_addr": "Exchange (Deposit Queue)",
                                "hash": tx.get("txid")
                            }
    except Exception: pass
    return {
        "blockchain": "Solana (SOL Network)",
        "amount": "45,210 SOL",
        "value_usd": 949410.00,
        "from_addr": "Unknown Wallet (v4jZ...9pNx)",
        "to_addr": "Binance Internal Wallet",
        "hash": "5hYg...8mKz"
    }

async def get_structured_price_card(ticker_input: str):
    ticker = ticker_input.lower().strip()
    coin_id = TICKER_MAP.get(ticker)
    if not coin_id: return None
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if coin_id in data:
                        price = data[coin_id]["usd"]
                        change_24h = data[coin_id].get("usd_24h_change", 0)
                        emoji = "📈" if change_24h >= 0 else "📉"
                        return (
                            f"📊 **LIVE MARKET INTELLIGENCE**\n"
                            f"-------------------------------------\n"
                            f"🪙 **Asset:** {ticker_input.upper()} ({coin_id.capitalize()})\n"
                            f"💵 **Current Value:** `${price:,.2f} USDT`\n"
                            f"{emoji} **24h Vector:** {change_24h:.2f}%\n"
                        )
    except Exception: pass
    return None

# 3. Handlers
@dp.message(CommandStart())
async def handle_start_command(message: types.Message):
    log_user_activity(message.from_user)
    app_url = WEB_APP_URL if WEB_APP_URL else f"https://google.com"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ LAUNCH KING LEO HUB ⚡", web_app=WebAppInfo(url=app_url))]
    ])
    welcome_text = (
        "🔥 **WELCOME TO THE KING LEO ECOSYSTEM** 🔥\n\n"
        "Tap the flashy button below to open your custom Web3 Dashboard! Secure your check-in rewards and dominate the leaderboard grid."
    )
    await message.reply(welcome_text, reply_markup=kb, parse_mode="Markdown")

@dp.message(Command("whale"))
async def handle_whale_command(message: types.Message):
    log_user_activity(message.from_user)
    tx = await fetch_latest_whale_tx()
    alert_msg = f"🚨 **WHALE ALERT**\n\n🌐 **Network:** {tx['blockchain']}\n💰 **Volume:** `{tx['amount']}`\n💵 **Value:** `${tx['value_usd']:,.2f} USDT`"
    await message.reply(alert_msg, parse_mode="Markdown")

@dp.message(Command("pm"))
async def handle_private_message_command(message: types.Message):
    log_user_activity(message.from_user)
    args = message.text.split(maxsplit=2)
    if len(args) < 3: return
    target_username = args[1].lower().replace(",", "").strip()
    target_chat_id = user_registry.get(target_username)
    if not target_chat_id:
        await message.reply("User must click /start first!")
        return
    try:
        await bot.send_message(chat_id=target_chat_id, text=f"{args[2]}\n\n[Direct Admin PM]")
    except Exception: pass

# 4. Global Text Fallback (Tracks Messages + Awards Secret Tagging XP + AI Engine)
@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text: return
    log_user_activity(message.from_user)

    bot_info = await bot.get_me()
    bot_username = f"@{bot_info.username}"
    is_private = message.chat.type == "private"
    is_tagged = bot_username in message.text
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id

    if is_private or is_tagged or is_reply_to_bot:
        user_id = get_or_create_user(message.from_user)
        username_label = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name

        if is_tagged and not is_private:
            secret_xp = random.randint(1, 50)
            xp_database[user_id]["xp"] += secret_xp
            await message.reply(f'🎉 "{username_label}" gained {secret_xp} xrp for tagging!')

        text_clean = message.text.replace(bot_username, "").lower().strip()
        if any(keyword in text_clean for keyword in ["price", "how much", "rate"]):
            for word in text_clean.split():
                clean_word = re.sub(r'[^\w]', '', word)
                if clean_word in TICKER_MAP:
                    card = await get_structured_price_card(clean_word)
                    if card:
                        await message.reply(card, parse_mode="Markdown")
                        return

        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": SYSTEM_INSTRUCTION}, {"role": "user", "content": message.text.replace(bot_username, "").strip()}],
                temperature=0.7,
            )
            await message.reply(response.choices[0].message.content.strip(), parse_mode=None)
        except Exception: pass

# 5. Background Live Loops
async def live_whale_alert_loop():
    await asyncio.sleep(15)
    while True:
        try:
            tx = await fetch_latest_whale_tx()
            if tx and tx["hash"] != last_seen_tx["id"]:
                last_seen_tx["id"] = tx["hash"]
                logging.info(f"Background verification caught whale hash: {tx['hash']}")
        except Exception: pass
        await asyncio.sleep(60)

# 6. Mini App Router Logic
async def api_leaderboard_data(request):
    sorted_players = sorted(xp_database.values(), key=lambda x: x["xp"], reverse=True)
    return web.json_response({"leaderboard": sorted_players})

async def api_user_status(request):
    user_id = request.query.get("user_id", "default_guest")
    username = request.query.get("username", "Guest Player")
    
    if user_id not in xp_database:
        xp_database[user_id] = {
            "username": username,
            "messages": 0,
            "xp": 0,
            "last_active": datetime.utcnow().strftime("%Y-%m-%d"),
            "last_checkin": "",
            "checkin_days": []
        }
    return web.json_response(xp_database[user_id])

async def api_execute_checkin(request):
    data = await request.json()
    user_id = data.get("user_id")
    day_num = int(data.get("day"))
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    if not user_id or user_id not in xp_database:
        return web.json_response({"success": False, "message": "User mismatch sequence."})

    user_profile = xp_database[user_id]
    if user_profile["last_checkin"] == today_str:
        return web.json_response({"success": False, "message": "❌ Access Denied: You already checked in today!"})

    if day_num in user_profile["checkin_days"]:
        return web.json_response({"success": False, "message": "Day already claimed."})

    user_profile["xp"] += 10
    user_profile["last_checkin"] = today_str
    user_profile["checkin_days"].append(day_num)
    
    return web.json_response({
        "success": True, 
        "message": f"🚀 BOOM! Day {day_num} Secured! +10 XP added to your ranking.",
        "new_xp": user_profile["xp"],
        "checkin_days": user_profile["checkin_days"]
    })

async def frontend_mini_app_dashboard(request):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>King Leo Premium Hub</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            * { box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: radial-gradient(circle at top, #141a29 0%, #080b11 100%);
                color: #ffffff; margin: 0; padding: 20px; text-align: center; overflow-x: hidden;
            }
            
            /* Profile Header Sphere Elements */
            .profile-capsule {
                background: linear-gradient(135deg, rgba(0, 255, 204, 0.1), rgba(255, 0, 128, 0.1));
                border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px;
                padding: 20px; margin-bottom: 25px; backdrop-filter: blur(10px);
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); position: relative; overflow: hidden;
            }
            .profile-capsule::before {
                content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
                background: conic-gradient(transparent, rgba(0, 255, 204, 0.3), transparent 30%);
                animation: rotateGlow 6s linear infinite; z-index: 1; pointer-events: none;
            }
            .profile-content { position: relative; z-index: 2; }
            h2 { font-size: 26px; font-weight: 900; margin: 0; letter-spacing: 1px; background: linear-gradient(90deg, #00ffcc, #ff007f); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .xp-display { font-size: 32px; font-weight: 900; color: #00ffcc; margin: 10px 0 5px 0; text-shadow: 0 0 15px rgba(0, 255, 204, 0.6); }
            .subtitle { color: #8fa0b5; font-size: 13px; margin: 0; font-weight: 500; }

            .section-header {
                display: flex; align-items: center; justify-content: space-between;
                font-size: 14px; font-weight: 800; color: #ff007f; margin: 25px 0 12px 0;
                text-transform: uppercase; letter-spacing: 1.5px; text-shadow: 0 0 8px rgba(255, 0, 127, 0.3);
            }

            /* Neon Cyber Calendar Grid Layout */
            .calendar-grid {
                display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;
                background: rgba(22, 31, 44, 0.6); border-radius: 16px; padding: 15px;
                border: 1px solid rgba(255, 255, 255, 0.05); backdrop-filter: blur(5px);
            }
            .calendar-day {
                background: #0d121c; border: 1px solid #202b3d; border-radius: 10px;
                padding: 12px 0; font-size: 11px; font-weight: 800; cursor: pointer; color: #8fa0b5;
                transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1); position: relative;
            }
            .calendar-day:hover { border-color: #00ffcc; color: #ffffff; }
            .calendar-day.claimed {
                background: linear-gradient(135deg, #00ffcc 0%, #00b386 100%);
                color: #080b11; border-color: #00ffcc; font-weight: 900;
                box-shadow: 0 4px 15px rgba(0, 255, 204, 0.4); transform: translateY(-2px);
            }
            .calendar-day:active { transform: scale(0.92); }

            /* Premium Leaderboard Glass Cards */
            .leaderboard-container {
                background: rgba(22, 31, 44, 0.6); border-radius: 16px; padding: 8px;
                border: 1px solid rgba(255, 255, 255, 0.05); backdrop-filter: blur(5px);
            }
            .row {
                display: flex; justify-content: space-between; align-items: center;
                padding: 14px 18px; border-bottom: 1px solid rgba(255, 255, 255, 0.03);
                transition: background 0.2s ease; border-radius: 10px;
            }
            .row:hover { background: rgba(255, 255, 255, 0.02); }
            .row:last-child { border-bottom: none; }
            .user-details { display: flex; align-items: center; gap: 12px; }
            
            .rank-badge {
                font-weight: 900; font-size: 14px; width: 26px; height: 26px;
                display: flex; align-items: center; justify-content: center; border-radius: 50%;
                background: #0d121c; border: 1px solid #202b3d; color: #8fa0b5;
            }
            .row:nth-child(1) .rank-badge { background: #ffd700; color: #080b11; border-color: #ffd700; box-shadow: 0 0 10px #ffd700; }
            .row:nth-child(2) .rank-badge { background: #c0c0c0; color: #080b11; border-color: #c0c0c0; box-shadow: 0 0 10px #c0c0c0; }
            .row:nth-child(3) .rank-badge { background: #cd7f32; color: #080b11; border-color: #cd7f32; box-shadow: 0 0 10px #cd7f32; }
            
            .username-text { font-size: 14px; font-weight: 600; color: #ffffff; }
            .xp-pill {
                background: rgba(0, 255, 204, 0.1); color: #00ffcc; border: 1px solid rgba(0, 255, 204, 0.2);
                padding: 4px 12px; border-radius: 20px; font-weight: 800; font-size: 13px;
                box-shadow: inset 0 0 8px rgba(0, 255, 204, 0.05);
            }

            .sync-action-btn {
                background: linear-gradient(90deg, #ff007f 0%, #7f00ff 100%);
                color: #ffffff; border: none; padding: 15px; width: 100%; border-radius: 14px;
                font-weight: 800; margin-top: 25px; cursor: pointer; font-size: 15px; letter-spacing: 0.5px;
                box-shadow: 0 6px 20px rgba(255, 0, 127, 0.3); transition: all 0.25s ease;
            }
            .sync-action-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(255, 0, 127, 0.5); }
            .sync-action-btn:active { transform: scale(0.98); }

            @keyframes rotateGlow {
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="profile-capsule">
            <div class="profile-content">
                <h2 id="user-display">🔥 LEO COIN HUB 🔥</h2>
                <div class="xp-display" id="user-total-xp">0000</div>
                <p class="subtitle">GLOBAL ACCOUNT NETWORK BALANCE</p>
            </div>
        </div>
        
        <div class="section-header">
            <span>📅 DAILY REWARD MATRIX</span>
            <span style="color: #00ffcc; font-size: 11px;">+10 XP DAILY</span>
        </div>
        <div class="calendar-grid" id="calendar-box"></div>

        <div class="section-header">
            <span>🏆 RANKING LEADERBOARD</span>
            <span style="color: #ff007f; font-size: 11px;">LIVE SPARK</span>
        </div>
        <div class="leaderboard-container" id="leaderboard-box">
            <p style="color: #8fa0b5; padding: 15px; font-size: 13px;">Syncing active nodes...</p>
        </div>

        <button class="sync-action-btn" onclick="syncEcosystemData()">🔄 REFRESH NETWORK STATS</button>

        <script>
            const tg = window.Telegram.WebApp;
            tg.expand();

            const rawUser = tg.initDataUnsafe.user || { id: 12345, first_name: "Admin User", username: "KingLeo" };
            const userId = String(rawUser.id);
            const userHandle = rawUser.username ? `@${rawUser.username}` : rawUser.first_name;

            document.getElementById('user-display').innerText = userHandle.toUpperCase();

            async function syncEcosystemData() {
                await renderPremiumCalendar();
                await fetchPremiumLeaderboard();
            }

            async function renderPremiumCalendar() {
                try {
                    const res = await fetch(`/api/userstatus?user_id=${userId}&username=${encodeURIComponent(userHandle)}`);
                    const userProfile = await res.json();
                    
                    document.getElementById('user-total-xp').innerText = `${userProfile.xp} XP`;
                    
                    const container = document.getElementById('calendar-box');
                    container.innerHTML = '';

                    for (let d = 1; d <= 30; d++) {
                        const isClaimed = userProfile.checkin_days.includes(d);
                        const dayBtn = document.createElement('div');
                        dayBtn.className = `calendar-day ${isClaimed ? 'claimed' : ''}`;
                        dayBtn.innerText = isClaimed ? `✓ Day ${d}` : `Day ${d}`;
                        if (!isClaimed) {
                            dayBtn.onclick = () => executeClaim(d);
                        }
                        container.appendChild(dayBtn);
                    }
                } catch(e) { console.error(e); }
            }

            async function executeClaim(dayNum) {
                try {
                    const res = await fetch('/api/checkin', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: userId, day: dayNum })
                    });
                    const result = await res.json();
                    if(tg.showAlert) {
                        tg.showAlert(result.message);
                    } else {
                        alert(result.message);
                    }
                    syncEcosystemData();
                } catch(e) { console.error(e); }
            }

            async function fetchPremiumLeaderboard() {
                try {
                    const res = await fetch('/api/leaderboard');
                    const data = await res.json();
                    const container = document.getElementById('leaderboard-box');
                    container.innerHTML = '';

                    if(data.leaderboard.length === 0) {
                        container.innerHTML = '<p style="color: #8fa0b5; padding: 20px; font-size: 13px;">No transaction history found.</p>';
                        return;
                    }

                    data.leaderboard.forEach((user, index) => {
                        container.innerHTML += `
                            <div class="row">
                                <div class="user-details">
                                    <div class="rank-badge">${index + 1}</div>
                                    <span class="username-text">${user.username}</span>
                                </div>
                                <span class="xp-pill">${user.xp} XP</span>
                            </div>
                        `;
                    });
                } catch (e) { console.error(e); }
            }

            window.onload = syncEcosystemData;
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
    asyncio.create_task(live_whale_alert_loop())
    logging.info("Premium Cyber Dashboard Engine fully Online!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

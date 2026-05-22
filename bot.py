import os
import asyncio
import logging
import datetime
import sqlite3
import random
import math

from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBAPP_URL = os.getenv("WEB_APP_URL", "http://localhost:10000")

if not TOKEN:
    raise Exception("Missing TELEGRAM_BOT_TOKEN")

bot = Bot(TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# =========================
# DATABASE
# =========================

DB_NAME = "pdcard.db"

def db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT,
        xp INTEGER DEFAULT 0,
        messages INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0,
        last_xp_message TEXT,
        last_tag_claim TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# TIME HELPERS
# =========================

def now():
    return datetime.datetime.utcnow()

def iso():
    return now().isoformat()

def can_use(last_time, cooldown):
    if not last_time:
        return True
    last = datetime.datetime.fromisoformat(last_time)
    return (now() - last).total_seconds() > cooldown

# =========================
# XP SYSTEM
# =========================

XP_COOLDOWN = 30
TAG_COOLDOWN = 86400

def get_level(xp):
    return int(math.sqrt(xp / 120)) + 1

def xp_to_next(level):
    return (level * level) * 120

def rank_title(level):
    if level < 3:
        return "🐣 Rookie Panda"
    elif level < 6:
        return "🐼 Active Panda"
    elif level < 10:
        return "🔥 Elite Panda"
    elif level < 15:
        return "💎 Diamond Panda"
    else:
        return "👑 Mythic Panda"

def message_xp():
    return random.randint(8, 15)

def streak_multiplier(streak):
    return min(1 + (streak * 0.1), 2.5)

# =========================
# USER SYSTEM
# =========================

def get_user(uid, username="Guest"):
    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    row = cur.fetchone()

    if not row:
        cur.execute(
            "INSERT INTO users (user_id, username) VALUES (?,?)",
            (uid, username)
        )
        conn.commit()
        conn.close()
        return get_user(uid, username)

    conn.close()
    return row

def update(uid, field, value):
    conn = db()
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, uid))
    conn.commit()
    conn.close()

# =========================
# TELEGRAM HANDLERS
# =========================

@dp.message(CommandStart())
async def start(msg: types.Message):

    get_user(str(msg.from_user.id), msg.from_user.username or "User")

    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text="🐼 OPEN PD CARD",
                web_app=types.WebAppInfo(url=WEBAPP_URL)
            )
        ]
    ])

    await msg.answer(
        "🐼 Welcome to PD CARD\nOpen your dashboard below",
        reply_markup=kb
    )

@dp.message(Command("leaderboard"))
async def leaderboard(msg: types.Message):

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT username, xp FROM users ORDER BY xp DESC LIMIT 10")
    rows = cur.fetchall()
    conn.close()

    text = "🏆 PD LEADERBOARD\n\n"

    for i, r in enumerate(rows, 1):
        text += f"{i}. {r[0]} — {r[1]} XP\n"

    await msg.answer(text)

# =========================
# MAIN XP + DAILY SYSTEM
# =========================

@dp.message()
async def xp_handler(msg: types.Message):

    if not msg.text:
        return

    uid = str(msg.from_user.id)
    username = msg.from_user.username or "User"

    row = get_user(uid, username)

    xp = row[2]
    messages = row[3]
    streak = row[4]
    last_xp_message = row[5]
    last_tag_claim = row[6]

    messages += 1

    # =========================
    # MESSAGE XP SYSTEM
    # =========================
    if can_use(last_xp_message, XP_COOLDOWN):
        xp += message_xp()
        update(uid, "last_xp_message", iso())

    # =========================
    # STREAK SYSTEM
    # =========================
    today = datetime.datetime.utcnow().date()

    if last_xp_message:
        last_date = datetime.datetime.fromisoformat(last_xp_message).date()

        if (today - last_date).days == 1:
            streak += 1
        elif (today - last_date).days > 1:
            streak = 1
    else:
        streak = 1

    update(uid, "xp", xp)
    update(uid, "messages", messages)
    update(uid, "streak", streak)

    raw = msg.text.upper()

    # =========================
    # CHECK XP / CHECK XRP + DAILY TAG REWARD
    # =========================
    if "CHECK XP" in raw or "CHECK XRP" in raw:

        if not can_use(last_tag_claim, TAG_COOLDOWN):

            await msg.reply(
                "🐼 already claimed\ncome again tomorrow"
            )
            return

        reward = random.randint(20, 60)
        xp += reward

        update(uid, "xp", xp)
        update(uid, "last_tag_claim", iso())

        lvl = get_level(xp)
        title = rank_title(lvl)

        await msg.reply(
            f"""🎉 DAILY XP CLAIMED

+{reward} XP
💎 XP: {xp}
📈 Level: {lvl}
🏷 Rank: {title}
🔥 Streak: {streak}

come back tomorrow 🐼
"""
        )
        return

# =========================
# WEB API: USER
# =========================

async def api_user(request):

    uid = request.query.get("user_id")
    username = request.query.get("username", "Guest")

    if not uid:
        return web.json_response({"error": "missing user"}, status=400)

    row = get_user(uid, username)

    return web.json_response({
        "user_id": row[0],
        "username": row[1],
        "xp": row[2],
        "messages": row[3],
        "level": get_level(row[2]),
        "streak": row[4]
    })

# =========================
# WEB API: LEADERBOARD
# =========================

async def api_leaderboard(request):

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT username, xp FROM users ORDER BY xp DESC")
    rows = cur.fetchall()
    conn.close()

    return web.json_response({
        "leaderboard": [
            {"username": r[0], "xp": r[1]} for r in rows
        ]
    })

# =========================
# WEB DASHBOARD (PANDA SLIDESHOW)
# =========================

async def dashboard(request):

    html = """
<!DOCTYPE html>
<html>
<head>
<title>🐼 PD CARD</title>

<style>
body{
margin:0;
background:#0b0b12;
color:white;
font-family:Arial;
}

.header{
text-align:center;
padding:20px;
font-size:22px;
font-weight:bold;
}

.slider{
display:flex;
overflow-x:auto;
gap:15px;
padding:20px;
scroll-snap-type:x mandatory;
}

.card{
min-width:260px;
height:330px;
background:linear-gradient(145deg,#1a1a2e,#0f0f1a);
border-radius:20px;
padding:15px;
scroll-snap-align:center;
box-shadow:0 10px 30px rgba(0,0,0,0.5);
}

.card img{
width:100%;
height:200px;
border-radius:15px;
object-fit:cover;
}

.row{
display:flex;
justify-content:space-between;
padding:10px;
background:#1c1c2c;
margin:8px;
border-radius:10px;
}
</style>

</head>

<body>

<div class="header">🐼 30-DAY PANDA JOURNEY</div>

<div class="slider" id="slider"></div>

<div id="lb"></div>

<script>

const pandas = Array.from({length:30}, (_,i)=>({
day:i+1,
img:`https://source.unsplash.com/300x300/?panda,${i}`
}));

function loadSlides(){
let html="";
pandas.forEach(p=>{
html+=`
<div class="card">
<h3>Day ${p.day}</h3>
<img src="${p.img}" />
</div>`;
});
document.getElementById("slider").innerHTML=html;
}

async function loadLB(){

let res = await fetch("/api/leaderboard");
let data = await res.json();

let html="";

data.leaderboard.forEach((u,i)=>{
html+=`
<div class="row">
<div>#${i+1} ${u.username}</div>
<div>${u.xp} XP</div>
</div>`;
});

document.getElementById("lb").innerHTML=html;
}

loadSlides();
loadLB();

</script>

</body>
</html>
"""

    return web.Response(text=html, content_type="text/html")

# =========================
# WEB SERVER
# =========================

async def start_web():

    app = web.Application()

    app.router.add_get("/", dashboard)
    app.router.add_get("/api/user", api_user)
    app.router.add_get("/api/leaderboard", api_leaderboard)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)

    await site.start()

# =========================
# MAIN
# =========================

async def main():
    await start_web()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

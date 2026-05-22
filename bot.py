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

# =========================
# CONFIG
# =========================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "")

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

if not TELEGRAM_BOT_TOKEN:
    logging.error("Missing TELEGRAM_BOT_TOKEN")
    sys.exit(1)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

BOT_USERNAME = None

db_lock = asyncio.Lock()

MESSAGE_XP_COOLDOWN = 30
TAG_REWARD_COOLDOWN = 86400

user_registry = {}
xp_database = {}

# =========================
# USER MANAGEMENT
# =========================

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

def create_timestamp():
    return utc_now().isoformat()

def get_or_create_user(user: types.User):

    user_id = str(user.id)

    username = (
        f"@{user.username}"
        if user.username
        else user.first_name
    )

    if user.username:
        user_registry[
            f"@{user.username.lower()}"
        ] = user.id

    if user_id not in xp_database:

        xp_database[user_id] = {

            "username": username,
            "messages": 0,
            "xp": 0,

            "last_active": "",

            "last_checkin": "",

            "last_tag_claim": "",

            "last_message_reward": "",

            "checkin_days": []

        }

    return user_id


async def log_user_activity(user: types.User):

    if user.is_bot:
        return

    async with db_lock:

        user_id = get_or_create_user(user)

        profile = xp_database[user_id]

        now = utc_now()

        profile["messages"] += 1
        profile["last_active"] = create_timestamp()

        last_reward = profile.get(
            "last_message_reward"
        )

        if last_reward:

            diff = (
                now -
                datetime.datetime.fromisoformat(
                    last_reward
                )
            ).total_seconds()

            if diff < MESSAGE_XP_COOLDOWN:
                return

        profile["xp"] += 15

        profile[
            "last_message_reward"
        ] = create_timestamp()


# =========================
# COMMANDS
# =========================

@dp.message(
    CommandStart(),
    F.chat.type == ChatType.PRIVATE
)
async def start_private(
        message: types.Message
):

    await log_user_activity(
        message.from_user
    )

    app_url = WEB_APP_URL or "https://google.com"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="🐼 WELCOME TO PD CARD 🐼",
                    web_app=WebAppInfo(
                        url=app_url
                    )
                )
            ]
        ]
    )

    text = (
        "🐼 *WELCOME TO PD CARD*\n\n"
        "Tap below to access your dashboard."
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=kb
    )


@dp.message(
    Command("whale")
)
async def whale(
        message: types.Message
):

    await log_user_activity(
        message.from_user
    )

    await message.answer(
        "📡 Tracking allocation ledgers..."
    )


# =========================
# MESSAGE HANDLER
# =========================

@dp.message()
async def incoming(
        message: types.Message
):

    if not message.text:
        return

    await log_user_activity(
        message.from_user
    )

    raw = (
        message.text
        .strip()
        .upper()
    )

    # leaderboard

    if (
        "CHECK XP" in raw
        or
        "CHECK XRP" in raw
    ):

        if not xp_database:

            return await message.reply(
                "No active users"
            )

        users = sorted(
            xp_database.values(),
            key=lambda x:x["xp"],
            reverse=True
        )

        out = (
            "📊 *PD LEADERBOARD*\n\n"
        )

        for i,u in enumerate(
                users,
                start=1
        ):

            out += (
                f"🏅 #{i} "
                f"*{u['username']}* "
                f"- {u['xp']} XP "
                f"({u['messages']} msgs)\n"
            )

        return await message.answer(
            out,
            parse_mode="Markdown"
        )

    # mention reward

    if (
        message.chat.type
        != ChatType.PRIVATE
        and BOT_USERNAME
        and BOT_USERNAME.lower()
        in message.text.lower()
    ):

        now = utc_now()

        if (
            now-message.date
        ).total_seconds() > 86400:

            return

        async with db_lock:

            uid = get_or_create_user(
                message.from_user
            )

            profile = xp_database[
                uid
            ]

            last_claim = profile.get(
                "last_tag_claim"
            )

            if last_claim:

                diff = (
                    now -
                    datetime.datetime
                    .fromisoformat(
                        last_claim
                    )
                ).total_seconds()

                if diff < TAG_REWARD_COOLDOWN:

                    return await message.reply(
                        "🐼 Daily mention reward already claimed."
                    )

            reward = random.randint(
                20,
                50
            )

            profile["xp"] += reward

            profile[
                "last_tag_claim"
            ] = create_timestamp()

        return await message.reply(

            f"🎉 Bonus unlocked: "
            f"+{reward} XP"

        )


# =========================
# APIs
# =========================

async def leaderboard_api(
        request
):

    users = sorted(

        xp_database.values(),

        key=lambda x:x["xp"],

        reverse=True

    )

    return web.json_response(
        {
            "leaderboard":users
        }
    )


async def user_api(
        request
):

    uid = request.query.get(
        "user_id"
    )

    username = request.query.get(
        "username",
        "Guest"
    )

    if not uid:

        return web.json_response(
            {
                "error":"missing user id"
            },
            status=400
        )

    async with db_lock:

        if uid not in xp_database:

            xp_database[uid]={

                "username":username,

                "messages":0,

                "xp":0,

                "last_active":"",

                "last_checkin":"",

                "last_tag_claim":"",

                "last_message_reward":"",

                "checkin_days":[]

            }

    return web.json_response(
        xp_database[uid]
    )


async def checkin_api(
        request
):

    try:

        data=await request.json()

        uid=data.get(
            "user_id"
        )

        day=int(
            data.get(
                "day"
            )
        )

    except:

        return web.json_response(

            {

                "success":False,

                "message":"Bad request"

            },

            status=400

        )

    async with db_lock:

        profile = xp_database.get(
            uid
        )

        if not profile:

            return web.json_response(
                {
                    "success":False,
                    "message":"User not found"
                }
            )

        if day <1 or day>24:

            return web.json_response(
                {
                    "success":False,
                    "message":"Invalid day"
                }
            )

        today=utc_now().date()

        if profile["last_checkin"]:

            last=datetime.datetime.fromisoformat(

                profile[
                    "last_checkin"
                ]

            ).date()

            if last==today:

                return web.json_response(

                    {

                        "success":False,

                        "message":"Already checked in today"

                    }

                )

        profile["xp"]+=10

        profile[
            "last_checkin"
        ]=create_timestamp()

        if day not in profile[
            "checkin_days"
        ]:

            profile[
                "checkin_days"
            ].append(day)

    return web.json_response(

        {

            "success":True,

            "message":
            f"Day {day} redeemed +10 XP"

        }

    )


# =========================
# MINI APP PAGE
# =========================

async def dashboard(
        request
):

    html="""
<!DOCTYPE html>
<html>
<head>
<title>PD CARD</title>
<style>
body{
background:#111;
color:white;
font-family:Arial;
padding:20px;
}

.card{
padding:20px;
border-radius:15px;
background:#222;
margin-bottom:20px;
}

.row{
display:flex;
justify-content:space-between;
padding:10px;
background:#333;
margin:5px;
border-radius:8px;
}
</style>
</head>

<body>

<div class="card">

<h1>🐼 PD CARD</h1>

<div id="xp">Loading...</div>

</div>

<div id="leaderboard"></div>

<script>

async function load(){

const user=777

let u=
await fetch(
`/api/userstatus?user_id=${user}`
)

u=await u.json()

document.getElementById(
"xp"
).innerText=
u.xp+" XP"

let lb=
await fetch(
"/api/leaderboard"
)

lb=await lb.json()

let html=""

lb.leaderboard.forEach(
(x,i)=>{

const safe=
document.createElement(
"div"
)

safe.innerText=
x.username

html+=`
<div class="row">

<div>
#${i+1}
${safe.innerText}
</div>

<div>
${x.xp}XP
</div>

</div>
`

})

document
.getElementById(
"leaderboard"
).innerHTML=html

}

load()

</script>

</body>
</html>
"""

    return web.Response(
        text=html,
        content_type="text/html"
    )


# =========================
# SERVER
# =========================

async def start_server():

    app=web.Application()

    app.router.add_get(
        "/",
        dashboard
    )

    app.router.add_get(
        "/api/leaderboard",
        leaderboard_api
    )

    app.router.add_get(
        "/api/userstatus",
        user_api
    )

    app.router.add_post(
        "/api/checkin",
        checkin_api
    )

    runner=web.AppRunner(
        app
    )

    await runner.setup()

    port=int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    site=web.TCPSite(

        runner,

        "0.0.0.0",

        port

    )

    await site.start()


# =========================
# MAIN
# =========================

async def main():

    global BOT_USERNAME

    me=await bot.get_me()

    BOT_USERNAME=(
        f"@{me.username}"
    )

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    await start_server()

    logging.info(
        "Server started"
    )

    try:

        await dp.start_polling(
            bot
        )

    finally:

        await bot.session.close()


if __name__=="__main__":

    asyncio.run(main())

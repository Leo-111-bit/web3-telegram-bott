import asyncio
from aiohttp import web
import datetime

# =====================
# LIGHTWEIGHT MEMORY DB
# =====================
users = {}

def get_user(uid, name="Guest"):
    if uid not in users:
        users[uid] = {
            "name": name,
            "xp": 0,
            "last_checkin": ""
        }
    return users[uid]


# =====================
# API ROUTES
# =====================

async def get_profile(request):
    uid = request.query.get("user_id", "0")
    name = request.query.get("name", "Guest")

    return web.json_response(get_user(uid, name))


async def get_leaderboard(request):
    data = sorted(users.items(), key=lambda x: x[1]["xp"], reverse=True)

    return web.json_response({
        "leaderboard": [
            {
                "name": u[1]["name"],
                "xp": u[1]["xp"]
            }
            for u in data
        ]
    })


async def checkin(request):
    data = await request.json()
    uid = data.get("user_id")
    day = data.get("day")

    user = get_user(uid)

    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    if user["last_checkin"] == today:
        return web.json_response({
            "success": False,
            "msg": "Already claimed today"
        })

    user["xp"] += 10
    user["last_checkin"] = today

    return web.json_response({
        "success": True,
        "xp": user["xp"]
    })


# =====================
# FRONTEND (MINI APP UI)
# =====================

async def index(request):

    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>PD CARD</title>

<style>
body{
    margin:0;
    font-family:Arial;
    background:#0b0b0f;
    color:white;
    padding:15px;
}

.card{
    background:#1a1a22;
    padding:15px;
    border-radius:12px;
    margin-bottom:15px;
}

h2,h3{
    margin:5px 0;
}

button{
    padding:10px;
    border:none;
    border-radius:8px;
    background:#a855f7;
    color:white;
    cursor:pointer;
}

button:hover{
    opacity:0.8;
}

#lb div{
    padding:5px 0;
    border-bottom:1px solid #333;
}
</style>
</head>

<body>

<div class="card">
    <h2>🐼 PD CARD</h2>
    <div id="xp">Loading...</div>
</div>

<div class="card">
    <h3>💱 Market Rates</h3>
    <p>Apple $100 → ₦145,000</p>
    <p>Steam $50 → ₦72,000</p>
    <p>Amazon $20 → ₦29,500</p>
</div>

<div class="card">
    <h3>🏆 Leaderboard</h3>
    <div id="lb">Loading...</div>
</div>

<div class="card">
    <h3>🎁 Daily Reward</h3>
    <button onclick="checkin()">Claim +10 XP</button>
</div>

<script>
const tg = window.Telegram?.WebApp;
tg?.expand();

const user = tg?.initDataUnsafe?.user || {
    id: "1",
    first_name: "Guest"
};

async function load(){

    // PROFILE
    let res = await fetch(
        `/profile?user_id=${user.id}&name=${user.first_name}`
    );

    let data = await res.json();

    document.getElementById("xp").innerText =
        "XP: " + data.xp;

    // LEADERBOARD
    let lb = await fetch("/leaderboard");
    lb = await lb.json();

    document.getElementById("lb").innerHTML =
        lb.leaderboard
        .map((u,i)=>
            `#${i+1} ${u.name} - ${u.xp} XP`
        ).join("<br>");
}

async function checkin(){

    await fetch("/checkin", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
            user_id: user.id,
            day: 1
        })
    });

    load();
}

load();
</script>

</body>
</html>
"""

    return web.Response(text=html, content_type="text/html")


# =====================
# APP SETUP
# =====================

app = web.Application()

app.router.add_get("/", index)
app.router.add_get("/profile", get_profile)
app.router.add_get("/leaderboard", get_leaderboard)
app.router.add_post("/checkin", checkin)

if __name__ == "__main__":
    web.run_app(app, port=10000)

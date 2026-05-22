import asyncio
import datetime
import random
from aiohttp import web

# =========================
# MEMORY DATABASE
# =========================
users = {}

BOT_USERNAME = "@PD_CARD"

MESSAGE_COOLDOWN = 20  # anti spam
TAG_COOLDOWN = 86400   # 24h

# =========================
# USER INIT
# =========================
def get_user(uid, name="Guest"):
    if uid not in users:
        users[uid] = {
            "name": name,
            "xp": 0,
            "last_msg": None,
            "last_tag": ""
        }
    return users[uid]

# =========================
# API: PROFILE
# =========================
async def profile(request):
    uid = request.query.get("user_id")
    name = request.query.get("name", "Guest")
    return web.json_response(get_user(uid, name))

# =========================
# API: LEADERBOARD
# =========================
async def leaderboard(request):
    data = sorted(users.items(), key=lambda x: x[1]["xp"], reverse=True)

    return web.json_response({
        "data": [
            {"name": v["name"], "xp": v["xp"]}
            for _, v in data
        ]
    })

# =========================
# API: CHECK XP (SIMPLIFIED BOT COMMAND STYLE)
# =========================
async def check_xp(request):
    data = sorted(users.values(), key=lambda x: x["xp"], reverse=True)

    msg = []
    for i, u in enumerate(data, 1):
        msg.append(f"{i}. {u['name']} - {u['xp']} XP")

    return web.json_response({"msg": "\n".join(msg)})

# =========================
# API: GROUP MESSAGE XP + TAG SYSTEM
# =========================
async def event(request):
    data = await request.json()

    uid = data["user_id"]
    name = data.get("name", "User")
    text = data.get("text", "").upper()
    is_group = data.get("group", True)

    user = get_user(uid, name)
    now = datetime.datetime.utcnow()

    # =========================
    # 1. GROUP MESSAGE XP
    # =========================
    if is_group:
        if user["last_msg"]:
            diff = (now - user["last_msg"]).total_seconds()
            if diff < MESSAGE_COOLDOWN:
                pass
            else:
                user["xp"] += 5
                user["last_msg"] = now
        else:
            user["xp"] += 5
            user["last_msg"] = now

    # =========================
    # 2. BOT TAG REWARD
    # =========================
    if BOT_USERNAME in text:

        today = now.strftime("%Y-%m-%d")

        if user["last_tag"] == today:
            return web.json_response({
                "msg": "🐼 Reward already claimed today"
            })

        reward = random.randint(20, 50)
        user["xp"] += reward
        user["last_tag"] = today

        return web.json_response({
            "msg": f"🎉 +{reward} XP Panda Bonus!"
        })

    return web.json_response({"ok": True})

# =========================
# FRONTEND MINI APP
# =========================
async def index(request):

    html = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>PD CARD</title>

<style>
body{
margin:0;
font-family:Arial;
background: radial-gradient(circle,#0f0f1a,#050509);
color:white;
}

/* ===== GLASS UI ===== */
.card{
background: rgba(255,255,255,0.05);
backdrop-filter: blur(12px);
border:1px solid rgba(255,255,255,0.08);
border-radius:16px;
padding:15px;
margin:10px;
box-shadow:0 10px 30px rgba(0,0,0,0.5);
}

/* ===== XP ===== */
#xp{
font-size:22px;
font-weight:800;
color:#a855f7;
text-shadow:0 0 10px #a855f7;
}

/* ===== NAV ===== */
.nav{
position:fixed;
bottom:0;
width:100%;
display:flex;
background:#0a0a10;
border-top:1px solid #222;
}

.nav button{
flex:1;
padding:12px;
background:none;
border:none;
color:white;
}

/* ===== PAGE ===== */
.page{display:none;padding:10px;}
.active{display:block;}

/* ===== USER LIST ===== */
.user{
padding:10px;
border-bottom:1px solid #222;
animation:fade .3s ease;
}

@keyframes fade{
from{opacity:0;transform:translateY(10px)}
to{opacity:1;transform:translateY(0)}
}

/* ===== SLIDER ===== */
#slide{
height:220px;
border-radius:12px;
background:url('/panda-pack.png');
background-size:300% 1000%;
transition:0.6s ease;
}
</style>
</head>

<body>

<!-- HOME -->
<div id="home" class="page active">

<div class="card">
<h2>🐼 PD CARD</h2>
<div id="xp">XP: 0</div>
</div>

<div class="card">
<h3>🎁 30-Day Panda Rewards</h3>
<div id="slide"></div>
<div id="text"></div>
</div>

</div>

<!-- TASKS -->
<div id="tasks" class="page">
<div class="card">
<h3>📌 Tasks</h3>
<p>Send Messages +5 XP</p>
<p>Daily Check-in +20 XP</p>
<p>Tag PD CARD +30 XP</p>
</div>
</div>

<!-- USERS -->
<div id="users" class="page">
<div class="card">
<h3>🏆 Leaderboard</h3>
<div id="lb"></div>
</div>
</div>

<!-- NAV -->
<div class="nav">
<button onclick="show('home')">Home</button>
<button onclick="show('tasks')">Tasks</button>
<button onclick="show('users')">Users</button>
</div>

<script>
const user = {id:"1",name:"Guest"};

function show(p){
document.querySelectorAll('.page')
.forEach(x=>x.classList.remove('active'));
document.getElementById(p).classList.add('active');
}

/* ===== LOAD DATA ===== */
async function load(){

let p = await fetch(`/profile?user_id=${user.id}&name=${user.name}`);
p = await p.json();
xp.innerText = "XP: " + p.xp;

/* leaderboard */
let l = await fetch("/leaderboard");
l = await l.json();

lb.innerHTML = l.data.map((u,i)=>
`<div class="user">#${i+1} ${u.name} - ${u.xp}</div>`
).join("")
}

setInterval(load,3000);

/* ===== 30 DAY PANDA SLIDES ===== */
const slides = Array.from({length:30},(_,i)=>({
x:(i%6)*20,
y:Math.floor(i/6)*25,
text:`Day ${i+1} +${10+i} XP`
}));

let i=0;

function run(){
let s = slides[i];
slide.style.backgroundPosition = `${s.x}% ${s.y}%`;
text.innerText = s.text;
i=(i+1)%slides.length;
}

setInterval(run,2500);
setInterval(load,3000);

run();load();
</script>

</body>
</html>
"""

    return web.Response(text=html, content_type="text/html")

# =========================
# APP SETUP
# =========================
app = web.Application()

app.router.add_get("/", index)
app.router.add_get("/profile", profile)
app.router.add_get("/leaderboard", leaderboard)
app.router.add_post("/event", event)
app.router.add_get("/checkxp", check_xp)

if __name__ == "__main__":
    web.run_app(app, port=10000)

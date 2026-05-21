import os
import sys
import logging
import asyncio
import aiohttp
import re
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from groq import Groq

# 1. Environment Config Validation
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

if not TELEGRAM_BOT_TOKEN or not GROQ_API_KEY:
    logging.error("CRITICAL: Missing TELEGRAM_BOT_TOKEN or GROQ_API_KEY.")
    sys.exit(1)

# 2. Initialization
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

# Dynamic database map to match usernames to user numeric IDs
user_registry = {}

TICKER_MAP = {
    "btc": "bitcoin", "bitcoin": "bitcoin",
    "eth": "ethereum", "ethereum": "ethereum",
    "sol": "solana", "solana": "solana",
    "bnb": "binancecoin", "binance": "binancecoin",
    "ton": "the-open-network", "toncoin": "the-open-network",
    "trx": "tron", "matic": "polygon",
    "arb": "arbitrum", "op": "optimism"
}

SYSTEM_INSTRUCTION = """
You are an elite, highly knowledgeable AI Assistant. 
You can answer questions about any topic in the world, handle general knowledge, or engage in friendly, non-explicit banter.

Rules:
1. Detect and adapt automatically to whatever language the user speaks (English, Pidgin, Yoruba, etc.) and reply natively.
2. NEVER mention or print any warning phrases about seed phrases or private keys unless explicitly asked about security. Keep responses clean.
"""

# Helper function to generate automated structured response
async def get_structured_price_card(ticker_input: str):
    ticker = ticker_input.lower().strip()
    coin_id = TICKER_MAP.get(ticker)
    
    if not coin_id:
        return None

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
                        
                        card = (
                            f"📊 **LIVE MARKET INTELLIGENCE**\n"
                            f"-------------------------------------\n"
                            f"🪙 **Asset:** {ticker_input.upper()} ({coin_id.capitalize()})\n"
                            f"💵 **Current Value:** `${price:,.2f} USDT`\n"
                            f"{emoji} **24h Vector:** {change_24h:.2f}%\n"
                            f"-------------------------------------\n"
                            f"🧮 **Automated Base Math (USDT Value):**\n"
                            f"• 1 {ticker_input.upper()} = {price:,.2f} USDT\n"
                            f"• 0.1 {ticker_input.upper()} = {(price * 0.1):,.2f} USDT\n"
                            f"• 0.01 {ticker_input.upper()} = {(price * 0.01):,.2f} USDT\n"
                            f"-------------------------------------\n"
                            f"🌐 **Data Reference:** CoinGecko Public Index\n"
                            f"-------------------------------------\n"
                        )
                        return card
    except Exception as e:
        logging.error(f"Structured automatic checker error: {e}")
    return None


# 3. Web3 Feature Command Handlers

@dp.message(Command("pm"))
async def handle_private_message_command(message: types.Message):
    """Usage: /pm @username Your secret message here"""
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply("Usage format: `/pm @username Your message text`")
        return

    # Strip out punctuation like commas from the username arg
    target_username = args[1].lower().replace(",", "").strip()
    text_to_send = args[2]

    target_chat_id = user_registry.get(target_username)

    if not target_chat_id:
        await message.reply(
            f"Cannot send message to {args[1]}.\n\n"
            f"The user must open a private chat and click /start with me first so I can capture their ID!"
        )
        return

    try:
        await bot.send_message(chat_id=target_chat_id, text=f"{text_to_send}\n\n[Direct Admin PM]")
        await message.reply(f"Successfully sent private message to {args[1]}!")
    except Exception as e:
        logging.error(f"Failed to send DM: {e}")
        await message.reply("Failed to DM user. They might have blocked the bot or cleared the chat history.")

@dp.message(Command("p"))
async def handle_price_command(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Please specify a crypto ticker! Example: `/p sol`")
        return
    
    card = await get_structured_price_card(args[1])
    if card:
        await message.reply(card, parse_mode="Markdown")
    else:
        await message.reply(f"Ticker '{args[1]}' not registered in index.")

@dp.message(Command("calc"))
async def handle_calculator_command(message: types.Message):
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Format error! Use: `/calc <amount> <ticker>`\nExample: `/calc 2.5 sol`", parse_mode="Markdown")
        return

    try:
        amount = float(args[1])
    except ValueError:
        await message.reply("Please input a valid number for the amount!")
        return

    ticker = args[2].lower()
    coin_id = TICKER_MAP.get(ticker, ticker)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if coin_id in data:
                        price = data[coin_id]["usd"]
                        total_usdt = amount * price
                        
                        reply_msg = (
                            f"🧮 **Conversion Calculator**\n"
                            f"-------------------------\n"
                            f"🪙 **Input:** {amount:,.4f} {ticker.upper()}\n"
                            f"💵 **Rate:** ${price:,.2f} USDT\n"
                            f"-------------------------\n"
                            f"💰 **Total Value:** ${total_usdt:,.2f} USDT ✨\n"
                            f"-------------------------\n"
                        )
                        await message.reply(reply_msg, parse_mode="Markdown")
                    else:
                        await message.reply(f"Could not find market rate for '{ticker}'.")
    except Exception as e:
        logging.error(f"Calculator Error: {e}")
        await message.reply("Error completing conversion math.")

@dp.message(Command("gas"))
async def handle_gas_command(message: types.Message):
    await message.reply("🔄 Fetching multi-network real-time gas fees... Hang tight!")
    eth_gwei = 15
    btc_sat = 22
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.blocknative.com/gasprices/blockprices") as response:
                if response.status == 200:
                    data = await response.json()
                    eth_gwei = int(data["blockPrices"][0]["estimatedPrices"][0]["price"])
    except Exception: pass

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://mempool.space/api/v1/fees/recommended") as response:
                if response.status == 200:
                    data = await response.json()
                    btc_sat = data["fastestFee"]
    except Exception: pass

    gas_card = (
        f"⛽ **WEB3 MULTI-CHAIN GAS TRACKER**\n"
        f"-------------------------------------\n\n"
        f"🔹 **Ethereum (ETH Mainnet)**\n"
        f"• Base Fee: `{eth_gwei} Gwei`\n"
        f"• Average Transfer: ~${(eth_gwei * 0.04):.2f} USDT\n\n"
        f"🔸 **Bitcoin (BTC Network)**\n"
        f"• High Priority: `{btc_sat} sat/vB`\n"
        f"• Settlement Time: ~10 Minutes\n\n"
        f"🔮 **Solana (SOL Network)**\n"
        f"• Base Fee: `0.000005 SOL` (~$0.0008)\n"
        f"• Priority Vote (Heavy congestion): ~$0.003 USDT\n\n"
        f"💎 **The Open Network (TON)**\n"
        f"• Standard Jetton Jet-Transfer: `0.05 TON`\n"
        f"• Status: Smooth & Optimized\n\n"
        f"-------------------------------------\n"
        f"Always review wallet parameters before execution!"
    )
    await message.reply(gas_card, parse_mode="Markdown")

@dp.message(CommandStart())
async def handle_start_command(message: types.Message):
    if message.from_user.username:
        user_registry[f"@{message.from_user.username.lower()}"] = message.from_user.id

    welcome_text = (
        "Welcome to Web3 Brain AI!\n\n"
        "⚡ **Available Command Tools:**\n"
        "• `/p <ticker>` - Check live prices\n"
        "• `/calc <amount> <ticker>` - Convert crypto directly to USDT\n"
        "• `/gas` - Check multi-chain gas specs\n"
        "• `/pm @username <text>` - Send a direct private message\n\n"
        "Or just ask: *'what is btc price?'*"
    )
    await message.reply(welcome_text, parse_mode="Markdown")

# 5. Core Content Processing Engine (AI + Context Awareness)
@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text:
        return

    # Track username mappings dynamically as people talk in the group chat
    if message.from_user.username:
        user_registry[f"@{message.from_user.username.lower()}"] = message.from_user.id

    bot_info = await bot.get_me()
    bot_username = f"@{bot_info.username}"
    
    is_private = message.chat.type == "private"
    is_tagged = bot_username in message.text
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id

    # Strictly process if it's a private chat, tagged, or replied to
    if is_private or is_tagged or is_reply_to_bot:
        text_clean = message.text.replace(bot_username, "").lower().strip()
        
        # Look for natural pricing keywords
        if any(keyword in text_clean for keyword in ["price", "how much", "rate", "cost"]):
            for word in text_clean.split():
                clean_word = re.sub(r'[^\w]', '', word)
                if clean_word in TICKER_MAP:
                    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
                    structured_card = await get_structured_price_card(clean_word)
                    if structured_card:
                        await message.reply(structured_card, parse_mode="Markdown")
                        return

        # AI Fallback Brain Execution
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        clean_prompt = message.text.replace(bot_username, "").strip()
        
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": clean_prompt if clean_prompt else "Hello!"}
                ],
                temperature=0.7,
            )
            reply_text = response.choices[0].message.content
            if reply_text:
                await message.reply(reply_text.strip(), parse_mode=None)
        except Exception as e:
            logging.error(f"Groq API Error: {e}")
            await message.reply("Sorry, I encountered a network error. Please try again!")

# 6. Dummy Web Server to satisfy Render health checks
async def home_page(request):
    return web.Response(text="Engine is Online and Running Fine!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", home_page)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await start_web_server()
    logging.info("Polling Engine Live with Restructured Handlers!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

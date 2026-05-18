import os
import asyncio
import sys
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from google import genai
from google.genai import types as genai_types

# Render will read your tokens securely from its dashboard using these lines
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
ai_client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """
You are a standalone, elite Web3 AI Assistant. 
Your job is to answer user questions regarding blockchain, cryptocurrency, decentralized finance (DeFi), smart contracts, gas fees, and ecosystems like Solana and Ethereum.

Rules:
1. Be highly accurate, professional, and clear.
2. Keep formatting simple so it transmits reliably. Do not use complex markdown tags.
3. SECURITY: Explicitly remind users to NEVER share their seed phrases or private keys.
"""

@dp.message(CommandStart())
async def handle_start_command(message: types.Message):
    welcome_text = (
        "Welcome to Web3 Brain AI!\n\n"
        "I am an artificial intelligence assistant dedicated to answering your cryptocurrency, blockchain, and decentralized finance questions.\n\n"
        "Ask me anything about tokens, smart contracts, gas fees, or ecosystems like Solana and Ethereum to get started!"
    )
    await message.answer(welcome_text)

@dp.message()
async def handle_incoming_messages(message: types.Message):
    if not message.text:
        return
    
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=message.text,
            config=genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
            ),
        )
        
        if response.text:
            await message.reply(response.text, parse_mode=None)
        else:
            await message.reply("I processed your request but couldn't generate an answer.")
            
    except Exception as e:
        logging.error(f"Error handling Gemini API request: {e}")
        await message.reply("Sorry, the AI network is currently busy or encountered an error. Please try asking your question again in a moment!")

async def main():
    logging.info("Starting Web3 Standalone AI Bot...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")

import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()

from utils.raphael import ensure_raphael_ready

from pathlib import Path
from dotenv import load_dotenv
import os

# .env 파일을 bot.py가 있는 폴더에서 강제 로드
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ .env에 DISCORD_TOKEN 없음")


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

@bot.event
async def on_ready():
    print(f"🤖 로그인 완료: {bot.user} (ID: {bot.user.id})")
    bot.loop.create_task(status_task())
    

# 상태 메세지 #
import random
import asyncio
from discord import Activity, ActivityType

async def status_task():
    await bot.wait_until_ready()
    statuses = [
        "📦 장터게시판 보는 중",
        "🌤️ 날씨 확인 중",
        "🛠️ 제작하는 중",
        "🎁 선물을 기다리는 중",
        "❤️ 호감도 체크 중",
        "😺 지피띠니랑 노는 중"
    ]
    while not bot.is_closed():
        activity = Activity(type=ActivityType.watching, name=random.choice(statuses))
        await bot.change_presence(activity=activity)
        await asyncio.sleep(3600)  # 1시간 (초 단위)




@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Slash 명령은 interaction 이벤트로 따로 처리됨 → 무시
    if message.interaction is not None:
        return

    lowered = message.content.lower()
    chat = bot.get_cog("AIChatCog")

    # 🔥 AIChat 전용 채널에서만 처리 (Q2 = A)
    if chat and message.channel.id == AI_CHAT_CHANNEL_ID:
        handled = await chat.handle_ai_chat(message)
        if handled:
            return  # AIChat이 처리했으면 바로 종료

    # 🌟 자연어 가격
    if any(w in lowered for w in ["시세", "얼마", "가격"]):
        market = bot.get_cog("MarketCog")
        if market:
            await market.search_and_reply(message)
        return  # 처리 후 종료!

    # 🌟 자연어 날씨
    if any(w in lowered for w in ["날씨", "기상", "어때"]):
        weather = bot.get_cog("WeatherCog")
        if weather:
            await weather.reply_weather_from_message(message)
        return  # 처리 후 종료!

    # 🎯 명령어는 마지막에 딱 1번만
    await bot.process_commands(message)


    chat = bot.get_cog("AIChatCog")
    if chat:
        return await chat.on_message(message)

    await bot.process_commands(message)

async def setup_extensions():
    await bot.load_extension("cogs.weather")
    await bot.load_extension("cogs.market")
    await bot.load_extension("cogs.ai_chat")
    await bot.load_extension("cogs.crafting")
    await bot.load_extension("cogs.economy")
    await bot.load_extension("cogs.help_info")
    await bot.load_extension("cogs.admin")

async def main():
    ensure_raphael_ready()
    async with bot:
        await setup_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
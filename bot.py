import os
import asyncio
import random
from pathlib import Path

import discord
from discord.ext import commands
from discord import Activity, ActivityType
from dotenv import load_dotenv

from utils.raphael import ensure_raphael_ready

# .env 로드
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("DISCORD_TOKEN")
AI_CHAT_CHANNEL_ID = int(os.getenv("AI_CHAT_CHANNEL_ID", "0"))
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

# 상태 메세지
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
        await asyncio.sleep(3600)


print("🔥 on_message fired:", id(on_message))


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # 슬래시 명령으로 들어온 건 따로 처리되니까 패스
    if message.interaction is not None:
        return

    lowered = message.content.lower()

    # 💬 AI 채팅 전용 채널
    from cogs.ai_chat import AI_CHAT_CHANNEL_ID as AI_ID_FROM_COG  # 같은 값 쓸 거면 이 라인 대신 위에서 os.getenv 써도 됨
    chat = bot.get_cog("AIChatCog")
    if chat and message.channel.id == AI_CHAT_CHANNEL_ID:
        # AIChat이 처리하고 바로 종료
        await chat.handle_ai_chat(message)
        return

    # 💰 자연어 시세
    if any(w in lowered for w in ["시세", "얼마", "가격"]):
        market = bot.get_cog("MarketCog")
        if market:
            await market.search_and_reply(message)
        return

    # 🌤️ 자연어 날씨
    if any(w in lowered for w in ["날씨", "기상", "어때"]):
        weather = bot.get_cog("WeatherCog")
        if weather:
            await weather.reply_weather_from_message(message)
        return

    # ❗ 나머지는 프리픽스 명령어
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

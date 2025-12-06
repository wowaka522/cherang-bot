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

    synced = await bot.tree.sync()
    print(f"🔄 슬래시 명령 싱크 완료: {len(synced)}개")
    print("📌 현재 Slash 명령:")
    for cmd in synced:
        print(" -", cmd.name)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Slash command는 여기서 패스
    if message.content.startswith("/"):
        await bot.process_commands(message)
        return

    lowered = message.content.lower()

    # 자연어 Market
    if any(w in lowered for w in ["시세", "얼마", "가격"]):
        market = bot.get_cog("MarketCog")
        if market:
            await market.search_and_reply(message)
        return

    # 자연어 Weather
    if any(w in lowered for w in ["날씨", "기상", "어때"]):
        weather = bot.get_cog("WeatherCog")
        if weather:
            await weather.reply_weather_from_message(message)
        return

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

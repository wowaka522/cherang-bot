import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# .env 파일 강제 로드
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ .env에 DISCORD_TOKEN 없음")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    application_id=int(os.getenv("APPLICATION_ID"))
)

from cogs.tts import VoiceView  # 👈 추가


# ============================= #
#        봇 로그인 처리
# ============================= #
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"🌐 Slash Commands Synced: {len(synced)}")
    except Exception as e:
        print("Slash Sync Error:", e)

    # 👇 persistent view 등록 (가장 중요!)
    bot.add_view(VoiceView())
    print("🔗 Persistent Views Registered")

    print("📌 Loaded COGs:", list(bot.cogs.keys()))
    print(f"🤖 로그인 완료: {bot.user} (ID: {bot.user.id})")


# ============================= #
#         상태 메시지
# ============================= #
import random
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
        await asyncio.sleep(3600)


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # prefix 명령어 최우선
    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return

    lowered = message.content.lower()

    # 자연어 처리
    if "시세" in lowered or "얼마" in lowered or "가격" in lowered:
        market = bot.get_cog("MarketCog")
        if market:
            return await market.search_and_reply(message)

    if "날씨" in lowered or "기상" in lowered or "어때" in lowered:
        weather = bot.get_cog("WeatherCog")
        if weather:
            return await weather.reply_weather_from_message(message)

    await bot.process_commands(message)


# ============================= #
#        Cog Load
# ============================= #
async def setup_extensions():
    await bot.load_extension("cogs.weather")
    await bot.load_extension("cogs.market")
    await bot.load_extension("cogs.ai_chat")
    await bot.load_extension("cogs.crafting")
    await bot.load_extension("cogs.economy")
    await bot.load_extension("cogs.help_info")
    await bot.load_extension("cogs.admin")
    await bot.load_extension("cogs.shop")
    await bot.load_extension("cogs.inventory")
    await bot.load_extension("cogs.craft")
    await bot.load_extension("cogs.love")
    await bot.load_extension("cogs.gambling")
    await bot.load_extension("cogs.quest")
    await bot.load_extension("cogs.tts")


async def main():
    asyncio.create_task(status_task())  # 상태메시지 유지
    async with bot:
        await setup_extensions()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())

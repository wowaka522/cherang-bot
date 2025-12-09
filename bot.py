import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path
import random
from discord import Activity, ActivityType

# ======================= #
#   .env Load
# ======================= #
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ .env에 DISCORD_TOKEN 없음")


# ======================= #
#   Intents
# ======================= #
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    application_id=int(os.getenv("APPLICATION_ID"))
)


# ======================= #
#        상태 메시지
# ======================= #
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


# ======================= #
#           Ready
# ======================= #
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"🌐 Slash Commands Synced: {len(synced)}")
    except Exception as e:
        print("Slash Sync Error:", e)

    print("🤖 봇 준비 완료!")


@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type.name == "component":
        print(f"[DBG] Interaction Component Received: {interaction.data}")


# ======================= #
#    자연어 + TTS + prefix
# ======================= #
@bot.event
async def on_message(message: discord.Message):
    # 디버그
    # print("🌐 Main on_message fired")  # 필요시 활성화

    if message.author.bot:
        return

    lowered = message.content.lower()

    # 1) 자연어 처리
    if any(w in lowered for w in ["시세", "얼마", "가격"]):
        market = bot.get_cog("MarketCog")
        if market:
            await market.search_and_reply(message)
        return

    if any(w in lowered for w in ["날씨", "기상", "어때"]):
        weather = bot.get_cog("WeatherCog")
        if weather:
            await weather.reply_weather_from_message(message)
        return

    # 2) prefix 명령어 처리
    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)

    # 3) TTS listener 호출
    tts = bot.get_cog("TTSCog")
    if tts:
        await tts.on_message(message)


# ======================= #
#       Load Extensions
# ======================= #
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


# ======================= #
#        실행
# ======================= #
async def main():
    await setup_extensions()
    asyncio.create_task(status_task())

    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())

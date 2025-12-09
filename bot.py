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
intents.members = True
intents.guilds = True
intents.guild_messages = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    application_id=int(os.getenv("APPLICATION_ID"))
)


@bot.event
async def on_ready():
    # Persistent View 등록만 함!!
    tts = bot.get_cog("TTSCog")
    if tts:
        bot.add_view(tts.view)
        print("🔗 TTS View Registered")

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
    await setup_extensions()  # 먼저 Cogs 로드

    # 🔥 여기에서 TTSCog.view를 등록한다!!
    tts = bot.get_cog("TTSCog")
    if tts:
        bot.add_view(tts.view)
        print("🔗 TTS Persistent View Registered (Main)")

    # Slash sync는 on_ready()에서 수행
    asyncio.create_task(status_task())
    async with bot:
        await bot.start(TOKEN)



if __name__ == "__main__":
    asyncio.run(main())

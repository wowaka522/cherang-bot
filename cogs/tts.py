import json
from pathlib import Path
import re
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View

from utils.tts_engine import google_tts, bing_tts, preprocess

CONFIG_PATH = Path("data") / "tts_config.json"

VOICE_MAP = {
    "여성 A (Google)": ("google", "ko-KR-Neural2-A"),
    "남성 B (Google)": ("google", "ko-KR-Neural2-B"),
    "여성 C (Bing)": ("bing", "SunHiNeural"),
    "남성 D (Bing)": ("bing", "BongJinNeural"),
}


def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text("utf-8"))
    return {"text_channel_id": None, "user_voice": {}}


def save_config(cfg: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")


class TTSCog(commands.Cog):
    """Google + Bing TTS with Voice UI"""

    def __init__(self, bot):
        self.bot = bot
        self.cfg = load_config()

    # ====================
    # /목소리 (UI 셀렉트 메뉴)
    # ====================
    @app_commands.command(name="목소리", description="TTS 목소리 선택")
    async def choose_voice(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        select = Select(
            placeholder="목소리를 선택하세요!",
            options=[
                discord.SelectOption(label=n, description=f"{VOICE_MAP[n][0].upper()} 엔진") 
                for n in VOICE_MAP.keys()
            ]
        )

        async def on_select(i: discord.Interaction):
            chosen = select.values[0]
            self.cfg["user_voice"][user_id] = chosen
            save_config(self.cfg)

            await i.response.edit_message(
                content=f"🔊 목소리를 **{chosen}**으로 설정했어요!",
                view=None
            )

        select.callback = on_select
        view = View()
        view.add_item(select)

        await interaction.response.send_message("목소리를 선택해주세요.", view=view, ephemeral=True)

    # ====================
    # /입장 & !입장
    # ====================
    @app_commands.command(name="입장", description="음성채널에 봇 입장")
    async def slash_join(self, interaction):
        await self._join(interaction)

    @commands.command(name="입장")
    async def cmd_join(self, ctx):
        await self._join(ctx)

    async def _join(self, source):
        user = source.user if isinstance(source, discord.Interaction) else source.author
        if not user.voice:
            return await source.response.send_message("먼저 음성채널 들어가.", ephemeral=True) \
                if isinstance(source, discord.Interaction) else \
                   await source.reply("먼저 음성채널 들어가.")

        channel = user.voice.channel
        vc = channel.guild.voice_client

        if vc:
            await vc.move_to(channel)
        else:
            await channel.connect()

        msg = f"🎧 {channel.mention} 입장!"
        if isinstance(source, discord.Interaction):
            await source.response.send_message(msg)
        else:
            await source.send(msg)

    # ====================
    # /퇴장 & !퇴장
    # ====================
    @app_commands.command(name="퇴장", description="봇 음성채널 퇴장")
    async def slash_leave(self, interaction):
        await self._leave(interaction)

    @commands.command(name="퇴장")
    async def cmd_leave(self, ctx):
        await self._leave(ctx)

    async def _leave(self, source):
        guild = source.guild if isinstance(source, discord.Interaction) else source.guild
        vc = guild.voice_client
        if not vc:
            return

        await vc.disconnect()
        msg = "👋 빠이빠이~"
        if isinstance(source, discord.Interaction):
            await source.response.send_message(msg)
        else:
            await source.send(msg)

    # ====================
    # on_message → TTS 분석
    # ====================
    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return

        if msg.channel.id != self.cfg.get("text_channel_id"):
            return

        vc = msg.guild.voice_client
        if not vc:
            return

        text = preprocess(msg.content.strip())
        if not text:
            return

        user_id = str(msg.author.id)
        selected = self.cfg["user_voice"].get(user_id, "여성 A (Google)")
        engine, voice = VOICE_MAP[selected]

        print(f"[TTS] {engine} | {voice} | {text}")

        ogg = google_tts(text, voice) if engine == "google" else bing_tts(text, voice)

        if ogg:
            vc.stop()
            vc.play(discord.FFmpegPCMAudio(
                ogg,
                before_options="-nostdin -vn",
                options="-ac 2 -ar 48000"
            ))


async def setup(bot):
    await bot.add_cog(TTSCog(bot))
    print("🔊 TTSCog Loaded with UI")

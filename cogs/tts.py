import json
from pathlib import Path
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
    """Google/Bing TTS + UI Voice Select"""

    def __init__(self, bot):
        self.bot = bot
        self.cfg = load_config()

    @app_commands.command(name="목소리", description="TTS 목소리 선택")
    async def choose_voice(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        select = Select(
            placeholder="목소리를 선택하세요!",
            options=[
                discord.SelectOption(label=name) for name in VOICE_MAP.keys()
            ]
        )

        async def on_select(i: discord.Interaction):
            chosen = select.values[0]
            self.cfg["user_voice"][user_id] = chosen
            save_config(self.cfg)

            await i.response.defer()
            await i.edit_original_response(
                content=f"🔊 목소리를 **{chosen}**으로 설정했어요!",
                view=None,
            )

        select.callback = on_select
        view = View()
        view.add_item(select)

        await interaction.response.send_message(
            "👇 아래에서 목소리를 골라주세요!",
            view=view,
            ephemeral=True
        )

    @commands.command(name="입장")
    async def cmd_join(self, ctx):
        await self._join(ctx)

    @app_commands.command(name="입장")
    async def slash_join(self, interaction):
        await self._join(interaction)

    async def _join(self, source):
        user = source.user if isinstance(source, discord.Interaction) else source.author
        if not user.voice:
            msg = "음성 채널에 먼저 들어간 후 시도해줘!"
            return await self._send(source, msg)

        channel = user.voice.channel
        vc = user.guild.voice_client

        if vc:
            await vc.move_to(channel)
        else:
            await channel.connect()

        await self._send(source, f"🎧 {channel.mention} 입장!")

    @commands.command(name="퇴장")
    async def cmd_leave(self, ctx):
        await self._leave(ctx)

    @app_commands.command(name="퇴장")
    async def slash_leave(self, interaction):
        await self._leave(interaction)

    async def _leave(self, source):
        vc = source.guild.voice_client
        if not vc:
            return

        await vc.disconnect()
        await self._send(source, "👋 빠이빠이~")

    async def _send(self, source, text):
        if isinstance(source, discord.Interaction):
            await source.response.send_message(text, ephemeral=False)
        else:
            await source.send(text)

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
        chosen = self.cfg["user_voice"].get(user_id, "여성 A (Google)")
        engine, voice = VOICE_MAP.get(chosen, VOICE_MAP["여성 A (Google)"])

        print(f"[TTS] {engine} | {voice} | {text}")

        ogg = google_tts(text, voice) if engine == "google" else bing_tts(text, voice)

        if ogg:
            if vc.is_playing():
                vc.stop()

            vc.play(discord.FFmpegPCMAudio(
                ogg,
                before_options="-nostdin -vn",
                options="-ac 2 -ar 48000"
            ))


async def setup(bot):
    await bot.add_cog(TTSCog(bot))
    print("🔊 TTSCog Loaded with UI")

import json
import io
from pathlib import Path

import discord
from discord.ext import commands
from discord import app_commands

from utils.azure_tts import azure_tts
import soundfile as sf

CONFIG_PATH = Path("data") / "tts_config.json"

def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text("utf-8"))
    return {"text_channel_id": None}

def save_config(cfg: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")


class TTSCog(commands.Cog):
    """Google TTS Only (Stable Version)"""

    def __init__(self, bot):
        self.bot = bot
        self.cfg = load_config()

    #---------------------------
    # /채널지정
    #---------------------------
    @app_commands.command(name="채널지정", description="TTS 텍스트 채널 설정")
    @app_commands.describe(channel="비우면 현재 채널 지정")
    async def set_tts_channel(self, interaction, channel: discord.TextChannel=None):

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("관리자만 가능!", ephemeral=True)

        if channel is None:
            if isinstance(interaction.channel, discord.TextChannel):
                channel = interaction.channel
            else:
                return await interaction.response.send_message(
                    "텍스트 채널에서 실행하거나 채널을 직접 지정해", ephemeral=True
                )

        self.cfg["text_channel_id"] = channel.id
        save_config(self.cfg)

        await interaction.response.send_message(
            f"TTS 채널: {channel.mention} 지정 완료"
        )

    #---------------------------
    # !입장
    #---------------------------
    @commands.command(name="입장")
    async def join_voice(self, ctx):
        if not ctx.author.voice:
            return await ctx.reply("먼저 음성 채널 들어가.", mention_author=False)

        channel = ctx.author.voice.channel
        try:
            if ctx.voice_client:
                await ctx.voice_client.move_to(channel)
            else:
                await channel.connect()
            print(f"[TTS] Connected: {channel.name}")
        except Exception as e:
            print("❌ join failed:", e)

    # !퇴장
    @commands.command(name="퇴장")
    async def leave_voice(self, ctx):
        vc = ctx.voice_client
        if vc:
            await vc.disconnect()

    #---------------------------
    # 텍스트 감지 TTS
    #---------------------------
    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return

        ch_id = self.cfg.get("text_channel_id")
        if not ch_id or msg.channel.id != ch_id:
            return

        vc = msg.guild.voice_client
        if not vc:
            return  # 음성채널 미입장 상태에서 skip

        text = msg.content.strip()
        if not text or text.startswith("!"):
            return

        print("[TTS]", text)

        try:
            audio = google_tts(text)

            buf = io.BytesIO()
            sf.write(buf, audio, 24000, format="wav")
            buf.seek(0)

            if vc.is_playing():
                vc.stop()

            vc.play(discord.FFmpegPCMAudio(buf, pipe=True))
        except Exception as e:
            print("❌ playback:", e)
            
    @set_tts_channel.error
    async def set_tts_error(self, interaction, error):
        print("❌ Slash command error:", error)



async def setup(bot):
    await bot.add_cog(TTSCog(bot))
    print("🔊 TTSCog Loaded")

import discord
from discord.ext import commands
from discord import app_commands
from pathlib import Path
from utils.google_tts import google_tts
import io
import soundfile as sf

class TTSCog(commands.Cog):
    """Google TTS Only"""

    def __init__(self, bot):
        self.bot = bot
        self.tts_channel_id = None  # 따로 저장 필요하면 DB 사용

    # ================== Slash Command ==================
    @app_commands.command(name="tts", description="TTS 재생 채널을 설정합니다.")
    @app_commands.describe(channel="TTS가 재생될 텍스트 채널")
    async def set_tts_channel(self, interaction: discord.Interaction, channel: discord.abc.GuildChannel):
        self.tts_channel_id = channel.id
        await interaction.response.send_message(f"TTS 채널 설정 완료! → {channel.mention}")

    # ================== TEXT COMMAND ==================

    @commands.command(name="입장")
    async def join(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("음성채널 먼저 들어가~")

        ch = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(ch)
        else:
            await ch.connect()

    @commands.command(name="퇴장")
    async def leave(self, ctx):
        vc = ctx.voice_client
        if vc:
            await vc.disconnect()

    # ================== TEXT 감지 후 재생 ==================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if self.tts_channel_id is None:
            return
        if message.channel.id != self.tts_channel_id:
            return

        vc = message.guild.voice_client
        if not vc:
            if message.author.voice:
                await message.author.voice.channel.connect()
                vc = message.guild.voice_client
        else:
            return

        text = message.content.strip()
        if not text or text.startswith("!"):
            return

        try:
            audio_data = google_tts(text)

            buffer = io.BytesIO()
            sf.write(buffer, audio_data, 24000, format='WAV')
            buffer.seek(0)

            if vc.is_playing():
                vc.stop()

            vc.play(discord.FFmpegPCMAudio(buffer, pipe=True))

        except Exception as e:
            print("[TTS ERROR]", e)

async def setup(bot):
    await bot.add_cog(TTSCog(bot))
    print("🔊 TTSCog Loaded")

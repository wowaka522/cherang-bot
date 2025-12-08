import discord
from discord.ext import commands
from pathlib import Path
from utils.google_tts import google_tts

class TTSCog(commands.Cog):
    """Google TTS Only"""

    def __init__(self, bot):
        self.bot = bot
        self.tts_channel_id = None  # 따로 저장 필요하면 config 사용

    # ================== TEXT COMMAND 버전 ==================

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

    @commands.command(name="tts채널")
    async def set_tts_channel(self, ctx, channel: discord.TextChannel):
        self.tts_channel_id = channel.id
        await ctx.send(f"TTS 채널 설정! → {channel.mention}")

    # ================== TEXT 감지 후 재생 ==================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # 설정된 채널 체크
        if self.tts_channel_id is None:
            return
        if message.channel.id != self.tts_channel_id:
            return

        vc = message.guild.voice_client
        if not vc:
            return

        text = message.content.strip()
        if not text:
            return

        # 명령어는 읽지 않음
        if text.startswith("!"):
            return

        try:
            # 메모리에 직접 TTS 생성 (파일 없음!)
            audio_data = google_tts(text)  # numpy array + sr 반환 전제

            import io
            import soundfile as sf
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

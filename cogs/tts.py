import asyncio
import discord
from discord.ext import commands
from discord import app_commands

from utils.google_tts import google_tts
from utils.tts_db import get_voice, set_voice

tts_queue = asyncio.Queue()
player_running = False


async def play_audio(vc: discord.VoiceClient, path: str):
    vc.play(discord.FFmpegPCMAudio(path))
    while vc.is_playing():
        await asyncio.sleep(0.1)


async def player_loop(bot):
    global player_running
    if player_running:
        return
    player_running = True

    while True:
        guild, audio = await tts_queue.get()
        vc = guild.voice_client
        if not vc or not vc.is_connected():
            continue

        try:
            await play_audio(vc, audio)
        except:
            pass


class VoiceSelect(discord.ui.View):
    async def _update(self, interaction, text):
        await interaction.response.defer(ephemeral=True)
        await interaction.edit_original_response(content=text, view=None)

    @discord.ui.button(label="여성 A", style=discord.ButtonStyle.primary)
    async def female_a(self, interaction, button):
        set_voice(interaction.user.id, "female_a")
        await self._update(interaction, "여성 A로 설정됨!")

    @discord.ui.button(label="여성 B", style=discord.ButtonStyle.primary)
    async def female_b(self, interaction, button):
        set_voice(interaction.user.id, "female_b")
        await self._update(interaction, "여성 B로 설정됨!")

    @discord.ui.button(label="남성 A", style=discord.ButtonStyle.secondary)
    async def male_a(self, interaction, button):
        set_voice(interaction.user.id, "male_a")
        await self._update(interaction, "남성 A로 설정됨!")

    @discord.ui.button(label="남성 B", style=discord.ButtonStyle.secondary)
    async def male_b(self, interaction, button):
        set_voice(interaction.user.id, "male_b")
        await self._update(interaction, "남성 B로 설정됨!")



class TTS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = None

        bot.loop.create_task(player_loop(bot))

    @app_commands.guild_only()
    @app_commands.command(name="목소리", description="TTS 목소리를 변경합니다")
    async def voice(self, interaction):
        await interaction.response.send_message(
            "원하는 목소리를 선택하세요 😺",
            view=VoiceSelect(),
            ephemeral=True
        )

    @app_commands.command(name="채널지정", description="TTS를 사용할 채널을 설정합니다")
    async def set_channel(self, interaction):
        self.channel_id = interaction.channel.id
        await interaction.response.send_message("이 채널에서 TTS를 사용할게요!", ephemeral=True)

    @commands.command(name="입장")
    async def join(self, ctx):
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()

    @commands.command(name="퇴장")
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()

    async def enqueue(self, message: discord.Message):
        voice = get_voice(message.author.id)
        audio_path = google_tts(message.content, voice)

        await tts_queue.put((message.guild, audio_path))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if self.channel_id != message.channel.id:
            return
        if not message.guild.voice_client:
            return

        await self.enqueue(message)


async def setup(bot):
    await bot.add_cog(TTS(bot))

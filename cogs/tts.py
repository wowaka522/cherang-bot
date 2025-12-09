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


class VoiceSelect(Select):
    def __init__(self, bot, cfg, user_id):
        self.bot = bot
        self.cfg = cfg
        self.user_id = user_id

        super().__init__(
            placeholder="목소리를 선택하세요!",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=n) for n in VOICE_MAP.keys()]
        )

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        self.cfg["user_voice"][self.user_id] = chosen
        save_config(self.cfg)

        await interaction.response.edit_message(
            content=f"🔊 목소리가 **{chosen}**으로 설정되었습니다!",
            view=None
        )


class VoiceView(View):
    def __init__(self, bot, cfg, user_id):
        super().__init__(timeout=60)
        self.add_item(VoiceSelect(bot, cfg, user_id))


class TTSCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = load_config()

    @app_commands.command(name="목소리", description="TTS 목소리 선택")
    async def voice_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        view = VoiceView(self.bot, self.cfg, user_id)

        await interaction.edit_original_response(
            content="👇 아래에서 목소리를 골라주세요!",
            view=view
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
            return await self._reply(source, "먼저 음성 채널 들어가!")

        channel = user.voice.channel
        vc = user.guild.voice_client

        if vc:
            await vc.move_to(channel)
        else:
            await channel.connect()

        await self._reply(source, f"🎧 {channel.mention} 입장!")

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
        await self._reply(source, "👋 빠이빠이~")

    async def _reply(self, source, msg):
        if isinstance(source, discord.Interaction):
            try:
                await source.response.send_message(msg)
            except:
                await source.followup.send(msg)
        else:
            await source.send(msg)

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return

        vc = msg.guild.voice_client
        if not vc or msg.channel.id != self.cfg.get("text_channel_id"):
            return

        text = preprocess(msg.content)
        if not text or text.startswith("!"):
            return

        user_id = str(msg.author.id)
        chosen = self.cfg["user_voice"].get(user_id, "여성 A (Google)")
        engine, voice_name = VOICE_MAP.get(chosen, VOICE_MAP["여성 A (Google)"])

        ogg = google_tts(text, voice_name) if engine == "google" else bing_tts(text, voice_name)

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
    print("🔊 TTSCog Loaded - FINAL SAFE VERSION")

import json
import tempfile
from pathlib import Path
import soundfile as sf
import discord
from discord.ext import commands
from discord import app_commands

from utils.google_tts import google_tts

CONFIG_PATH = Path("data") / "tts_config.json"


def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text("utf-8"))
    return {"text_channel_id": None, "user_voice": {}}


def save_config(cfg: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")


VOICE_MAP = {
    "여성 A": "ko-KR-Neural2-A",
    "남성 B": "ko-KR-Neural2-B",
}


class VoiceSelect(discord.ui.Select):
    def __init__(self, cfg):
        self.cfg = cfg
        super().__init__(
            custom_id="voice_select_v3",
            placeholder="🔊 목소리를 선택하세요!",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=v) for v in VOICE_MAP.keys()]
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        chosen = self.values[0]
        uid = str(interaction.user.id)
        self.cfg["user_voice"][uid] = chosen
        save_config(self.cfg)

        print(f"[TTS] Voice Selected: {chosen}")

        await interaction.followup.send(
            f"🔈 **{chosen}** 으로 설정 완료!",
            ephemeral=True
        )


class VoiceView(discord.ui.View):
    def __init__(self, cfg):
        super().__init__(timeout=None)
        self.add_item(VoiceSelect(cfg))


class TTSCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = load_config()

        # Only one persistent view
        self.view = VoiceView(self.cfg)
        self.bot.add_view(self.view)

    @app_commands.command(name="목소리", description="TTS 목소리 변경")
    async def voice_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "👇 아래에서 목소리를 선택하세요!",
            view=self.view,
            ephemeral=True
        )

    @app_commands.command(name="채널지정", description="TTS 텍스트 채널 설정")
    async def set_tts_channel(self, interaction, channel: discord.TextChannel=None):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("관리자만 가능!", ephemeral=True)

        if channel is None:
            channel = interaction.channel

        self.cfg["text_channel_id"] = channel.id
        save_config(self.cfg)

        await interaction.response.send_message(
            f"📌 이제 TTS 채널이 **{channel.mention}** 로 설정됐어요!"
        )

    @commands.command(name="입장")
    async def join_voice(self, ctx):
        if not ctx.author.voice:
            return await ctx.reply("음성 채널 먼저 들어가!")
        ch = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(ch)
        else:
            await ch.connect()

    @commands.command(name="퇴장")
    async def leave_voice(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return

        ch_id = self.cfg.get("text_channel_id")
        if not ch_id or msg.channel.id != ch_id:
            return

        vc = msg.guild.voice_client
        if not vc:
            return

        text = msg.content.strip()
        if not text or text.startswith("!"):
            return

        uid = str(msg.author.id)
        chosen = self.cfg["user_voice"].get(uid, "여성 A")
        voice = VOICE_MAP[chosen]

        print(f"[TTS] {chosen} | text='{text[:30]}'")

        try:
            audio_np, sample_rate = google_tts(text, voice)
            print("google_tts return:", audio_np, sample_rate)

            if audio_np is None:
                print("❌ google_tts returned None")
                return

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                sf.write(tmp.name, audio_np, sample_rate, format="WAV")
                wav_path = tmp.name

            if vc.is_playing():
                vc.stop()

            vc.play(discord.FFmpegPCMAudio(
                wav_path,
                before_options="-nostdin -vn",
                options="-ac 2 -ar 48000"
            ))

            print(f"[TTS] Playing → {wav_path}")

        except Exception as e:
            print("❌ playback:", e)


async def setup(bot):
    await bot.add_cog(TTSCog(bot))
    print("🔊 TTSCog Ready (Voice Stable)")

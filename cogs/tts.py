import json
import tempfile
from pathlib import Path

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View

from utils.google_tts import google_tts
import soundfile as sf

CONFIG_PATH = Path("data") / "tts_config.json"

VOICE_MAP = {
    "여성 A (Google)": "ko-KR-Neural2-A",
    "남성 B (Google)": "ko-KR-Neural2-B",
    "여성 C (Bing)": "SunHiNeural",
    "남성 D (Bing)": "BongJinNeural"
}


def load_config():
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text("utf-8"))
    except:
        pass
    return {"text_channel_id": None, "user_voice": {}}


def save_config(cfg: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")


# ============================= #
#     Voice Select UI Component
# ============================= #
class VoiceSelect(Select):
    def __init__(self):
        super().__init__(
            custom_id="voice_select",
            placeholder="🔊 목소리를 선택하세요!",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=v) for v in VOICE_MAP.keys()]
        )

    async def callback(self, interaction: discord.Interaction):
        cfg = interaction.client.get_cog("TTSCog").cfg
        chosen = self.values[0]
        cfg["user_voice"][str(interaction.user.id)] = chosen
        save_config(cfg)

        print(f"[TTS] Voice Selected: {chosen}")
        await interaction.response.send_message(
            f"✨ 목소리가 **{chosen}** 으로 설정됐어요!",
            ephemeral=True
        )


class VoiceView(View):
    def __init__(self):
        super().__init__(timeout=None)  # persistent
        self.add_item(VoiceSelect())


# ============================= #
#            Cog Main
# ============================= #
class TTSCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = load_config()
        self.view = VoiceView()

    @app_commands.command(name="목소리", description="TTS 목소리 선택")
    async def voice_cmd(self, interaction: discord.Interaction):
        await interaction.followup.send(
            "👇 아래에서 목소리를 선택해 주세요!",
            view=VoiceView(),
            ephemeral=True
        )

    @app_commands.command(name="채널지정", description="TTS 텍스트 채널 설정")
    async def set_tts_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("관리자만 가능!", ephemeral=True)

        if channel is None:
            if isinstance(interaction.channel, discord.TextChannel):
                channel = interaction.channel
            else:
                return await interaction.response.send_message("텍스트 채널에서 실행해!", ephemeral=True)

        self.cfg["text_channel_id"] = channel.id
        save_config(self.cfg)
        await interaction.response.send_message(
            f"📌 이제 이 채널에서 TTS 할게요 → {channel.mention}"
        )

    @commands.command(name="입장")
    async def join_voice(self, ctx):
        if not ctx.author.voice:
            return await ctx.reply("먼저 음성 채널 들어가!")
        ch = ctx.author.voice.channel
        vc = ctx.voice_client
        if vc:
            await vc.move_to(ch)
        else:
            await ch.connect()
        print(f"[TTS] Connected: {ch.name}")

    @commands.command(name="퇴장")
    async def leave_voice(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return

        await self.bot.process_commands(msg)

        ch_id = self.cfg.get("text_channel_id")
        if not ch_id or msg.channel.id != ch_id:
            return

        vc = msg.guild.voice_client
        if not vc:
            return

        text = msg.content
        if not text or text.startswith("!"):
            return

        print(f"[DBG] TTS Trigger: {text[:30]}")

        user_id = str(msg.author.id)
        chosen = self.cfg["user_voice"].get(user_id, "여성 A (Google)")
        voice = VOICE_MAP[chosen]

        try:
            audio_np, sample_rate = google_tts(text, voice)
            if audio_np is None:
                print("❌ google_tts returned None")
                return

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                sf.write(tmp.name, audio_np, sample_rate, format="wav")
                wav_path = tmp.name

            print(f"[TTS] Play → {wav_path}")
            if vc.is_playing():
                vc.stop()

            vc.play(discord.FFmpegPCMAudio(
                wav_path,
                before_options="-nostdin -vn",
                options="-ac 2 -ar 48000"
            ))

        except Exception as e:
            print("❌ playback:", e)


async def setup(bot):
    await bot.add_cog(TTSCog(bot))
    print("🔊 TTSCog Ready (Persistent)")

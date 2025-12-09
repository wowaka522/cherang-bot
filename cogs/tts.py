import json
import io
from pathlib import Path
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View

from utils.tts_engine import google_tts, bing_tts, preprocess
import soundfile as sf

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


def save_config(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")


# =========================
# 목소리 선택 UI
# =========================
class VoiceSelect(Select):
    def __init__(self):
        super().__init__(
            placeholder="🔊 목소리를 선택하세요!",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=k) for k in VOICE_MAP.keys()],
            custom_id="voice_select_menu"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cfg = interaction.client.get_cog("TTSCog").cfg
        chosen = self.values[0]

        cfg["user_voice"][str(interaction.user.id)] = chosen
        save_config(cfg)

        print(f"[TTS] Voice Selected by {interaction.user}: {chosen}")

        await interaction.followup.send(
            f"목소리가 **{chosen}** 으로 설정되었어요!",
            ephemeral=True
        )


class VoiceView(View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(VoiceSelect())


# =========================
# 메인 TTS COG
# =========================
class TTSCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = load_config()

    # /채널지정
    @app_commands.command(name="채널지정", description="TTS 텍스트 채널 설정")
    @app_commands.describe(channel="비우면 현재 채널을 지정")
    async def set_channel(self, interaction, channel: discord.TextChannel = None):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("권한 없음!", ephemeral=True)

        if channel is None:
            channel = interaction.channel

        self.cfg["text_channel_id"] = channel.id
        save_config(self.cfg)

        await interaction.response.send_message(f"📌 TTS 채널 설정됨: {channel.mention}")

    # /목소리 UI 명령
    @app_commands.command(name="목소리", description="TTS 목소리 선택")
    async def select_voice(self, interaction):
        view = VoiceView()
        await interaction.response.send_message(
            "👇 원하는 목소리를 선택하세요!",
            view=view,
            ephemeral=True
        )

    # !입장
    @commands.command(name="입장")
    async def join_voice(self, ctx):
        if not ctx.author.voice:
            return await ctx.reply("음성 채널 먼저 들어가!")

        ch = ctx.author.voice.channel
        try:
            if ctx.voice_client:
                await ctx.voice_client.move_to(ch)
            else:
                await ch.connect()
            print(f"[TTS] Joined Channel: {ch.name}")
        except Exception as e:
            print("❌ join error:", e)

    # !퇴장
    @commands.command(name="퇴장")
    async def leave_voice(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()

    # 메시지 TTS
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

        text = preprocess(msg.content.strip())
        if not text or text.startswith("!"):
            return

        print(f"[TTS] {text}")

        try:
            user_id = str(msg.author.id)
            chosen = self.cfg["user_voice"].get(user_id, "여성 A (Google)")
            engine, voice_name = VOICE_MAP[chosen]

            wav = google_tts(text, voice_name) if engine == "google" else bing_tts(text, voice_name)
            if not wav:
                return

            # 바이트로 변환
            buf = io.BytesIO()
            sf.write(buf, wav, 24000, format="wav")
            buf.seek(0)

            if vc.is_playing():
                vc.stop()

            vc.play(discord.FFmpegPCMAudio(buf, pipe=True))
        except Exception as e:
            print("❌ Playback Error:", e)


async def setup(bot):
    await bot.add_cog(TTSCog(bot))
    print("🔊 TTSCog Loaded (Final Stable)")

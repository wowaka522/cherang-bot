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
    def __init__(self, cfg):
        self.cfg = cfg
        super().__init__(
            placeholder="🔊 목소리를 선택하세요!",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=k) for k in VOICE_MAP.keys()]
        )

    async def callback(self, inter: discord.Interaction):
        user_id = str(inter.user.id)
        chosen = self.values[0]

        self.cfg["user_voice"][user_id] = chosen
        save_config(self.cfg)

        await inter.response.send_message(
            f"🎙️ 목소리가 **{chosen}** 으로 설정되었습니다!",
            ephemeral=True
        )
        print(f"[TTS] User {user_id} set voice: {chosen}")


class TTSCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = load_config()

    # =====================
    # /목소리
    # =====================
    @app_commands.command(name="목소리", description="TTS 목소리 선택")
    async def voice_cmd(self, interaction):
        view = View()
        view.add_item(VoiceSelect(self.cfg))

        await interaction.response.send_message(
            "👇 아래에서 목소리를 선택하세요!",
            view=view,
            ephemeral=True
        )

    # =====================
    # !입장
    # =====================
    @commands.command(name="입장")
    async def join_voice(self, ctx):
        if not ctx.author.voice:
            return await ctx.reply("먼저 음성 채널 들어가!")
        channel = ctx.author.voice.channel
        await channel.connect()
        print(f"[TTS] Connected to: {channel.name}")

    # =====================
    # !퇴장
    # =====================
    @commands.command(name="퇴장")
    async def leave_voice(self, ctx):
        vc = ctx.voice_client
        if vc:
            await vc.disconnect()

    # =====================
    # 메시지 → TTS
    # =====================
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

        text = preprocess(msg.content)
        if not text or text.startswith("!"):
            return

        user_id = str(msg.author.id)
        chosen = self.cfg["user_voice"].get(user_id, "여성 A (Google)")
        engine, voice = VOICE_MAP[chosen]

        print(f"[TTS] {engine} | {voice} | {text}")

        ogg = google_tts(text, voice) if engine == "google" else bing_tts(text, voice)
        if not ogg:
            print("❌ TTS failed")
            return

        if vc.is_playing():
            vc.stop()

        vc.play(discord.FFmpegPCMAudio(
            ogg,
            before_options="-nostdin -vn",
            options="-ac 2 -ar 48000"
        ))


async def setup(bot):
    await bot.add_cog(TTSCog(bot))
    print("🔊 TTSCog Loaded (Final Stable)")

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


# ======================
# Persistent UI 방식
# ======================
class VoiceSelect(Select):
    def __init__(self, cfg):
        self.cfg = cfg
        super().__init__(
            placeholder="🔊 목소리를 선택하세요!",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=k) for k in VOICE_MAP.keys()],
            custom_id="voice_select_menu"
        )

    async def callback(self, inter: discord.Interaction):
        chosen = self.values[0]
        self.cfg["user_voice"][str(inter.user.id)] = chosen
        save_config(self.cfg)

        print(f"[TTS] Voice Selected: {chosen}")

        await inter.response.edit_message(
            content=f"목소리가 **{chosen}** 으로 설정되었습니다!",
            view=None
        )


class VoiceView(View):
    def __init__(self, cfg):
        super().__init__(timeout=None)  # <-- persistent 핵심
        self.add_item(VoiceSelect(cfg))


# ======================
#   Cog
# ======================
class TTSCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = load_config()

        # 봇 부팅 때 persistent UI 등록
        bot.add_view(VoiceView(self.cfg))

    @ app_commands.command(name="목소리", description="TTS 목소리 선택")
    async def voice_cmd(self, interaction):
        view = VoiceView(self.cfg)
        await interaction.response.send_message(
            "👇 아래에서 목소리를 선택해 주세요!",
            view=view,
            ephemeral=False  # 🔥 변경
        )


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
        if not text or text.startswith("!"):
            return

        user_id = str(msg.author.id)
        chosen = self.cfg["user_voice"].get(user_id, "여성 A (Google)")
        engine, voice = VOICE_MAP[chosen]

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
    print("🔊 TTSCog Loaded (Persistent UI Fixed)")

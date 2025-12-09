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

        options = [
            discord.SelectOption(label=name)
            for name in VOICE_MAP.keys()
        ]

        super().__init__(
            placeholder="목소리 선택👩🧑",
            min_values=1,
            max_values=1,
            options=options
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
    async def choose_voice(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        view = VoiceView(self.bot, self.cfg, user_id)
        await interaction.response.send_message(
            "👇 아래에서 목소리 골라보세요!",
            view=view,
        )

    # 기존 입장/퇴장 명령은 그대로 유지
    # (생략: 너가 가진 버전 그대로 유지하면 OK)

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return

        vc = msg.guild.voice_client
        if not vc or msg.channel.id != self.cfg.get("text_channel_id"):
            return

        text = preprocess(msg.content.strip())
        if not text:
            return

        user_id = str(msg.author.id)
        chosen = self.cfg["user_voice"].get(user_id, "여성 A (Google)")
        engine, voice = VOICE_MAP[chosen]

        ogg = google_tts(text, voice) if engine == "google" else bing_tts(text, voice)

        print(f"[TTS] {engine} | {voice} | {text}")

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
    print("🔊 TTSCog Loaded with Select UI")

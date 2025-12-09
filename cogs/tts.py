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
    def __init__(self):
        super().__init__(
            placeholder="🔊 목소리를 선택하세요!",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=k) for k in VOICE_MAP.keys()],
            custom_id="voice_select_menu"
        )

    async def callback(self, interaction: discord.Interaction):
        cfg = interaction.client.get_cog("TTSCog").cfg
        chosen = self.values[0]

        cfg["user_voice"][str(interaction.user.id)] = chosen
        save_config(cfg)

        print(f"[TTS] Voice Selected: {chosen}")

        await interaction.response.edit_message(
            content=f"목소리가 **{chosen}** 으로 설정되었습니다!",
            view=None
        )


class TTSCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = load_config()

        view = View(timeout=None)
        view.add_item(VoiceSelect())
        bot.add_view(view)

    @app_commands.command(name="목소리", description="TTS 목소리 선택")
    async def voice_cmd(self, interaction):
        await interaction.response.send_message(
            "👇 아래에서 목소리를 선택해 주세요!",
            view=self.bot._views[0],
            ephemeral=True
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
        if not text:
            return

        cfg_voice = self.cfg["user_voice"].get(str(msg.author.id), "여성 A (Google)")
        engine, voice = VOICE_MAP[cfg_voice]

        print(f"[TTS] {engine} | {voice} | {text}")

        ogg = google_tts(text, voice) if engine == "google" else bing_tts(text, voice)

        if ogg:
            if vc.is_playing(): vc.stop()
            vc.play(discord.FFmpegPCMAudio(ogg, before_options="-nostdin -vn", options="-ac 2 -ar 48000"))


async def setup(bot):
    await bot.add_cog(TTSCog(bot))
    print("🔊 TTSCog Loaded (Persistent View Real Fix)")

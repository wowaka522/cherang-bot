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


# ==============================
#   UI 선택 클래스
# ==============================
class VoiceSelect(Select):
    def __init__(self, bot, cfg, user_id):
        self.bot = bot
        self.cfg = cfg
        self.user_id = user_id

        super().__init__(
            placeholder="🔊 목소리 선택하세요!",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=k) for k in VOICE_MAP.keys()]
        )

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        self.cfg["user_voice"][self.user_id] = chosen
        save_config(self.cfg)

        print(f"[TTS] Voice Selected: {chosen}")

        await interaction.response.edit_message(
            content=f"목소리가 **{chosen}** 으로 설정되었어요!",
            view=None
        )


class VoiceView(View):
    def __init__(self, bot, cfg, user_id):
        # 핵심: timeout None + persistent view 작동
        super().__init__(timeout=None)
        self.add_item(VoiceSelect(bot, cfg, user_id))


# ==============================
#   메인 TTS Cog
# ==============================
class TTSCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = load_config()

        # persistent view 등록
        bot.add_view(VoiceView(bot, self.cfg, "PERSIST"))

    # /목소리 명령 UI 호출
    @app_commands.command(name="목소리", description="TTS 목소리 선택")
    async def voice_cmd(self, interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        view = VoiceView(self.bot, self.cfg, user_id)

        await interaction.edit_original_response(
            content="👇 아래에서 목소리를 선택해 주세요!",
            view=view
        )

    # ===== 입장 =====
    @commands.command(name="입장")
    async def cmd_join(self, ctx):
        await self._join(ctx)

    @app_commands.command(name="입장")
    async def slash_join(self, interaction):
        await self._join(interaction)

    async def _join(self, src):
        user = src.user if isinstance(src, discord.Interaction) else src.author
        if not user.voice:
            return await self._send(src, "먼저 음성 채널 들어가!")

        ch = user.voice.channel
        vc = user.guild.voice_client

        if vc:
            await vc.move_to(ch)
        else:
            await ch.connect()

    # ===== 퇴장 =====
    @commands.command(name="퇴장")
    async def cmd_leave(self, ctx):
        await self._leave(ctx)

    @app_commands.command(name="퇴장")
    async def slash_leave(self, inter):
        await self._leave(inter)

    async def _leave(self, src):
        vc = src.guild.voice_client
        if vc:
            await vc.disconnect()

    async def _send(self, src, msg):
        if isinstance(src, discord.Interaction):
            try: await src.response.send_message(msg)
            except: await src.followup.send(msg)
        else:
            await src.send(msg)

    # ===== 메시지 TTS =====
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
    print("🔊 TTSCog Loaded (Persistent View)")

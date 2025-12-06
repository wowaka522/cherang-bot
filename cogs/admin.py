import discord
from discord.ext import commands  # 🔥 이 줄 필요!!!
from discord import app_commands
import asyncio
import subprocess
from pathlib import Path
import os
import tempfile
import shutil

# 여기에 최신 exe URL 설정 (나중에 작성)
LATEST_EXE_URL = ""

ADMINS = []

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="라파엘업데이트", description="Raphael 데이터 자동 업데이트")
    async def update_raphael(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ 관리자만 사용 가능합니다.", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            import requests
        except ImportError:
            return await interaction.followup.send(
                "⚠ requests 라이브러리가 설치되지 않았습니다.\n`pip install requests` 후 다시 시도해 주세요.",
                ephemeral=True,
            )

        from utils.raphael import RAPHAEL_EXE

        tmp_dir = Path(tempfile.mkdtemp())
        tmp_exe = tmp_dir / "raphael-cli.exe"

        try:
            r = requests.get(LATEST_EXE_URL, timeout=30)
            if r.status_code != 200:
                return await interaction.followup.send(
                    f"❌ 다운로드 실패 (status={r.status_code})",
                    ephemeral=True,
                )

            tmp_exe.write_bytes(r.content)
            shutil.copy2(tmp_exe, RAPHAEL_EXE)

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        await interaction.followup.send(
            "✅ raphael-cli.exe 최신 버전으로 교체 완료!",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(AdminCog(bot))

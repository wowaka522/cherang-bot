import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os

ADMINS = [292296682790584320]  # 필요하면 Discord ID 입력


def is_admin(member: discord.Member) -> bool:
    if member.id in ADMINS:
        return True
    return member.guild_permissions.administrator


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="라파엘업데이트",
        description="Raphael 데이터 최신 업데이트 + 봇 자동 재시작"
    )
    async def update_raphael(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            return await interaction.response.send_message(
                "❌ 관리자만 사용할 수 있어!", ephemeral=True
            )

        await interaction.response.send_message(
            "🛠 라파엘 데이터 업데이트 시작...", ephemeral=True
        )

        RAPHAEL_PATH = "/home/wltn5548/cherang-bot/raphael/raphael-rs/raphael-rs"
        COMMAND = f"cd {RAPHAEL_PATH} && git pull"

        process = await asyncio.create_subprocess_shell(
            COMMAND,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            return await interaction.followup.send(
                f"❌ 업데이트 실패!\n```{stderr.decode()}```",
                ephemeral=True,
            )

        await interaction.followup.send(
            "✨ 업데이트 완료! 체랑봇 재시작 중...\n(잠시 후 자동 복귀)", ephemeral=True
        )

        # 🔥 재시작 실행
        restart = await asyncio.create_subprocess_shell(
            "pm2 restart cherang",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        r_out, r_err = await restart.communicate()

        print("PM2 Restart:", r_out.decode(), r_err.decode())

async def setup(bot: commands.Bot):
    pass
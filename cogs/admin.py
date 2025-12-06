import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import subprocess

ADMINS = []  # 필요하면 Discord ID 넣어도 됨


def is_admin(member: discord.Member) -> bool:
    if member.id in ADMINS:
        return True
    return member.guild_permissions.administrator


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="라파엘업데이트", description="Raphael 데이터 최신 업데이트 + 봇 재시작(관리자)")
    async def update_raphael(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            return await interaction.response.send_message(
                "❌ 관리자만 사용할 수 있어!", ephemeral=True
            )

        await interaction.response.send_message(
            "🛠 라파엘 데이터 업데이트 시작...", ephemeral=True
        )

        # 서버에서 update_raphael.bat 실행
        process = await asyncio.create_subprocess_shell(
            r'updater\update_raphael.bat',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            await interaction.followup.send(
                f"❌ 업데이트 실패!\n```{stderr.decode()}```",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            "✅ 업데이트 완료! `pm2 restart cherang` 해줘",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(AdminCog(bot))

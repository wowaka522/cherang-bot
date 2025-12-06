# cogs/help_info.py
import discord
from discord.ext import commands
from discord import app_commands

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="도움말", description="체랑봇 전체 명령어 안내")
    async def help_slash(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📌 체랑봇 명령어 안내",
            description="명령어는 `/` 또는 자연어로 사용할 수 있어!",
            color=0x7BD8FF
        )

        embed.add_field(
            name="💬 자연어 예시",
            value=(
                "냥이야 홍옥색 시세 알려줘\n"
                "체랑아 울다하 날씨 어때?\n"
                "냥이야 나 사랑해?"
            ),
            inline=False
        )

        embed.add_field(
            name="📦 거래 관련",
            value=(
                "`/시세 <아이템>` - 한국 서버 시세 조회\n"
                "예: `/시세 로네크 아교`"
            ),
            inline=False
        )

        embed.add_field(
            name="🌤 날씨",
            value="`/날씨 <지역>` - 지역 기상 확인",
            inline=False
        )

        embed.add_field(
            name="⚙ 제작",
            value=(
                "`/제작 <레시피>` - 제작 매크로 생성\n"
                "`/상태` - 제작 스탯 관리"
            ),
            inline=False
        )

        embed.add_field(
            name="💰 경제 시스템 (! 명령)",
            value=(
                "`!돈` - 잔액 확인\n"
                "`!일하기` - 돈 벌기\n"
                "`!상점` - 상점 보기\n"
                "`!구매 아이템명`\n"
                "`!인벤`\n"
                "`!주기 @유저 금액`\n"
                "`!선물 @유저 아이템`\n"
                "`!도박 금액`"
            ),
            inline=False
        )

        embed.add_field(
            name="❤️ 호감도",
            value="`!호감도` - 체랑이 너를 얼마나 좋아하는지!",
            inline=False
        )

        embed.set_footer(text="✨ 체랑봇과 즐거운 시간 보내! ")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
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
            description="slash 명령어 또는 자연어로 말을 걸어 줘!",
            color=0x7BD8FF
        )

        # 💬 자연어 예시
        embed.add_field(
            name="💬 자연어 예시",
            value=(
                "냥이야 로네크 아교 시세 알려줘\n"
                "체랑아 울다하 날씨 어때?\n"
                "냥… 나랑 얘기 좀 하자"
            ),
            inline=False
        )

        # 📦 거래 관련
        embed.add_field(
            name="📦 거래 관련",
            value="`/시세 <아이템>` - 거래소 시세 조회",
            inline=False
        )

        # 🌤 날씨
        embed.add_field(
            name="🌤 날씨",
            value="`/날씨 <지역>` - 지역 기상 확인",
            inline=False
        )

        # ⚙ 제작 시스템
        embed.add_field(
            name="⚙ 제작 시스템",
            value=(
                "`/제작 <레시피>` - 제작 매크로 생성\n"
                "`/상태` - 제작 스탯 조회/관리"
            ),
            inline=False
        )

        # 💰 게임 콘텐츠
        embed.add_field(
            name="💰 게임 콘텐츠",
            value=(
                "`/도박` - 슬롯 / 바카라 / 블랙잭\n"
                "`!일하기` - 돈 벌기\n"
                "`!상점` - 상점 보기\n"
                "`!인벤` - 인벤토리"
            ),
            inline=False
        )

        # ❤️ 호감도
        embed.add_field(
            name="❤️ 호감도 / 대화",
            value="`/호감도` - 체랑과의 관계 확인 및 말걸기",
            inline=False
        )

        # 🎯 퀘스트
        embed.add_field(
            name="🎯 퀘스트 & 업적",
            value="`/퀘스트` - 일일퀘스트 및 업적 확인",
            inline=False
        )

        # 🔊 TTS 추가 (✨여기에 추가된 부분✨)
        embed.add_field(
            name="🔊 음성 채팅 (TTS)",
            value=(
                "`!입장` - 봇을 음성채널로 불러오기\n"
                "`!퇴장` - 음성채널에서 내보내기\n"
                "`/tts채널 <채널>` - 읽어줄 텍스트 채널 설정\n\n"
                "📌 설정된 채널에서 메시지 → 자동으로 읽어줌!"
            ),
            inline=False
        )

        embed.set_footer(text="✨ 체랑봇과 재밌게 놀아줘!")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))

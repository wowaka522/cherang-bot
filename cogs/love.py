# cogs/love.py
import random
import time

import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction

from utils.user_api import (
    get_user,
    update_user,
    add_love,
    get_user_love,
)

# DeepSeek 대화모드 상태/쿨타임 관리 함수들 (ai_chat 쪽에서 제공)
from cogs.ai_chat import (
    can_start_talk_mode,   # (can, remain_seconds)
    start_talk_mode,       # 대화모드 시작
    is_talk_active,        # 현재 대화모드인지 여부
)

# ==========================
# 호감도 문구
# ==========================

def love_level(score: int) -> str:
    if score >= 70:
        return "💘 완전 최애 장게냥"
    if score >= 40:
        return "💖 친한 장게 친구"
    if score >= 10:
        return "💛 적당히 아는 사이"
    if score > -10:
        return "🤍 그냥 지나가는 모험가"
    if score > -40:
        return "💢 조금 짜증나는 손님"
    return "🖤 장게에서 쫓아내고 싶은 손님"


def make_love_embed(user: discord.Member) -> discord.Embed:
    score = get_user_love(user.id)
    level = love_level(score)
    total_blocks = 20
    filled = int((score + 100) / 200 * total_blocks)
    filled = max(0, min(total_blocks, filled))
    bar = "🟦" * filled + "⬛" * (total_blocks - filled)

    embed = discord.Embed(
        title=f"{user.display_name} ❤️ 체랑봇",
        description=level,
        color=0xFFB7C5,
    )
    embed.add_field(name="호감도", value=f"**{score} / 100**", inline=False)
    embed.add_field(name="관계 게이지", value=bar, inline=False)
    embed.set_footer(text="…딱히 좋아하는 건 아닌데.")
    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)
    return embed


# ==========================
# 버튼 UI
# ==========================

class LoveView(ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

        # 말걸기 모드 활성 중이면 버튼 비활성화
        if is_talk_active(self.user_id):
            for child in self.children:
                if isinstance(child, ui.Button) and child.label == "💬 말걸기":
                    child.disabled = True
                    child.label = "💬 대화 진행 중"

    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("한심… 네 UI 아니잖아.", ephemeral=True)
            return False
        return True

    @ui.button(label="💬 말걸기", style=discord.ButtonStyle.primary)
    async def talk(self, interaction: Interaction, button: ui.Button):
        uid = self.user_id

        # ai_chat 쪽에서 쿨타임/상태 확인
        can, remain = can_start_talk_mode(uid)
        if not can:
            # 남은 시간 표시 (대충 시/분)
            hours = remain // 3600
            minutes = (remain % 3600) // 60
            if hours > 0:
                msg = f"…조금만 기다리라니까. ({hours}시간 {minutes}분 남았어.)"
            elif minutes > 0:
                msg = f"…금방이야. ({minutes}분만 기다려.)"
            else:
                msg = "방금 끝났잖아. 좀 쉬게 해."
            return await interaction.response.send_message(msg, ephemeral=True)

        # 여기서 대화모드 ON (실제 답장은 ai_chat.py가 담당)
        start_talk_mode(uid)

        # 시작 멘트는 로직 고정 쿨데레
        start_lines = [
            "…뭐야. 또 얘기하고 싶은 거야?",
            "할 말 있어? 없으면 끌게.",
            "흥. 잠깐 정도는 들어줄 수는 있지.",
            "바쁜데… 뭐, 딱 10마디까지만.",
        ]
        await interaction.response.send_message(random.choice(start_lines), ephemeral=True)

        # 말걸기 누른 순간, 버튼 비활성화된 UI로 갱신
        embed = make_love_embed(interaction.user)
        view = LoveView(self.user_id)
        try:
            await interaction.message.edit(embed=embed, view=view)
            ephemeral=True
        except:
            pass
        # 원래 /호감도 메시지는 그대로 두고, 새로 열 필요는 없음
        # 굳이 다시 보내진 않음. 필요하면 여기서 편집 가능.

    @ui.button(label="🔁 새로고침", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: Interaction, button: ui.Button):
        embed = make_love_embed(interaction.user)
        # 말걸기 진행 중이면 새로고침 눌러도 버튼은 비활성 상태 유지
        view = LoveView(self.user_id)
        await interaction.response.edit_message(embed=embed, view=view)


# ==========================
# Cog
# ==========================

class LoveCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Slash Command: /호감도
    @app_commands.command(name="호감도", description="체랑과의 관계도를 확인합니다.")
    async def love(self, interaction: Interaction):
        user = interaction.user
        embed = make_love_embed(user)
        await interaction.response.send_message(
            embed=embed,
            view=LoveView(user.id)
        )


async def setup(bot):
    await bot.add_cog(LoveCog(bot))
    print("💗 LoveCog Loaded!")

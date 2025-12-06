# utils/love_embed.py

import discord
from utils.love_db import get_user_love

LOVE_LEVELS = [
    (-100, -20, "…거기 멈춰. 진짜 짜증나거든."),
    (-19, -1, "흥. 나한테 말 걸 생각은 하지도 마."),
    (0, 19, "뭐… 나쁘진 않다."),
    (20, 49, "조금… 친해진 것 같기도 하고."),
    (50, 79, "너랑 얘기하는 거, 싫지 않아."),
    (80, 100, "…넌 특별하니까.")
]

def get_level_text(score: int) -> str:
    for low, high, text in LOVE_LEVELS:
        if low <= score <= high:
            return text
    return "…뭐야, 이거 계산 오류 아냐?"

def make_love_embed(user: discord.abc.User) -> discord.Embed:
    score = get_user_love(str(user.id))
    level = get_level_text(score)

    total_blocks = 20
    filled = int((score + 100) / 200 * total_blocks)
    filled = max(0, min(total_blocks, filled))
    bar = "🟦" * filled + "⬛" * (total_blocks - filled)

    emb = discord.Embed(
        title=f"{user.display_name}와 체랑의 관계",
        description=f"**{level}**",
        color=0xFF91B0
    )
    emb.add_field(name="호감도", value=f"**{score} / 100**", inline=False)
    emb.add_field(name="관계 게이지", value=bar, inline=False)
    emb.set_footer(text="대화 많이 하면… 더 알고 싶어질지도 모르니까.")
    if user.avatar:
        emb.set_thumbnail(url=user.avatar.url)
    return emb

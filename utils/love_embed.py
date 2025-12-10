import discord
from utils.love_db import get_user_love

LOVE_LEVELS = [
    (0, 19, "…그냥 지나가는 모험가"),
    (20, 39, "조금 알 것 같기도?"),
    (40, 59, "흠, 너 괜찮네."),
    (60, 79, "너랑 있는 거… 싫지 않네."),
    (80, 99, "…난 네가 좋아."),
    (100, 9999, "특별해. 아주 많이.")
]

def get_level_text(score: int) -> str:
    for low, high, text in LOVE_LEVELS:
        if low <= score <= high:
            return text
    return "…뭔가 오류났어."

def make_love_embed(user: discord.abc.User) -> discord.Embed:
    score = get_user_love(str(user.id))

    total_blocks = 20
    filled = min(total_blocks, int(score / 100 * total_blocks))
    bar = "🟦" * filled + "⬛" * (total_blocks - filled)

    emb = discord.Embed(
        title=f"{user.display_name} ❤️ 체랑봇",
        description=f"**{get_level_text(score)}**",
        color=0xFF91B0
    )
    emb.add_field(name="호감도", value=f"**{score} / 100**", inline=False)
    emb.add_field(name="관계 게이지", value=bar, inline=False)
    emb.set_footer(text="…딱히 좋아하는 건 아니네.")
    if user.avatar:
        emb.set_thumbnail(url=user.avatar.url)
    return emb

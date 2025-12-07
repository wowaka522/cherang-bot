# cogs/inventory.py

import random
import discord
from discord.ext import commands
from discord import ui, Interaction

from utils.user_api import (
    get_user,
    update_user,
    add_item,
    remove_item,
)

from utils.items_db import (
    get_item_category_by_name,
    is_gear_category,
    get_item_emoji,
    random_gear_name,
    POTION_ITEMS,
    FOOD_ITEMS,
)

# 상점/랜덤박스 쪽에서 쓰는 대표 상자 이름들 타입 매핑
BOX_TYPES = {
    "흑와단 특별 지급 물자함": "gear",
    "별빛축제 선물상자": "potion",
    "체랑의 보물상자": "food",
}

# ------------------------
#   카테고리 판별 헬퍼
# ------------------------

def get_category(item_name: str) -> str:
    """
    인벤 아이템 카테고리 분류
    - box      : 상자/물자함/보물상자 등
    - gear     : 장비류
    - consume  : 음식/약품
    - material : 제작/채집 재료 등 (판매/선물/개봉 X)
    """
    # 이름으로 상자감 먼저 체크
    if "상자" in item_name or "물자함" in item_name or "보물상자" in item_name:
        return "box"

    cat = get_item_category_by_name(item_name) or ""

    # 약품 / 요리 → 소비형
    if cat == "약품" or cat == "요리":
        return "consume"

    # 장비 카테고리
    if cat and is_gear_category(cat):
        return "gear"

    # 재료 느낌 (카테고리 정보 없거나 기타)
    return "material"


def split_inventory(inv: dict[str, int]):
    """
    인벤을 표시용으로 두 그룹으로 나눈다.
    - equip_like: 장비/소비/상자 등 (판매/선물/개봉 대상)
    - materials : 재료 (제작용)
    """
    equip_like = {}
    materials = {}

    for name, cnt in inv.items():
        if cnt <= 0:
            continue
        cat = get_category(name)
        if cat in ("gear", "consume", "box"):
            equip_like[name] = cnt
        else:
            materials[name] = cnt

    return equip_like, materials


# ------------------------
#   상자 개봉 보상
# ------------------------

def reward_from_box(box_name: str) -> str | None:
    box_type = BOX_TYPES.get(box_name)

    if box_type == "gear":
        return random_gear_name()
    if box_type == "potion" and POTION_ITEMS:
        return random.choice(POTION_ITEMS)
    if box_type == "food" and FOOD_ITEMS:
        return random.choice(FOOD_ITEMS)

    # 타입 모르면 그냥 장비 시도 → 실패 시 None
    return random_gear_name()


# ------------------------
#   인벤 메시지 갱신 공통
# ------------------------

async def send_or_update_inventory_message(
    *,
    interaction: Interaction | None = None,
    ctx: commands.Context | None = None,
    user_id: int,
):
    """
    - ctx 가 있으면: 새 메시지로 인벤 표시
    - interaction 이 있으면: 그 메시지를 수정
    """
    data = get_user(user_id)
    inv = data.get("inventory", {})

    if not inv:
        embed = discord.Embed(
            title="🎒 인벤토리",
            description="텅.",
            color=0xAAAAAA,
        )
        if interaction:
            await interaction.response.edit_message(embed=embed, view=None)
        elif ctx:
            await ctx.reply(embed=embed, mention_author=False)
        return

    equip_like, materials = split_inventory(inv)

    desc_lines: list[str] = []

    if equip_like:
        desc_lines.append("**⚔️ 장비 / 소모품 / 상자**")
        for name, cnt in equip_like.items():
            emoji = get_item_emoji(name)
            desc_lines.append(f"{emoji} {name} x{cnt}")

    if materials:
        if desc_lines:
            desc_lines.append("")
        desc_lines.append("**🌿 재료 (판매/선물 불가)**")
        for name, cnt in materials.items():
            emoji = get_item_emoji(name)
            desc_lines.append(f"{emoji} {name} x{cnt}")

    desc = "\n".join(desc_lines) if desc_lines else "…아무것도 없네."

    embed = discord.Embed(
        title="🎒 인벤토리",
        description=desc,
        color=0x3498DB,
    )
    embed.set_footer(text="…이 정도면 인정.")

    view = InventoryView(user_id)

    if interaction:
        await interaction.response.edit_message(embed=embed, view=view)
    elif ctx:
        await ctx.reply(embed=embed, view=view, mention_author=False)


# =====================================================
#   Select & View 정의
# =====================================================

class BoxSelect(ui.Select):
    def __init__(self, user_id: int):
        self.user_id = user_id
        data = get_user(user_id)
        inv = data.get("inventory", {})

        options: list[discord.SelectOption] = []
        for name, cnt in inv.items():
            if cnt <= 0:
                continue
            if get_category(name) == "box":
                options.append(
                    discord.SelectOption(
                        label=name,
                        description=f"{cnt}개 보유",
                    )
                )

        super().__init__(
            placeholder="개봉할 상자를 골라.",
            options=options,
            max_values=1,
        )

    async def callback(self, interaction: Interaction):
        box_name = self.values[0]
        user_id = self.user_id

        # 상자 1개 제거
        if not remove_item(user_id, box_name, 1):
            return await interaction.response.send_message("상자가 없는데?", ephemeral=True)

        reward_name = reward_from_box(box_name)
        if reward_name:
            add_item(user_id, reward_name, 1)
            emoji = get_item_emoji(reward_name)
            desc = f"{box_name}을(를) 열었다.\n→ {emoji} **{reward_name}** 획득!"
        else:
            desc = f"{box_name}을(를) 열긴 했는데… 아무것도 없었다."

        embed = discord.Embed(
            title="📦 개봉 완료",
            description=desc,
            color=0xFFD700,
        )
        embed.set_footer(text="또 열 거야? …알아서 해.")

        await interaction.response.send_message(embed=embed)
        # 인벤 메시지 갱신 (원래 인벤 메시지)
        try:
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=None,
                view=InventoryView(user_id),
            )
        except Exception:
            # 원본 메시지 수정 실패하면 무시
            pass


class SellSelect(ui.Select):
    def __init__(self, user_id: int):
        self.user_id = user_id
        data = get_user(user_id)
        inv = data.get("inventory", {})

        options: list[discord.SelectOption] = []
        for name, cnt in inv.items():
            if cnt <= 0:
                continue
            cat = get_category(name)
            # 재료 / 상자는 판매 X, 장비/소모품만
            if cat in ("gear", "consume"):
                options.append(
                    discord.SelectOption(
                        label=name,
                        description=f"{cnt}개 보유",
                    )
                )

        super().__init__(
            placeholder="팔 아이템을 골라.",
            options=options,
            max_values=1,
        )

    async def callback(self, interaction: Interaction):
        item_name = self.values[0]
        user_id = self.user_id

        if not remove_item(user_id, item_name, 1):
            return await interaction.response.send_message("그거 없는데?", ephemeral=True)

        data = get_user(user_id)
        money = data.get("money", 0)

        # TODO: 나중에 KR_DETAIL에서 실제 상점가 가져와서 50% 계산
        base_price = 100  # 임시 상점가
        sell_price = base_price // 2

        money += sell_price
        data["money"] = money
        update_user(user_id, data)

        embed = discord.Embed(
            title="💰 판매 완료",
            description=f"{item_name}을(를) **{sell_price} 길**에 팔았다.\n현재 소지금: {money} 길",
            color=0x55FFAA,
        )
        embed.set_footer(text="현명한 선택… 이라고 해둘게.")

        await interaction.response.send_message(embed=embed)
        try:
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                view=InventoryView(user_id),
            )
        except Exception:
            pass


class GiftSelect(ui.Select):
    def __init__(self, user_id: int):
        self.user_id = user_id
        data = get_user(user_id)
        inv = data.get("inventory", {})

        options: list[discord.SelectOption] = []
        for name, cnt in inv.items():
            if cnt <= 0:
                continue
            cat = get_category(name)
            # 재료/상자는 선물 X, 장비/소모품만
            if cat in ("gear", "consume"):
                options.append(
                    discord.SelectOption(
                        label=name,
                        description=f"{cnt}개 보유",
                    )
                )

        super().__init__(
            placeholder="체랑에게 줄 선물을 골라.",
            options=options,
            max_values=1,
        )

    async def callback(self, interaction: Interaction):
        item_name = self.values[0]
        user_id = self.user_id

        if not remove_item(user_id, item_name, 1):
            return await interaction.response.send_message("그거 없는데?", ephemeral=True)

        # 필요하면 여기서 봇 인벤에 추가도 가능
        # add_item("bot", item_name, 1)

        embed = discord.Embed(
            title="🎁 선물",
            description=f"체랑에게 **{item_name}** 을(를) 건넸다.\n…뭐, 고맙다.",
            color=0xFF88DD,
        )
        embed.set_footer(text="(작게) 고맙다냥…")

        await interaction.response.send_message(embed=embed)
        try:
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                view=InventoryView(user_id),
            )
        except Exception:
            pass


class InventoryView(ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "네 인벤이 아니잖아.", ephemeral=True
            )
            return False
        return True

    @ui.button(label="📦 개봉", style=discord.ButtonStyle.primary)
    async def btn_open(self, interaction: Interaction, button: ui.Button):
        data = get_user(self.user_id)
        inv = data.get("inventory", {})
        has_box = any(
            cnt > 0 and get_category(name) == "box"
            for name, cnt in inv.items()
        )
        if not has_box:
            return await interaction.response.send_message("열 상자가 없는데?", ephemeral=True)

        view = ui.View(timeout=60)
        view.add_item(BoxSelect(self.user_id))

        embed = discord.Embed(
            title="📦 어떤 상자를 열까?",
            color=0xFFD700,
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @ui.button(label="💰 판매", style=discord.ButtonStyle.success)
    async def btn_sell(self, interaction: Interaction, button: ui.Button):
        data = get_user(self.user_id)
        inv = data.get("inventory", {})
        has_sell = any(
            cnt > 0 and get_category(name) in ("gear", "consume")
            for name, cnt in inv.items()
        )
        if not has_sell:
            return await interaction.response.send_message("팔 게 없는데?", ephemeral=True)

        view = ui.View(timeout=60)
        view.add_item(SellSelect(self.user_id))

        embed = discord.Embed(
            title="💰 뭘 팔 건데?",
            color=0x55FFAA,
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @ui.button(label="🎁 선물", style=discord.ButtonStyle.secondary)
    async def btn_gift(self, interaction: Interaction, button: ui.Button):
        data = get_user(self.user_id)
        inv = data.get("inventory", {})
        has_gift = any(
            cnt > 0 and get_category(name) in ("gear", "consume")
            for name, cnt in inv.items()
        )
        if not has_gift:
            return await interaction.response.send_message("줄 만한 건 없네.", ephemeral=True)

        view = ui.View(timeout=60)
        view.add_item(GiftSelect(self.user_id))

        embed = discord.Embed(
            title="🎁 뭘 줄래?",
            color=0xFF88DD,
        )
        await interaction.response.edit_message(embed=embed, view=view)


# =====================================================
#   Cog
# =====================================================

class InventoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="인벤")
    async def inv(self, ctx: commands.Context):
        user_id = ctx.author.id
        await send_or_update_inventory_message(ctx=ctx, user_id=user_id)


async def setup(bot):
    await bot.add_cog(InventoryCog(bot))
    print("📦 InventoryCog Loaded!")

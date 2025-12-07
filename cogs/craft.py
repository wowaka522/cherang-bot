# cogs/craft.py

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
    random_gear_name,
    get_item_emoji,
)

# ===== 생활 / 제작 아이템 =====

GATHER_ITEMS = [
    "에테르 모래", "기름씨앗", "검은밀", "새알", "계피",
    "찻잎", "이페나무 원목", "티타늄 광석", "물", "뜰냉이", "섬전암"
]

CRAFT_RECIPES = {
    # 1차 재료
    "휘핑크림": {"기름씨앗": 3},
    "검은밀가루": {"검은밀": 1},
    "보석수": {"섬전암": 1, "물": 1, "에테르 모래": 1, "뜰냉이": 1},
    "티타늄 덩어리": {"티타늄 광석": 3},
    "이페나무 목재": {"이페나무 원목": 3},

    # 2차 완제품
    "고급 마테차 쿠키": {
        "휘핑크림": 1, "검은밀가루": 1, "에테르 모래": 1, "새알": 1
    },
    "장비 제작": {
        "보석수": 1, "티타늄 덩어리": 1, "이페나무 목재": 1
    },
}


# ==============================
#   내부 헬퍼
# ==============================

def get_inventory(user_id: int) -> dict:
    data = get_user(user_id)
    inv = data.get("inventory", {})
    if not isinstance(inv, dict):
        inv = {}
        data["inventory"] = inv
        update_user(user_id, data)
    return inv


def can_craft_product(user_id: int, product: str) -> bool:
    """해당 유저가 product를 제작할 수 있는지 (재료 충분?)"""
    if product not in CRAFT_RECIPES:
        return False

    inv = get_inventory(user_id)
    mats = CRAFT_RECIPES[product]
    for mat, cnt in mats.items():
        if inv.get(mat, 0) < cnt:
            return False
    return True


def build_recipe_detail_text(user_id: int, product: str) -> str:
    """재료 ✔/❌ 포함 상세 텍스트"""
    inv = get_inventory(user_id)
    mats = CRAFT_RECIPES[product]
    lines = []
    for mat, cnt in mats.items():
        have = inv.get(mat, 0)
        mark = "✔" if have >= cnt else "❌"
        lines.append(f"{mark} {mat} — 필요 {cnt}개 / 보유 {have}개")
    return "\n".join(lines)


async def do_craft(user_id: int, product: str, interaction: Interaction):
    """실제 제작 처리 로직"""

    if product not in CRAFT_RECIPES:
        return await interaction.response.send_message("그건 만들 줄 몰라.", ephemeral=True)

    # 재료 충분한지 재검사
    if not can_craft_product(user_id, product):
        text = f"{product} 제작에 필요한 재료가 부족해."
        return await interaction.response.send_message(text, ephemeral=True)

    mats = CRAFT_RECIPES[product]

    # 재료 소모
    for mat, cnt in mats.items():
        if not remove_item(user_id, mat, cnt):
            # 이론상 안 나와야 함
            return await interaction.response.send_message(
                f"{mat} 재고가 모자라. 다시 시도해봐.",
                ephemeral=True,
            )

    # 결과 아이템 처리
    desc = ""
    if product == "장비 제작":
        item_name = random_gear_name()
        if not item_name:
            return await interaction.response.send_message(
                "장비 DB 오류… 나중에 다시 시도해.",
                ephemeral=True,
            )
        add_item(user_id, item_name, 1)
        emoji = get_item_emoji(item_name)
        desc = f"⚔️ **{item_name}** 제작 성공!"
    elif product == "고급 마테차 쿠키":
        # 실제 DB에 있는 요리 → 이름 그대로 지급
        add_item(user_id, product, 1)
        emoji = get_item_emoji(product)
        desc = f"{emoji} **{product}** 제작 성공!"
    else:
        # 1차 재료 등 — 재료 취급 (판매/선물 X, 제작 재료용)
        add_item(user_id, product, 1)
        emoji = get_item_emoji(product)
        desc = f"{emoji} **{product}** 제작 성공!"

    embed = discord.Embed(
        title="제작 완료!",
        description=desc,
        color=0x88AAFF,
    )
    embed.set_footer(text="…이 정도면 인정.")

    # 메시지 내용만 바꾸고, 버튼은 제거
    await interaction.response.edit_message(embed=embed, view=None)


# ==============================
#   UI 컴포넌트
# ==============================

class CraftSelect(ui.Select):
    def __init__(self, user_id: int):
        self.user_id = user_id

        options = []
        for product in CRAFT_RECIPES.keys():
            if can_craft_product(user_id, product):
                options.append(
                    discord.SelectOption(
                        label=product,
                        description="재료 충분."
                    )
                )

        if not options:
            # 옵션이 없으면 이 Select는 사용되지 않게 해야 함
            options = [
                discord.SelectOption(
                    label="제작 가능 항목 없음",
                    description="재료가 부족해.",
                    default=True,
                )
            ]

        super().__init__(
            placeholder="만들 아이템을 골라.",
            options=options,
            max_values=1,
        )

    async def callback(self, interaction: Interaction):
        product = self.values[0]
        if product not in CRAFT_RECIPES:
            return await interaction.response.send_message(
                "그건 못 만들어.", ephemeral=True
            )

        await do_craft(self.user_id, product, interaction)


class CraftMenuView(ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "네 제작 메뉴 아니야.", ephemeral=True
            )
            return False
        return True

    @ui.button(label="🧱 제작하기", style=discord.ButtonStyle.primary)
    async def btn_craft(self, interaction: Interaction, button: ui.Button):
        # 제작 가능한 레시피가 있는지 확인
        craftable = [
            p for p in CRAFT_RECIPES.keys()
            if can_craft_product(self.user_id, p)
        ]

        if not craftable:
            return await interaction.response.send_message(
                "지금 당장은 만들 수 있는 게 없어. 재료부터 모아와.",
                ephemeral=True,
            )

        view = ui.View(timeout=60)
        view.add_item(CraftSelect(self.user_id))

        embed = discord.Embed(
            title="🧱 제작 가능 목록",
            description="만들 아이템을 하나 골라.",
            color=0x88AAFF,
        )

        await interaction.response.edit_message(embed=embed, view=view)

    @ui.button(label="📘 레시피 보기", style=discord.ButtonStyle.secondary)
    async def btn_recipes(self, interaction: Interaction, button: ui.Button):
        uid = self.user_id
        embed = discord.Embed(
            title="📘 제작 가능 레시피",
            color=0x88AAFF,
        )

        for product, mats in CRAFT_RECIPES.items():
            desc = build_recipe_detail_text(uid, product)
            embed.add_field(
                name=f"🛠 {product}",
                value=desc or "재료 없음",
                inline=False,
            )

        embed.set_footer(text="!레시피 <아이템명> 으로도 개별 확인 가능.")
        await interaction.response.edit_message(embed=embed, view=self)


# ==============================
#   Cog
# ==============================

class CraftCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # !제작 → 메뉴 UI
    @commands.command(name="제작")
    async def cmd_craft_menu(self, ctx: commands.Context):
        uid = ctx.author.id

        embed = discord.Embed(
            title="🛠 제작 메뉴",
            description="뭐 할래?\n\n🧱 제작하기 — 재료로 아이템 제작\n📘 레시피 보기 — 필요한 재료 확인",
            color=0x88AAFF,
        )
        embed.set_footer(text="재료가 없으면… 뭐, 일부터 해야지.")

        view = CraftMenuView(uid)
        await ctx.reply(embed=embed, view=view, mention_author=False)

    # !레시피 [아이템명]
    @commands.command(name="레시피")
    async def cmd_recipe(self, ctx: commands.Context, *, product: str = None):
        uid = ctx.author.id

        if not product:
            # 전체 레시피 목록 간단 출력
            embed = discord.Embed(
                title="📘 제작 가능 레시피 목록",
                description="\n".join([f"🛠 {name}" for name in CRAFT_RECIPES.keys()]),
                color=0x88AAFF,
            )
            embed.set_footer(text="!레시피 <아이템명> 으로 상세 확인 가능.")
            return await ctx.reply(embed=embed, mention_author=False)

        if product not in CRAFT_RECIPES:
            return await ctx.reply("그건 만들 수 없는 듯한데…?", mention_author=False)

        desc = build_recipe_detail_text(uid, product)
        embed = discord.Embed(
            title=f"📘 레시피 — {product}",
            description=desc,
            color=0x88AAFF,
        )
        embed.set_footer(text=f"!제작 으로 제작 메뉴를 열 수 있어.")
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot):
    await bot.add_cog(CraftCog(bot))
    print("🛠 CraftCog Loaded!")

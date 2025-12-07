# cogs/shop.py

import random
import discord
from discord.ext import commands
from discord import ui, Interaction

from utils.user_api import (
    get_user,
    update_user,
    add_item,
)

from utils.items_db import (
    random_gear_name,
    get_item_emoji,
    POTION_ITEMS,
    FOOD_ITEMS,
)

# ============================= #
#   Persistent View 선언 최상단  #
# ============================= #

class PersistentOpenBoxView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)


# ============================= #
#           상점 DB             #
# ============================= #

SHOP_BOXES = {
    "흑와단 특별 지급 물자함": {
        "price": 3000,
        "type": "gear",
    },
    "별빛축제 선물상자": {
        "price": 1500,
        "type": "potion",
    },
    "체랑의 보물상자": {
        "price": 1200,
        "type": "food",
    },
}


# ============================= #
#          랜덤 보상 처리        #
# ============================= #

def grant_reward(box_type: str):
    if box_type == "gear":
        return random_gear_name()
    if box_type == "potion":
        return random.choice(POTION_ITEMS)
    if box_type == "food":
        return random.choice(FOOD_ITEMS)
    return None


# ============================= #
#           개봉 버튼           #
# ============================= #

class OpenBoxButton(ui.Button):
    def __init__(self, user_id: int, box_name: str):
        super().__init__(label="📦 바로 개봉", style=discord.ButtonStyle.primary)
        self.user_id = user_id
        self.box_name = box_name

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("이건 그 사람 전용이야.", ephemeral=True)

        data = get_user(self.user_id)
        inv = data.get("inventory", {})

        if inv.get(self.box_name, 0) <= 0:
            return await interaction.response.send_message("상자가 없어.", ephemeral=True)

        # 개봉 → 상자 1개 소모
        inv[self.box_name] -= 1
        if inv[self.box_name] <= 0:
            del inv[self.box_name]
        data["inventory"] = inv
        update_user(self.user_id, data)

        # 보상 지급
        box_type = SHOP_BOXES[self.box_name]["type"]
        reward = grant_reward(box_type)
        add_item(self.user_id, reward)

        emoji = get_item_emoji(reward)

        embed = discord.Embed(
            title="🎁 개봉 결과",
            description=f"{self.box_name} 개봉!\n→ {emoji} **{reward}** 획득!",
            color=0xFFD700,
        )
        embed.set_footer(text="…기대는 안 했는데. 뭐, 잘 나왔네?")

        await interaction.response.send_message(embed=embed)


# ============================= #
#         아이템 선택창         #
# ============================= #

class BuySelect(ui.Select):
    def __init__(self, user_id: int):
        self.user_id = user_id
        opts = []

        for name, info in SHOP_BOXES.items():
            opts.append(
                discord.SelectOption(
                    label=name,
                    description=f"{info['price']} 길"
                )
            )

        super().__init__(
            placeholder="뭘 살래?",
            options=opts,
            max_values=1,
        )

    async def callback(self, interaction: Interaction):
        uid = self.user_id
        choice = self.values[0]
        price = SHOP_BOXES[choice]["price"]

        data = get_user(uid)
        money = data.get("money", 0)

        if money < price:
            return await interaction.response.send_message(
                f"{price} 길 부족. 돈 좀 벌고 와.",
                ephemeral=True,
            )

        # 구매 처리
        data["money"] -= price
        update_user(uid, data)
        add_item(uid, choice)

        embed = discord.Embed(
            title="🛒 구매 완료",
            description=f"{choice} 구입 완료!\n💰 현재 잔액: {data['money']} 길",
            color=0x55FFAA,
        )
        embed.set_footer(text="돈 쓰는 건 또 빠르네.")

        # 개봉 버튼 표시
        view = PersistentOpenBoxView()
        view.add_item(OpenBoxButton(uid, choice))

        await interaction.response.edit_message(embed=embed, view=view)


# ============================= #
#           상점 View           #
# ============================= #

class ShopView(ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id

    async def interaction_check(self, interaction: Interaction):
        return interaction.user.id == self.user_id

    @ui.button(label="🛒 구매", style=discord.ButtonStyle.success)
    async def buy_btn(self, interaction: Interaction, button: ui.Button):
        view = PersistentOpenBoxView()
        view.add_item(BuySelect(self.user_id))

        await interaction.response.edit_message(
            embed=discord.Embed(title="🛒 무엇을 살래?", color=0x55FFAA),
            view=view
        )


# ============================= #
#              Cog              #
# ============================= #

class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(PersistentOpenBoxView())  # Persistent 등록

    @commands.command(name="상점")
    async def shop(self, ctx: commands.Context):
        uid = ctx.author.id
        money = get_user(uid).get("money", 0)

        lines = []
        for name, info in SHOP_BOXES.items():
            lines.append(f"{get_item_emoji(name)} **{name}** — {info['price']} 길")

        embed = discord.Embed(
            title="🛒 상점",
            description="\n".join(lines) + f"\n\n💰 소지금: {money} 길",
            color=0x3498DB,
        )
        embed.set_footer(text="또 왔어? …구경해나 보지.")

        await ctx.reply(
            embed=embed,
            view=ShopView(uid),
            mention_author=False
        )


async def setup(bot):
    await bot.add_cog(ShopCog(bot))
    print("🛒 ShopCog Loaded!")

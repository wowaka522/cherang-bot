# cogs/economy.py

import os
import random
import discord
from discord.ext import commands

from utils.user_api import (
    add_money,
    get_user,
    update_user,
    add_item,
)

OWNER_ID = int(os.getenv("OWNER_ID", "0"))


JOBS = [
    ("길거리에서 춤춰 벌었다", 20, 35),
    ("누가 팁으로 던져줬다", 10, 25),
    ("기적적으로 돈을 주웠다", 30, 50),
    ("고양이 귀 만져보기 체험 알바", 15, 40),
]

SHOP_ITEMS = {
    "고양이 캔": 50,
    "따끈한 쿠키": 30,
    "고급 깃털": 120,
    "포션": 100,
}


class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 💰 잔액 확인
    @commands.command(name="돈")
    async def money(self, ctx):
        data = get_user(ctx.author.id)
        money = data.get("money", 0)
        await ctx.reply(f"네 지갑에 {money} 길.", mention_author=False)

    # 🧹 일하기
    @commands.command(name="일하기")
    async def work(self, ctx):
        job, mn, mx = random.choice(JOBS)
        pay = random.randint(mn, mx)
        total = add_money(ctx.author.id, pay)
        await ctx.reply(f"{job}… {pay} 길 벌어왔어. (총 {total} 길)", mention_author=False)

    # 🎁 선물
    @commands.command(name="선물")
    async def gift(self, ctx, 대상: discord.Member, *, 아이템: str):
        giver = ctx.author.id
        receiver = 대상.id

        data = get_user(giver)
        inv = data.get("inventory", {})

        if 아이템 not in inv or inv[아이템] <= 0:
            return await ctx.reply("거짓말 하지 마. 그거 없잖아.", mention_author=False)

        inv[아이템] -= 1
        update_user(giver, data)
        add_item(receiver, 아이템)

        love_change = +2 if receiver == OWNER_ID else +1
        await ctx.reply(
            f"{대상.display_name}에게 {아이템} 선물... 뭐, 좋을지도?\n(호감도 +{love_change})",
            mention_author=False
        )

    # 💸 돈 주기
    @commands.command(name="주기")
    async def give_money(self, ctx, 대상: discord.Member, 금액: int):
        if 금액 <= 0:
            return await ctx.reply("장난해?", mention_author=False)

        uid = ctx.author.id
        recv = 대상.id

        data = get_user(uid)
        if data["money"] < 금액:
            return await ctx.reply("가진 것도 없으면서.", mention_author=False)

        data["money"] -= 금액
        update_user(uid, data)

        add_money(recv, 금액)
        await ctx.reply(f"{대상.display_name}에게 {금액} 길 줬어.", mention_author=False)

    # 🎒 인벤토리
    @commands.command(name="인벤")
    async def inv(self, ctx):
        data = get_user(ctx.author.id)
        inv = data.get("inventory", {})

        if not inv:
            return await ctx.reply("텅 비었네.", mention_author=False)

        text = "\n".join(f"- {k} x{v}" for k, v in inv.items())
        await ctx.reply(f"네 가방에서 뒤적뒤적…\n{text}", mention_author=False)

    # 🛒 상점
    @commands.command(name="상점")
    async def shop(self, ctx):
        text = "\n".join(f"- {k} : {v} 길" for k, v in SHOP_ITEMS.items())
        await ctx.reply(f"팔리는 물건들:\n{text}", mention_author=False)

    # 🛍️ 구매
    @commands.command(name="구매")
    async def buy(self, ctx, *, 아이템: str):
        if 아이템 not in SHOP_ITEMS:
            return await ctx.reply("그딴 거 안 팔아.", mention_author=False)

        price = SHOP_ITEMS[아이템]
        data = get_user(ctx.author.id)

        if data["money"] < price:
            return await ctx.reply("가난한 주제에.", mention_author=False)

        data["money"] -= price
        add_item(ctx.author.id, 아이템)
        update_user(ctx.author.id, data)

        await ctx.reply(f"{아이템} 샀다. 만족해?", mention_author=False)

    # 🎲 도박
    @commands.command(name="도박")
    async def gamble(self, ctx, 금액: int):
        data = get_user(ctx.author.id)

        if data["money"] < 금액:
            return await ctx.reply("돈도 없으면서?", mention_author=False)

        if random.random() > 0.50:
            data["money"] += 금액
            result = "이겨서"
        else:
            data["money"] -= 금액
            result = "져서"

        update_user(ctx.author.id, data)
        await ctx.reply(f"{result} 총 {data['money']} 길이야.", mention_author=False)


async def setup(bot):
    await bot.add_cog(EconomyCog(bot))

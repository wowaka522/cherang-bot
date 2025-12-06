import discord
from discord import app_commands, Embed
from discord.ext import commands

from utils.market_data import (
    KR_ICONS,
    KR_DETAIL,
    get_price,
    build_history_chart,
    format_price,
)
from utils.search_improved import search_item
from utils.text_cleaner import extract_item_name


# 한국 서버 월드 ID
KR_WORLDS = {
    "모그리": 2077,
    "초코보": 2076,
    "카벙클": 2075,
    "톤베리": 2078,
    "펜리르": 2080,
}


class MarketCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ======================
    # Slash 응답 전용 (완전 안전 & UI 유지)
    # ======================
    async def _send_slash(
        self,
        interaction: discord.Interaction,
        embed: discord.Embed,
        file: discord.File | None = None,
        view: discord.ui.View | None = None,
    ):
        try:
            kwargs = {
                "embed": embed,
                "ephemeral": False,
            }

            if file:
                kwargs["file"] = file
            if view:
                kwargs["view"] = view

            await interaction.followup.send(**kwargs)

        except Exception as e:
            print(f"[Slash Send Error] {e}")
            try:
                await interaction.followup.send(embed=embed)
            except:
                pass


    # ======================
    # 자연어 응답 (문자 메시지)
    # ======================
    async def _send_msg(
        self,
        msg: discord.Message,
        embed: discord.Embed,
        file: discord.File | None = None,
        view: discord.ui.View | None = None,
    ):
        sent = await msg.reply(
            embed=embed,
            view=view if view else None,
            mention_author=False,
        )

        if file:
            await msg.reply(
                file=file,
                mention_author=False,
            )

        return sent

    # ======================
    # /시세 커맨드
    # ======================
    @app_commands.command(
        name="시세",
        description="한국 서버 FF14 아이템 시세 조회",
    )
    async def price_cmd(self, interaction: discord.Interaction, 아이템이름: str):
        await interaction.response.defer(thinking=True)

        item_name = extract_item_name(아이템이름)
        embed, file, view, error = self.build_price_view(item_name)

        if error:
            return await interaction.followup.send(error, ephemeral=True)

        await self._send_slash(interaction, embed, file, view)

    # ======================
    # 자연어 시세 (명령 아닌 경우)
    # ======================
    async def search_and_reply(self, msg: discord.Message, *_):
        item_name = extract_item_name(msg.content)
        embed, file, view, error = self.build_price_view(item_name)

        if error:
            return await msg.reply(error, mention_author=False)

        await self._send_msg(msg, embed, file, view)

    # ======================
    # Embed + 그래프 + 버튼 생성
    # ======================
    def build_price_view(self, item_name: str):
        item_id, real_name, similar = search_item(item_name)

        if not item_id:
            return None, None, None, f"❌ '{item_name}'과 비슷한 아이템을 찾지 못했어."

        embed = Embed(
            title=real_name,
            description="🇰🇷 한국 서버 시세",
            color=0xFFD700,
        )

        icon = KR_ICONS.get(str(item_id))
        if icon:
            embed.set_thumbnail(
                url="https://xivapi.com/"
                + icon.replace("ui/icon/", "i/").replace(".tex", ".png")
            )

        det = KR_DETAIL.get(str(item_id), {})
        desc = det.get("desc", "") or "설명이 없어요."

        embed.add_field(
            name="📄 설명",
            value=(desc[:250] + "…") if len(desc) > 250 else desc,
            inline=False,
        )
        embed.add_field(
            name="📂 카테고리",
            value=det.get("category", "???"),
            inline=False,
        )

        # 월드별 최저가
        prices = []
        for server_name, world_id in KR_WORLDS.items():
            data = get_price(world_id, item_id)
            hq = nq = None

            if data and data.get("listings"):
                for it in data["listings"]:
                    price = it.get("pricePerUnit")
                    if price is None:
                        continue
                    if it.get("hq"):
                        hq = min(hq, price) if hq is not None else price
                    else:
                        nq = min(nq, price) if nq is not None else price

            prices.append({"server": server_name, "hq": hq, "nq": nq, "wid": world_id})

        # 시세 출력
        for p in prices:
            lines = []
            if p["hq"] is not None:
                lines.append(f"✨ HQ: **{format_price(p['hq'])}**")
            if p["nq"] is not None:
                lines.append(f"💰 NQ: {format_price(p['nq'])}")

            embed.add_field(
                name=p["server"],
                value="\n".join(lines) if lines else "❌ 매물 없음",
                inline=False,
            )

        # 그래프 생성
        file = None
        ref = next((p for p in prices if p["hq"] or p["nq"]), None)
        if ref:
            buf = build_history_chart(ref["server"], ref["wid"], item_id)
            if buf:
                file = discord.File(buf, filename="chart.png")
                embed.set_image(url="attachment://chart.png")
                embed.set_footer(text=f"그래프: {ref['server']} 최근 7일")

        # 비슷한 아이템 버튼
        view = None
        if similar:
            view = discord.ui.View()
            for name in similar[:10]:
                view.add_item(SimilarButton(name, self))

        return embed, file, view, None


class SimilarButton(discord.ui.Button):
    def __init__(self, name: str, cog: MarketCog):
        super().__init__(label=name, style=discord.ButtonStyle.secondary)
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        embed, file, view, error = self.cog.build_price_view(self.label)

        if error:
            return await interaction.followup.send(error, ephemeral=True)

        await interaction.edit_original_response(
            embed=embed,
            attachments=[file] if file else [],
            view=view,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(MarketCog(bot))
    print("✨ MarketCog Loaded!")

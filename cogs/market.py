# cogs/market.py
import discord
from discord import app_commands, Embed
from discord.ext import commands

from utils.market_data import (
    KR_ICONS, KR_DETAIL,
    get_price, build_history_chart, format_price
)
from utils.search_improved import search_item
from utils.text_cleaner import extract_item_name


KR_WORLDS = {
    "모그리": 2077,
    "초코보": 2076,
    "카벙클": 2075,
    "톤베리": 2078,
    "펜리르": 2080,
}


class MarketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Slash 호출 전용 응답
    async def _send_slash(self, interaction, embed, file, view):
        try:
            return await interaction.followup.send(
                embed=embed,
                file=file if file else None,
                view=view if view else None,
                ephemeral=False
            )
        except Exception:
            return await interaction.response.send_message(embed=embed)

    # 자연어 전용 응답
    async def _send_msg(self, msg, embed, file, view):
        return await msg.reply(
            embed=embed,
            file=file if file else None,
            view=view if view else None,
            mention_author=False
        )

    # ======================
    # /시세
    # ======================
    @app_commands.command(name="시세", description="한국 서버 FF14 아이템 시세 조회")
    async def price_cmd(self, interaction: discord.Interaction, 아이템이름: str):
        await interaction.response.defer(thinking=True)
        item_name = extract_item_name(아이템이름)
        embed, file, view, error = self.build_price_view(item_name)

        if error:
            return await interaction.followup.send(error, ephemeral=True)

        await self._send_slash(interaction, embed, file, view)

    # ======================
    # 자연어 시세
    # ======================
    async def search_and_reply(self, msg: discord.Message, *_):
        item_name = extract_item_name(msg.content)
        embed, file, view, error = self.build_price_view(item_name)

        if error:
            return await msg.reply(error, mention_author=False)

        await self._send_msg(msg, embed, file, view)

    # ======================
    # Embed + 파일 + 버튼 생성
    # ======================
    def build_price_view(self, item_name: str):
        item_id, real_name, similar = search_item(item_name)

        if not item_id:
            return None, None, None, f"❌ '{item_name}'과 비슷한 아이템을 찾지 못했어."

        embed = Embed(title=real_name, description="🇰🇷 한국 서버 시세", color=0xFFD700)

        icon = KR_ICONS.get(str(item_id))
        if icon:
            embed.set_thumbnail(
                url="https://xivapi.com/" + icon.replace("ui/icon/", "i/").replace(".tex", ".png")
            )

        det = KR_DETAIL.get(str(item_id), {})
        desc = det.get("desc", "")
        embed.add_field(
            name="📄 설명",
            value=(desc[:250] + "…") if len(desc) > 250 else desc or "정보 없음",
            inline=False
        )
        embed.add_field(
            name="📂 카테고리",
            value=det.get("category", "???"),
            inline=False
        )

        prices = []
        for s, wid in KR_WORLDS.items():
            data = get_price(wid, item_id)
            hq = nq = None
            if data and data.get("listings"):
                for it in data["listings"]:
                    price = it.get("pricePerUnit")
                    if price is None: continue
                    if it.get("hq"): hq = min(hq, price) if hq else price
                    else: nq = min(nq, price) if nq else price
            prices.append({"server": s, "hq": hq, "nq": nq, "wid": wid})

        for p in prices:
            lines = []
            if p["hq"]: lines.append(f"✨ HQ: **{format_price(p['hq'])}**")
            if p["nq"]: lines.append(f"💰 NQ: {format_price(p['nq'])}")
            embed.add_field(
                name=p["server"],
                value="\n".join(lines) if lines else "❌ 없음",
                inline=False
            )

        file = None
        ref = next((p for p in prices if p["hq"] or p["nq"]), None)
        if ref:
            buf = build_history_chart(ref["server"], ref["wid"], item_id)
            if buf:
                file = discord.File(buf, filename="chart.png")
                embed.set_image(url="attachment://chart.png")
                embed.set_footer(text=f"그래프: {ref['server']} 최근 7일")

        view = None
        if similar:
            view = discord.ui.View()
            for name in similar[:10]:
                view.add_item(SimilarButton(name, self))

        return embed, file, view, None


class SimilarButton(discord.ui.Button):
    def __init__(self, name, cog):
        super().__init__(label=name, style=discord.ButtonStyle.secondary)
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        embed, file, view, error = self.cog.build_price_view(self.label)
        if error:
            return await interaction.followup.send(error)

        await interaction.edit_original_response(
            embed=embed,
            attachments=[file] if file else [],
            view=view,
        )


async def setup(bot):
    await bot.add_cog(MarketCog(bot))
    print("✨ MarketCog Loaded!")
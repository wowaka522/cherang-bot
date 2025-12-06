# cogs/market.py
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
    # 공통: Slash용 응답 (defer 전용 안전 버전)
    # ======================
    async def _send_slash(
        self,
        interaction: discord.Interaction,
        embed: discord.Embed,
        file: discord.File | None = None,
        view: discord.ui.View | None = None,
    ):
        """
        슬래시 명령 전용 응답:
        - defer() 호출 이후 반드시 followup.send()만 사용!
        - 중복 response 방지
        """
        try:
            # Embed + 버튼 먼저
            await interaction.followup.send(
                embed=embed,
                view=view if view else None,
                ephemeral=False,
            )

            # 파일은 따로 followup 전송
            if file:
                await interaction.followup.send(file=file)

        except Exception as e:
            print(f"[Slash Send Error] {e}")
            # fallback: 그래도 최소 embed라도 보내기
            try:
                await interaction.followup.send(embed=embed)
            except:
                pass


    # ======================
    # 공통: 자연어용 응답
    # ======================
    async def _send_msg(
        self,
        msg: discord.Message,
        embed: discord.Embed,
        file: discord.File | None = None,
        view: discord.ui.View | None = None,
    ):
        """
        일반 채팅(자연어)용 응답:
        - 먼저 embed + 버튼
        - 그 다음 파일(그래프) 따로
        """
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
    # /시세 슬래시 커맨드
    # ======================
    @app_commands.command(
        name="시세",
        description="한국 서버 FF14 아이템 시세 조회",
    )
    async def price_cmd(self, interaction: discord.Interaction, 아이템이름: str):
        # 디코한테 "생각중..." 알리기
        await interaction.response.defer(thinking=True)

        item_name = extract_item_name(아이템이름)
        embed, file, view, error = self.build_price_view(item_name)

        if error:
            return await interaction.followup.send(error, ephemeral=True)

        await self._send_slash(interaction, embed, file, view)

    # ======================
    # 자연어 시세 (ex. "황금장어 시세 알려줘")
    # ======================
    async def search_and_reply(self, msg: discord.Message, *_):
        item_name = extract_item_name(msg.content)
        embed, file, view, error = self.build_price_view(item_name)

        if error:
            return await msg.reply(error, mention_author=False)

        await self._send_msg(msg, embed, file, view)

    # ======================
    # 시세 Embed + 그래프 + 비슷한 아이템 버튼 생성
    # ======================
    def build_price_view(self, item_name: str):
        item_id, real_name, similar = search_item(item_name)

        if not item_id:
            return None, None, None, f"❌ '{item_name}'과 비슷한 아이템을 찾지 못했어."

        # --- 기본 Embed ---
        embed = Embed(
            title=real_name,
            description="🇰🇷 한국 서버 시세",
            color=0xFFD700,
        )

        # 아이콘 썸네일
        icon = KR_ICONS.get(str(item_id))
        if icon:
            embed.set_thumbnail(
                url="https://xivapi.com/"
                + icon.replace("ui/icon/", "i/").replace(".tex", ".png")
            )

        # 상세 설명 / 카테고리
        det = KR_DETAIL.get(str(item_id), {})
        desc = det.get("desc", "")
        if not desc:
            desc = "설명이 없어요."

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

        # --- 월드별 최소가 계산 ---
        prices = []
        for server_name, world_id in KR_WORLDS.items():
            data = get_price(world_id, item_id)
            hq = None
            nq = None

            if data and data.get("listings"):
                for it in data["listings"]:
                    price = it.get("pricePerUnit")
                    if price is None:
                        continue
                    if it.get("hq"):
                        hq = min(hq, price) if hq is not None else price
                    else:
                        nq = min(nq, price) if nq is not None else price

            prices.append(
                {
                    "server": server_name,
                    "hq": hq,
                    "nq": nq,
                    "wid": world_id,
                }
            )

        # --- Embed에 시세 출력 ---
        for p in prices:
            lines: list[str] = []
            if p["hq"] is not None:
                lines.append(f"✨ HQ: **{format_price(p['hq'])}**")
            if p["nq"] is not None:
                lines.append(f"💰 NQ: {format_price(p['nq'])}")

            embed.add_field(
                name=p["server"],
                value="\n".join(lines) if lines else "❌ 매물 없음",
                inline=False,
            )

        # --- 그래프 생성 (첫 번째 유효 월드 기준) ---
        file = None
        ref = next((p for p in prices if p["hq"] is not None or p["nq"] is not None), None)
        if ref:
            buf = build_history_chart(ref["server"], ref["wid"], item_id)
            if buf:
                file = discord.File(buf, filename="chart.png")
                embed.set_image(url="attachment://chart.png")
                embed.set_footer(text=f"그래프: {ref['server']} 최근 7일")

        # --- 비슷한 아이템 버튼 ---
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
        # 버튼 눌렀을 때도 "생각중..." 먼저
        await interaction.response.defer(thinking=True)

        embed, file, view, error = self.cog.build_price_view(self.label)

        if error:
            return await interaction.followup.send(error, ephemeral=True)

        # 버튼이 붙어있는 "그 메시지"를 수정
        # (original_response 말고 edit_message를 쓰는 게 안전함)
        if file:
            await interaction.edit_original_response(
                embed=embed,
                attachments=[file],
                view=view,
            )
        else:
            await interaction.edit_original_response(
                embed=embed,
                view=view,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(MarketCog(bot))
    print("✨ MarketCog Loaded!")

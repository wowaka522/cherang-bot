# cogs/economy.py

import os
import time
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

# ====== 일하기 텍스트 (일반 업무) ======
WORK_NORMAL_LIST = [
    "소장용 피망전을 로웨나 상회에 납품했다.",
    "소장용 타코 카르네 아사다를 로웨나 상회에 납품했다.",
    "젊은 경영자 이올라를 도와 중용의 공예관에 기여했다.",
    "실록 시스템을 도와 중용의 공예관에 기여했다.",
    "수의사 베스릭을 도와 중용의 공예관에 기여했다.",
    "케시 레이를 도와 환상의 거대 생물을 쫓는 일을 도왔다.",
    "고독한 어부 프리스릭을 도와 중용의 공예관에 기여했다.",
    "루루샤 교수를 도와 마법대학에 기여했다.",
    "주드를 도와 마법대학에 기여했다.",
    "데브로이를 도와 마법대학에 기여했다.",
    "히나게시를 도와 마법대학에 기여했다.",
    "차라카 티아를 도와 마법대학에 기여했다.",
    "랄소지를 도와 와추메키메키 종합상가에 기여했다.",
    "파메카를 도와 와추메키메키 종합상가에 기여했다.",
    "셰로쟈를 도와 와추메키메키 종합상가에 기여했다.",
    "채집가 노인을 도와 와추메키메키 종합상가에 기여했다.",
    "도누하누를 도와 와추메키메키 종합상가에 기여했다.",
]

# ====== 던전 목록 ======
DUNGEON_LIST = [
    "사스타샤 침식 동굴",
    "탐타라 묘소",
    "구리종 광산",
    "할라탈리 수련장",
    "토토라크 감옥",
    "하우케타 별궁",
    "브레이플록스의 야영지",
    "카른의 무너진 사원",
    "나무꾼의 비명",
    "돌방패 경계초소",
    "제멜 요새",
    "금빛 골짜기",
    "방랑자의 궁전",
    "카스트룸 메리디아눔",
    "마도성 프라이토리움",
    "옛 암다포르 성",
    "시리우스 대등대",
    "옛 암다포르 시가지",
    "난파선의 섬",
    "얼음외투 대빙벽",
    "묵약의 탑",
    "어스름 요새",
    "솜 알",
    "용의 둥지",
    "이슈가르드 교황청",
    "구브라 환상도서관",
    "마과학 연구소",
    "거두지 않는 섬",
    "무한연속 박물함",
    "성 모샨 식물원",
    "거꾸로 선 탑",
    "소르 카이",
    "젤파톨",
    "바일사르 장성",
    "세이렌 해",
    "시스이 궁",
    "바르담 패도",
    "도마 성",
    "카스트룸 아바니아",
    "알라미고",
    "쿠가네 성",
    "성도산 사원",
    "스칼라 유적",
    "지옥뚜껑",
    "강엔 종묘",
    "영구 초토지대",
    "김리트 황야",
    "홀민스터",
    "도느 메그",
    "키타나 신굴",
    "말리카 큰우물",
    "굴그 화산",
    "아모로트",
    "쌍둥이 시르쿠스",
    "애나이더 아카데미아",
    "그랑 코스모스",
    "애니드라스 아남네시스",
    "노르브란트",
    "마토야의 공방",
    "파글단",
    "조트 탑",
    "바브일 탑",
    "바나스파티",
    "휘페르보레아 조물원",
    "아이티온 별현미경",
    "잔해별",
    "스마일턴",
    "스티그마-4",
    "알자달 해저 유적",
    "트로이아 궁정",
    "라피스 마날리스",
    "함 섬",
    "달의 지하계곡",
    "이후이카 투무",
    "워코 조모",
    "하늘심연 세노테",
    "뱅가드",
    "오리제닉스",
    "알렉산드리아",
    "사보텐더 계곡",
    "헤매는 성",
    "유웨야와타",
    "언더킵",
    "메인 터미널",
]

# ====== 채집 재료 ======
GATHER_ITEMS = [
    "에테르 모래",
    "기름씨앗",
    "검은밀",
    "새알",
    "계피",
    "찻잎",
    "이페나무 원목",
    "티타늄 광석",
    "뜰냉이",
    "섬전암",
]

WORK_COOLDOWN = 60 * 60      # 1시간
GATHER_COOLDOWN = 60 * 10    # 10분


# ====== 일/채집 버튼 View ======

class WorkGatherView(discord.ui.View):
    """!일하기 / !채집 통합 선택 UI"""

    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "이건 그 사람 전용 버튼이야. 구경만 해.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="🧹 일하기", style=discord.ButtonStyle.primary)
    async def do_work(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        uid = interaction.user.id
        data = get_user(uid)

        now = time.time()
        last = data.get("last_work", 0)
        remain = last + WORK_COOLDOWN - now

        if remain > 0:
            mins = int(remain // 60)
            secs = int(remain % 60)
            return await interaction.response.send_message(
                f"아직 쉴 시간인데? **{mins}분 {secs}초** 뒤에 다시 와.",
                ephemeral=True,
            )

        data["last_work"] = now
        update_user(uid, data)

        # 일반 업무 vs 던전 50:50
        if random.random() < 0.5 or not DUNGEON_LIST:
            text = random.choice(WORK_NORMAL_LIST)
            pay = random.randint(30, 100)
            title = "🧹 일하기 완료"
        else:
            dungeon = random.choice(DUNGEON_LIST)
            text = f"{dungeon}을(를) 탐방하고 보고서를 제출했다."
            pay = random.randint(100, 300)
            title = "🏰 던전 임무 완료"

        total = add_money(uid, pay)

        try:
            await interaction.message.delete()
        except Exception:
            pass

        desc = f"{text}\n\n🪙 {pay} 길을 받았다.\n(현재 소지금: {total} 길)"

        embed = discord.Embed(
            title=title,
            description=desc,
            color=0x55FFAA,
        )
        embed.set_footer(text="…열심히는 하네. 이 정도면 인정.")

        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="🌿 채집하기", style=discord.ButtonStyle.success)
    async def do_gather(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        uid = interaction.user.id
        data = get_user(uid)

        now = time.time()
        last = data.get("last_gather", 0)
        remain = last + GATHER_COOLDOWN - now

        if remain > 0:
            mins = int(remain // 60)
            secs = int(remain % 60)
            return await interaction.response.send_message(
                f"벌써 또 가겠다고? **{mins}분 {secs}초**만 더 기다려.",
                ephemeral=True,
            )

        data["last_gather"] = now
        update_user(uid, data)

        item_name = random.choice(GATHER_ITEMS)
        amount = random.randint(1, 3)
        add_item(uid, item_name, amount)

        pay = random.randint(5, 20)
        total = add_money(uid, pay)

        try:
            await interaction.message.delete()
        except Exception:
            pass

        desc = (
            f"숲을 한참 쏘다니다가 **{item_name} x{amount}** 챙겨왔다.\n"
            f"덤으로 {pay} 길도 쥐어줬다.\n"
            f"(현재 소지금: {total} 길)"
        )

        embed = discord.Embed(
            title="🌿 채집 완료",
            description=desc,
            color=0x77DD77,
        )
        embed.set_footer(text="…괜찮네. 꽤 쓸 만한 재료야.")

        await interaction.response.send_message(embed=embed)


# ====== 인벤토리 UI ======

class InventoryMainView(discord.ui.View):
    """!인벤 -> 개봉/판매/선물 버튼"""

    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "네 인벤이 아니잖아. 구경만 해.",
                ephemeral=True,
            )
            return False
        return True

    async def _start_mode(self, interaction: discord.Interaction, mode: str):
        uid = interaction.user.id
        data = get_user(uid)
        inv: dict = data.get("inventory", {}) or {}

        # 모드별 아이템 필터
        items = list(inv.items())

        if mode == "open":
            items = [(name, cnt) for name, cnt in items if cnt > 0 and is_box_item_name(name)]
            title = "📦 개봉할 상자 선택"
            placeholder = "개봉할 상자를 골라."
        elif mode == "sell":
            items = [(name, cnt) for name, cnt in items if cnt > 0]
            title = "💰 판매할 아이템 선택"
            placeholder = "판매할 아이템을 골라."
        elif mode == "gift":
            items = [(name, cnt) for name, cnt in items if cnt > 0]
            title = "🎁 선물할 아이템 선택"
            placeholder = "선물할 아이템을 골라."
        else:
            return

        if not items:
            msg = {
                "open": "열 수 있는 상자가 없는데?",
                "sell": "팔 게 없잖아. 먼저 좀 모아와.",
                "gift": "선물할만한 게 없어. 네 인벤부터 챙겨.",
            }.get(mode, "해당 모드에 맞는 아이템이 없어.")
            return await interaction.response.send_message(msg, ephemeral=True)

        # 디스코드 Select는 최대 25개 옵션
        items = items[:25]

        options = []
        for name, cnt in items:
            item_id = get_item_id_by_name(name)
            label = f"{name} x{cnt}"
            if item_id is not None:
                cat = get_item_category(item_id)
                desc = cat
            else:
                desc = ""
            options.append(
                discord.SelectOption(
                    label=label[:100],
                    description=desc[:100] if desc else None,
                    value=name,
                )
            )

        embed = discord.Embed(
            title=title,
            description="목록에서 하나만 골라.",
            color=0x2ecc71 if mode == "open" else 0xe67e22 if mode == "sell" else 0x9b59b6,
        )

        view = InventorySelectView(self.user_id, mode, options)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="📦 개봉", style=discord.ButtonStyle.primary)
    async def btn_open(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._start_mode(interaction, "open")

    @discord.ui.button(label="💰 판매", style=discord.ButtonStyle.danger)
    async def btn_sell(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._start_mode(interaction, "sell")

    @discord.ui.button(label="🎁 선물", style=discord.ButtonStyle.success)
    async def btn_gift(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._start_mode(interaction, "gift")


class InventorySelectView(discord.ui.View):
    """인벤 선택용 Select View"""

    def __init__(self, user_id: int, mode: str, options: list[discord.SelectOption]):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.mode = mode

        select = discord.ui.Select(
            placeholder="아이템을 선택해.",
            min_values=1,
            max_values=1,
            options=options,
        )
        select.callback = self._on_select  # type: ignore
        self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "이 인벤은 네 거 아니야.",
                ephemeral=True,
            )
            return False
        return True

    async def _on_select(self, interaction: discord.Interaction):
        uid = interaction.user.id
        selected_name = interaction.data["values"][0]  # type: ignore

        # label이 "이름 x수량"이라 value에 순수 이름만 넣어뒀음.
        item_name = selected_name

        data = get_user(uid)
        inv: dict = data.get("inventory", {}) or {}
        count = inv.get(item_name, 0)

        if count <= 0:
            return await interaction.response.send_message(
                "이미 없어졌는데? 인벤 다시 열어봐.",
                ephemeral=True,
            )

        if self.mode == "open":
            await self._handle_open(interaction, data, inv, item_name)
        elif self.mode == "sell":
            await self._handle_sell(interaction, data, inv, item_name)
        elif self.mode == "gift":
            await self._handle_gift(interaction, data, inv, item_name)

    async def _handle_open(self, interaction: discord.Interaction, data: dict, inv: dict, box_name: str):
        uid = interaction.user.id

        if not is_box_item_name(box_name):
            return await interaction.response.send_message(
                "저건 상자가 아닌데? 상자만 골라.",
                ephemeral=True,
            )

        # 상자 1개 소모
        if inv.get(box_name, 0) <= 0:
            return await interaction.response.send_message(
                "이미 다 쓴 상자야. 인벤 다시 확인해봐.",
                ephemeral=True,
            )
        inv[box_name] -= 1
        if inv[box_name] <= 0:
            inv.pop(box_name, None)
        data["inventory"] = inv
        update_user(uid, data)

        # 장비 랜덤 지급
        reward_name = get_random_equip_item_name()
        add_item(uid, reward_name, 1)

        item_id = get_item_id_by_name(reward_name)
        icon_url = get_icon_url(item_id) if item_id is not None else None
        desc = get_item_desc(item_id) if item_id is not None else ""

        embed = discord.Embed(
            title="📦 상자 개봉!",
            description=f"**{box_name}**을(를) 열어 **{reward_name}**을(를) 얻었다.",
            color=0xf1c40f,
        )
        if desc:
            embed.add_field(name="설명", value=desc[:1024], inline=False)
        if icon_url:
            embed.set_thumbnail(url=icon_url)

        embed.set_footer(text="운이… 나쁘진 않네. 이번엔.")

        await interaction.response.edit_message(embed=embed, view=None)

    async def _handle_sell(self, interaction: discord.Interaction, data: dict, inv: dict, item_name: str):
        uid = interaction.user.id

        if inv.get(item_name, 0) <= 0:
            return await interaction.response.send_message(
                "팔 게 없는데? 인벤 다시 확인해봐.",
                ephemeral=True,
            )

        item_id = get_item_id_by_name(item_name)
        base_price = get_item_base_price(item_id) if item_id is not None else 100
        sell_price = max(1, base_price // 2)

        # 1개 판매
        inv[item_name] -= 1
        if inv[item_name] <= 0:
            inv.pop(item_name, None)
        data["inventory"] = inv
        update_user(uid, data)

        total = add_money(uid, sell_price)

        icon_url = get_icon_url(item_id) if item_id is not None else None

        embed = discord.Embed(
            title="💰 판매 완료",
            description=f"**{item_name}**을(를) 팔아서 **{sell_price} 길**을 받았다.\n"
                        f"(현재 소지금: {total} 길)",
            color=0xe67e22,
        )
        if icon_url:
            embed.set_thumbnail(url=icon_url)
        embed.set_footer(text="쓸 데 없는 건 빨리 털어내는 게 낫지.")

        await interaction.response.edit_message(embed=embed, view=None)

    async def _handle_gift(self, interaction: discord.Interaction, data: dict, inv: dict, item_name: str):
        # 여기서는 실제 선물 전송까지는 안 하고,
        # 어떤 아이템을 선물할지 골라주는 용도로 사용.
        # 실제 선물은 기존 !선물 명령어로 처리.
        cmd_example = f"!선물 @대상 {item_name}"

        embed = discord.Embed(
            title="🎁 선물 준비",
            description=(
                f"**{item_name}**을(를) 선물로 줄 거야?\n\n"
                f"대상을 정했으면 채팅에 이렇게 치면 돼:\n`{cmd_example}`"
            ),
            color=0x9b59b6,
        )
        embed.set_footer(text="선물할 사람까지 내가 골라줄 순 없잖아?")

        await interaction.response.edit_message(embed=embed, view=None)


# ====== Economy Cog ======

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 💰 잔액 (!돈 / !길)
    @commands.command(name="돈")
    async def money(self, ctx: commands.Context):
        data = get_user(ctx.author.id)
        await ctx.reply(
            f"네 지갑에 {data.get('money', 0)} 길.",
            mention_author=False,
        )

    @commands.command(name="길")
    async def money_alias(self, ctx: commands.Context):
        await self.money(ctx)

    # 🧹 / 🌿 선택 UI
    @commands.command(name="일하기")
    async def work_menu(self, ctx: commands.Context):
        view = WorkGatherView(ctx.author.id)

        embed = discord.Embed(
            title="오늘은 뭐 할 거냐?",
            description="버튼 눌러서 골라.",
            color=0x3498DB,
        )
        embed.set_footer(text="괜히 눌러놓고 귀찮다고 하지 말고.")

        await ctx.reply(
            embed=embed,
            view=view,
            mention_author=False,
        )

    @commands.command(name="채집")
    async def gather_menu_alias(self, ctx: commands.Context):
        await self.work_menu(ctx)

    # 🎁 선물 (텍스트 명령 버전 – 버튼/선택 UI와 연동)
    @commands.command(name="선물")
    async def gift(self, ctx, 대상: discord.Member, *, 아이템: str):
        giver = ctx.author.id
        receiver = 대상.id
        data = get_user(giver)
        inv = data.get("inventory", {})

        if inv.get(아이템, 0) <= 0:
            return await ctx.reply("거짓말하지마. 없잖아.", mention_author=False)

        inv[아이템] -= 1
        if inv[아이템] <= 0:
            inv.pop(아이템, None)
        data["inventory"] = inv
        update_user(giver, data)
        add_item(receiver, 아이템)
        await ctx.reply(
            f"{대상.display_name}에게 {아이템} 선물… 좋아하겠지 뭐.",
            mention_author=False,
        )

    # 💸 돈 주기
    @commands.command(name="주기")
    async def give_money(self, ctx, 대상: discord.Member, 금액: int):
        if 금액 <= 0:
            return await ctx.reply("장난?", mention_author=False)

        uid = ctx.author.id
        recv = 대상.id
        data = get_user(uid)

        if data.get("money", 0) < 금액:
            return await ctx.reply("가진 것도 없으면서.", mention_author=False)

        data["money"] -= 금액
        update_user(uid, data)
        add_money(recv, 금액)
        await ctx.reply(
            f"{대상.display_name}에게 {금액} 길 줬어.",
            mention_author=False,
        )

    # 🎒 인벤 (UI 버전)
    # @commands.command(name="인벤")
    # async def inv(self, ctx: commands.Context):
        data = get_user(ctx.author.id)
        inv: dict = data.get("inventory", {}) or {}

        if not inv:
            return await ctx.reply("텅.", mention_author=False)

        lines = []
        for name, cnt in list(inv.items())[:20]:
            item_id = get_item_id_by_name(name)
            cat = get_item_category(item_id) if item_id is not None else ""
            if cat:
                lines.append(f"- **{name}** x{cnt} (`{cat}`)")
            else:
                lines.append(f"- **{name}** x{cnt}")

        desc = "\n".join(lines)
        if len(inv) > 20:
            desc += f"\n… 등 {len(inv) - 20}개 더 있음."

        embed = discord.Embed(
            title=f"{ctx.author.display_name}의 인벤토리",
            description=desc,
            color=0x95a5a6,
        )
        embed.set_footer(text="뭐 할지 모르겠으면… 개봉하거나 팔아보든가.")

        view = InventoryMainView(ctx.author.id)
        await ctx.reply(embed=embed, view=view, mention_author=False)

    # ⚙ 관리자 지급
    @commands.command(name="지급")
    async def give_admin(self, ctx, 대상: discord.Member, 금액: int):
        if ctx.author.id != OWNER_ID:
            return await ctx.reply("누구 맘대로? 주인만 가능.", mention_author=False)
        if 금액 <= 0:
            return await ctx.reply("장난?", mention_author=False)

        total = add_money(대상.id, 금액)
        await ctx.reply(
            f"{대상.display_name} 지갑에 {금액} 길 박아줬음. (총 {total} 길)",
            mention_author=False,
        )
        


async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
    print("✨ EconomyCog Loaded!")

# cogs/gambling.py

import random
import asyncio
import discord
from discord import app_commands
from discord.ext import commands

from utils.user_api import (
    get_user,
    update_user,
)

# ================================
# 공통 설정
# ================================

MIN_BET = 100          # 슬롯/바카라 최소 베팅
BJ_MIN_BET = 1000      # 블랙잭 최소 베팅
BJ_MAX_BET = 5000      # 블랙잭 최대 베팅

# 슬롯 심볼 테이블
# (name, emoji_id, weight, code, multiplier)
SLOT_TABLE = [
    ("potion", 1447268604218441909, 10, "Potion", 10),
    ("red",    1447268797621731378, 40, "R", 1.3),
    ("yellow", 1447268817595007099, 40, "Y", 1.3),
    ("green",  1447268747613044767, 40, "G", 1.3),
    ("blue",   1447189856152326194, 40, "B", 1.3),
    ("purple", 1447268773512876205, 40, "P", 1.3),
]

# ================================
# 공통 쿨데레/악마 멘트
# ================================

def get_cool_comment(win: int, bet: int) -> str:
    """도박 결과에 따른 체랑 코멘트 (슬롯/바카라/블랙잭 공용)"""
    # 냥체 5% 확률
    if random.random() < 0.05:
        return "…우으. 이번엔 망한 거다냥. 아, 아니야. 아무것도 아냐."

    if win == 0:
        return random.choice([
            "하아… 그래서 내가 하지 말랬잖아.",
            "도박의 신이 널 싫어하나 봐.",
            "그 돈으로 밥이나 사 먹지 그랬어.",
            "여긴 원래 집이 아니라 지갑이 타는 곳이거든.",
        ])
    elif win < bet:
        return random.choice([
            "완전 망하진 않았네. 그게 더 짜증나.",
            "반쯤만 털렸네. 축하해야 하나?",
            "살짝만 베였어. 다음엔 더 깊게 들어갈지도?",
        ])
    elif win == bet:
        return random.choice([
            "본전 치기… 재미없어.",
            "이득도 아니고 손해도 아니고, 애매하네.",
        ])
    elif win < bet * 3:
        return random.choice([
            "뭐, 잘했네. 조금은 인정해 줄게.",
            "운이… 아주 나쁘진 않네.",
        ])
    else:
        return random.choice([
            "…뭐야. 생각보다 잘 뽑았는데?",
            "설마 잭팟 냈다고 자랑 다니진 않을 거지?",
            "이 정도면 카지노 입장에서도 재밌는 손님이네.",
        ])


# ================================
# 슬롯 관련
# ================================

def pick_symbol():
    """SLOT_TABLE에서 확률 가중치로 심볼 하나 뽑기"""
    weights = [t[2] for t in SLOT_TABLE]
    name, eid, _, code, mult = random.choices(SLOT_TABLE, weights=weights, k=1)[0]
    emoji = f"<:{name}:{eid}>"
    return emoji, code, mult


async def start_slot_spin(interaction: discord.Interaction, user_id: int, bet: int):
    data = get_user(user_id)
    money = data.get("money", 0)

    if bet < MIN_BET:
        return await interaction.response.send_message(
            f"최소 베팅은 {MIN_BET} 길이야. 장난하냐.", ephemeral=True
        )

    if bet <= 0:
        return await interaction.response.send_message("장난하냐.", ephemeral=True)

    if money < bet:
        return await interaction.response.send_message("돈도 없으면서.", ephemeral=True)

    # 돈 차감
    data["money"] = money - bet
    update_user(user_id, data)

    # 첫 메시지
    first_embed = discord.Embed(
        title="🎰 슬롯 머신 - 스핀 중",
        description="❔ ❔ ❔",
        color=0x55FFAA
    )
    first_embed.add_field(name="베팅", value=f"{bet} 길", inline=True)
    first_embed.add_field(name="잔액", value=f"{data['money']} 길", inline=True)
    first_embed.set_footer(text="…하, 이제 돌렸으니까 돌이킬 수도 없지.")

    await interaction.response.send_message(embed=first_embed)
    msg = await interaction.original_response()

    result = []
    display = ["❔", "❔", "❔"]
    anim_embed = first_embed

    # 3칸 순차 공개
    for i in range(3):
        await asyncio.sleep(0.6)

        symbol = pick_symbol()  # (emoji, code, mult)
        result.append(symbol)

        for idx in range(3):
            if idx <= i:
                display[idx] = result[idx][0]
            else:
                display[idx] = "❔"

        anim_embed.description = " ".join(display)
        await msg.edit(embed=anim_embed)

    # 승리 계산
    names = [x[1] for x in result]   # code
    mults = [x[2] for x in result]   # mult

    win = 0
    if len(set(names)) == 1:
        # 3개 모두 같은 심볼
        win = int(bet * mults[0])
    elif "Potion" in names:
        # 포션 하나라도 포함
        win = int(bet * 0.5)

    data = get_user(user_id)
    data["money"] = data.get("money", 0) + win
    update_user(user_id, data)

    final_symbols = " ".join([x[0] for x in result])
    comment = get_cool_comment(win, bet)

    final_embed = discord.Embed(
        title="🎰 결과!",
        description=(
            f"{final_symbols}\n\n"
            f"베팅: **{bet} 길**\n"
            f"획득: **{win} 길**\n"
            f"현재 잔액: **{data['money']} 길**\n\n"
            f"{comment}"
        ),
        color=0xFFD700 if win > 0 else 0x555555
    )
    await msg.edit(embed=final_embed)


# ================================
# 바카라 관련
# ================================

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

def baccarat_card_value(rank: str) -> int:
    if rank == "A":
        return 1
    if rank in ["J", "Q", "K", "10"]:
        return 0
    return int(rank)


def baccarat_draw_card() -> str:
    return random.choice(RANKS)


def baccarat_hand_sum(cards) -> int:
    return sum(baccarat_card_value(r) for r in cards) % 10


def baccarat_format_cards(cards):
    # 🃏 A 🃏 9 이런 느낌
    return " ".join(f"🃏{c}" for c in cards)


async def start_baccarat_game(interaction: discord.Interaction, user_id: int, bet: int, bet_type: str):
    """바카라 한 판 진행"""
    data = get_user(user_id)
    money = data.get("money", 0)

    if bet < MIN_BET:
        return await interaction.response.send_message(
            f"최소 베팅은 {MIN_BET} 길이야. 농담이 아니야.", ephemeral=True
        )
    if bet <= 0:
        return await interaction.response.send_message("장난하냐.", ephemeral=True)
    if money < bet:
        return await interaction.response.send_message("돈도 없으면서.", ephemeral=True)

    # 돈 차감
    data["money"] = money - bet
    update_user(user_id, data)

    # 초기 상태
    player_cards = []
    banker_cards = []

    bet_name_map = {
        "player": "플레이어 승 (2배)",
        "banker": "뱅커 승 (1.5배)",
        "tie": "타이 (9배)",
        "pair": "페어 (12배)",
    }

    # 첫 임베드
    embed = discord.Embed(
        title="🎴 바카라 - 진행 중",
        description=(
            "플레이어와 뱅커의 패를 공개하는 중…\n\n"
            "플레이어: ❔ ❔ (합계: ?)\n"
            "뱅커: ❔ ❔ (합계: ?)"
        ),
        color=0xAA2233
    )
    embed.add_field(name="베팅", value=f"{bet} 길", inline=True)
    embed.add_field(name="베팅 종류", value=bet_name_map.get(bet_type, bet_type), inline=True)
    embed.add_field(name="현재 잔액", value=f"{data['money']} 길", inline=False)
    embed.set_footer(text="…이긴다고 장담은 안 해.")

    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()

    # 카드 공개 애니메이션
    # 1) 플레이어 1장
    await asyncio.sleep(0.7)
    player_cards.append(baccarat_draw_card())
    desc = (
        f"플레이어: {baccarat_format_cards(player_cards)} ❔ (합계: ?)\n"
        f"뱅커: ❔ ❔ (합계: ?)"
    )
    embed.description = desc
    await msg.edit(embed=embed)

    # 2) 뱅커 1장
    await asyncio.sleep(0.7)
    banker_cards.append(baccarat_draw_card())
    desc = (
        f"플레이어: {baccarat_format_cards(player_cards)} ❔ (합계: ?)\n"
        f"뱅커: {baccarat_format_cards(banker_cards)} ❔ (합계: ?)"
    )
    embed.description = desc
    await msg.edit(embed=embed)

    # 3) 플레이어 2장
    await asyncio.sleep(0.7)
    player_cards.append(baccarat_draw_card())
    desc = (
        f"플레이어: {baccarat_format_cards(player_cards)} (합계: ?)\n"
        f"뱅커: {baccarat_format_cards(banker_cards)} ❔ (합계: ?)"
    )
    embed.description = desc
    await msg.edit(embed=embed)

    # 4) 뱅커 2장 + 최종 합계
    await asyncio.sleep(0.7)
    banker_cards.append(baccarat_draw_card())

    p_sum = baccarat_hand_sum(player_cards)
    b_sum = baccarat_hand_sum(banker_cards)

    desc = (
        f"플레이어: {baccarat_format_cards(player_cards)} (합계: **{p_sum}**)\n"
        f"뱅커: {baccarat_format_cards(banker_cards)} (합계: **{b_sum}**)"
    )
    embed.description = desc

    # 승패 판정
    if p_sum > b_sum:
        winner = "player"
    elif p_sum < b_sum:
        winner = "banker"
        # dealer
    else:
        winner = "tie"

    # 페어 여부 (양쪽 첫 2장 중 한쪽이라도 페어면 인정)
    is_pair = (player_cards[0] == player_cards[1]) or (banker_cards[0] == banker_cards[1])

    win = 0
    # 배당: 플레이어 (2배), 뱅커 (1.5배), 타이 (9배), 페어 (12배)
    if bet_type == "player":
        if winner == "player":
            win = int(bet * 2)
    elif bet_type == "banker":
        if winner == "banker":
            win = int(bet * 1.5)
    elif bet_type == "tie":
        if winner == "tie":
            win = int(bet * 9)
    elif bet_type == "pair":
        if is_pair:
            win = int(bet * 12)

    data = get_user(user_id)
    data["money"] = data.get("money", 0) + win
    update_user(user_id, data)

    winner_text = {
        "player": "플레이어 승",
        "banker": "뱅커 승",
        "tie": "타이",
    }[winner]

    pair_text = "있음" if is_pair else "없음"

    comment = get_cool_comment(win, bet)

    result_embed = discord.Embed(
        title="🎴 바카라 결과",
        description=(
            f"{desc}\n\n"
            f"승부 결과: **{winner_text}**\n"
            f"페어 여부: **{pair_text}**\n\n"
            f"베팅: **{bet} 길** ({bet_name_map.get(bet_type, bet_type)})\n"
            f"획득: **{win} 길**\n"
            f"현재 잔액: **{data['money']} 길**\n\n"
            f"{comment}"
        ),
        color=0xFFD700 if win > 0 else 0x555555
    )

    await msg.edit(embed=result_embed)


# ================================
# 블랙잭 관련
# ================================

def bj_draw_card() -> str:
    return random.choice(RANKS)


def bj_hand_value(cards) -> int:
    """에이스 1/11 처리 포함"""
    total = 0
    aces = 0
    for r in cards:
        if r == "A":
            total += 11
            aces += 1
        elif r in ["K", "Q", "J", "10"]:
            total += 10
        else:
            total += int(r)
    # 에이스 11 -> 1로 하나씩 내리기
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def bj_is_blackjack(cards) -> bool:
    return len(cards) == 2 and bj_hand_value(cards) == 21


def bj_format_cards(cards):
    return " ".join(f"🃏{c}" for c in cards)


class BlackjackGameView(discord.ui.View):
    def __init__(self, user_id: int, bet: int, player_cards, dealer_cards):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.bet = bet
        self.player_cards = player_cards
        self.dealer_cards = dealer_cards
        self.finished = False
        self.first_action = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("네 판 아니잖아.", ephemeral=True)
            return False
        return True

    def build_embed(self, reveal: bool = False, extra: str = None, color=0x228833):
        p_val = bj_hand_value(self.player_cards)
        if reveal:
            d_val = bj_hand_value(self.dealer_cards)
            dealer_txt = f"{bj_format_cards(self.dealer_cards)} (합계: **{d_val}**)"
        else:
            dealer_txt = f"{bj_format_cards(self.dealer_cards[:1])} 🂠 (합계: ?)"

        desc = (
            f"플레이어: {bj_format_cards(self.player_cards)} (합계: **{p_val}**)\n"
            f"딜러: {dealer_txt}"
        )
        if extra:
            desc += f"\n\n{extra}"

        e = discord.Embed(title="🃏 블랙잭", description=desc, color=color)
        e.add_field(name="베팅", value=f"{self.bet} 길", inline=True)
        return e

    async def safe_edit(self, interaction: discord.Interaction, embed, view=None):
        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.message.edit(embed=embed, view=view)
        except Exception:
            await interaction.followup.send(embed=embed, view=view)

    async def end_game(self, interaction: discord.Interaction, result_text: str, color=0x555555):
        if self.finished:
            return
        
        self.finished = True
        # 버튼 제거!

        embed = self.build_embed(reveal=True, extra=result_text, color=color)
        await self.safe_edit(interaction, embed, view=None)

    async def dealer_turn(self, interaction: discord.Interaction):
        # 딜러 공개
        await self.safe_edit(interaction, self.build_embed(True, "딜러가 카드를 받는 중…"))
        await asyncio.sleep(0.7)

        while bj_hand_value(self.dealer_cards) < 17:
            self.dealer_cards.append(bj_draw_card())
            await self.safe_edit(interaction, self.build_embed(True, "딜러가 카드를 받는 중…"))
            await asyncio.sleep(0.7)

        p = bj_hand_value(self.player_cards)
        d = bj_hand_value(self.dealer_cards)

        data = get_user(self.user_id)

        if d > 21:
            win = self.bet * 2
            msg = "딜러 버스트! 네 승리."
        elif p > d:
            win = self.bet * 2
            msg = "이겼네. 운 좋네?"
        elif p < d:
            win = 0
            msg = "졌지. 그럴 줄 알았어."
        else:
            win = self.bet
            msg = "무승부. 목숨부지한 정도?"

        data["money"] += win
        update_user(self.user_id, data)
        comment = get_cool_comment(win, self.bet)

        result = f"{msg}\n획득: **{win} 길**\n잔액: **{data['money']} 길**\n\n{comment}"
        await self.end_game(interaction, result, 0xFFD700 if win > 0 else 0x555555)

    # ===========================
    #        버튼 영역
    # ===========================
    @discord.ui.button(label="HIT", style=discord.ButtonStyle.success)
    async def hit(self, interaction: discord.Interaction, _):
        if self.finished:
            return await interaction.response.send_message("이미 끝난 판.", ephemeral=True)

        self.player_cards.append(bj_draw_card())
        p = bj_hand_value(self.player_cards)

        if p > 21:  # 버스트
            data = get_user(self.user_id)
            comment = get_cool_comment(0, self.bet)
            return await self.end_game(
                interaction,
                f"버스트! 0 길.\n잔액: **{data['money']} 길**\n\n{comment}",
                0x555555
            )

        self.first_action = False
        await self.safe_edit(interaction, self.build_embed(False, "계속?"), self)

    @discord.ui.button(label="STAY", style=discord.ButtonStyle.primary)
    async def stay(self, interaction: discord.Interaction, _):
        if self.finished:
            return await interaction.response.send_message("이미 끝난 판.", ephemeral=True)

        self.first_action = False
        await self.dealer_turn(interaction)

    @discord.ui.button(label="DOUBLE", style=discord.ButtonStyle.secondary)
    async def double(self, interaction: discord.Interaction, _):
        if self.finished:
            return await interaction.response.send_message("이미 끝났어.", ephemeral=True)
        if not self.first_action:
            return await interaction.response.send_message("더블은 첫 행동만 돼.", ephemeral=True)

        data = get_user(self.user_id)
        if data.get("money", 0) < self.bet:
            return await interaction.response.send_message("돈 없는데 더블이?", ephemeral=True)

        data["money"] -= self.bet
        update_user(self.user_id, data)
        self.bet *= 2
        self.first_action = False

        self.player_cards.append(bj_draw_card())
        if bj_hand_value(self.player_cards) > 21:  # 즉시 버스트
            comment = get_cool_comment(0, self.bet)
            return await self.end_game(
                interaction,
                f"더블치고 버스트ㅋㅋ\n획득: 0 길\n잔액: **{data['money']} 길**\n\n{comment}",
                0x555555
            )

        await self.dealer_turn(interaction)

    @discord.ui.button(label="SURRENDER", style=discord.ButtonStyle.danger)
    async def surrender(self, interaction: discord.Interaction, _):
        if self.finished:
            return await interaction.response.send_message("이미 끝났어.", ephemeral=True)
        if not self.first_action:
            return await interaction.response.send_message("이제 와서?", ephemeral=True)

        refund = self.bet // 2
        data = get_user(self.user_id)
        data["money"] += refund
        update_user(self.user_id, data)
        comment = get_cool_comment(refund, self.bet)

        await self.end_game(
            interaction,
            f"항복이네.\n환급: {refund} 길\n잔액: **{data['money']} 길**\n\n{comment}"
        )


class BlackjackBetView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("네 돈 아니잖아.", ephemeral=True)
            return False
        return True

    @discord.ui.select(
        placeholder="블랙잭 베팅 금액 선택",
        options=[
            discord.SelectOption(label="1000 길"),
            discord.SelectOption(label="2000 길"),
            discord.SelectOption(label="3000 길"),
            discord.SelectOption(label="5000 길"),
        ]
    )
    async def select_bet(self, interaction: discord.Interaction, select: discord.ui.Select):
        bet = int(select.values[0].split()[0])

        if bet < BJ_MIN_BET or bet > BJ_MAX_BET:
            return await interaction.response.send_message(
                f"블랙잭 베팅은 {BJ_MIN_BET}~{BJ_MAX_BET} 길 사이만 가능해.", ephemeral=True
            )

        data = get_user(self.user_id)
        money = data.get("money", 0)

        if money < bet:
            return await interaction.response.send_message("돈도 없으면서 블랙잭이래.", ephemeral=True)

        # 베팅 차감
        data["money"] = money - bet
        update_user(self.user_id, data)

        # 카드 2장씩 배분
        player_cards = [bj_draw_card(), bj_draw_card()]
        dealer_cards = [bj_draw_card(), bj_draw_card()]

        p_sum = bj_hand_value(player_cards)
        d_sum = bj_hand_value(dealer_cards)

        player_bj = bj_is_blackjack(player_cards)
        dealer_bj = bj_is_blackjack(dealer_cards)

        # 자연 블랙잭 처리
        if player_bj or dealer_bj:
            if player_bj and dealer_bj:
                # 푸시
                win = int(bet)
                result_text = "둘 다 블랙잭이네. …재미없게 무승부야."
            elif player_bj:
                # 플레이어 BJ: 1.5배
                win = int(bet * 2.5)
                result_text = "블랙잭. 오늘 운 다 썼네."
            else:
                # 딜러 BJ
                win = 0
                result_text = "딜러가 블랙잭이야. …이렇게까지 질 수도 있지."

            data = get_user(self.user_id)
            data["money"] = data.get("money", 0) + win
            update_user(self.user_id, data)

            desc = (
                f"플레이어: {bj_format_cards(player_cards)} (합계: **{p_sum}**)\n"
                f"딜러: {bj_format_cards(dealer_cards)} (합계: **{d_sum}**)\n\n"
                f"{result_text}\n\n"
                f"베팅: **{bet} 길**\n"
                f"획득: **{win} 길**\n"
                f"현재 잔액: **{data['money']} 길**\n\n"
            )
            comment = get_cool_comment(win, bet)
            desc += comment

            embed = discord.Embed(
                title="🃏 블랙잭 - 결과",
                description=desc,
                color=0xFFD700 if win > 0 else 0x555555
            )
            return await interaction.response.edit_message(embed=embed, view=None)

        # 자연 블랙잭 아니면, 인터랙션 게임 시작
        desc = (
            f"플레이어: {bj_format_cards(player_cards)} (합계: **{p_sum}**)\n"
            f"딜러: {bj_format_cards(dealer_cards[:1])} 🂠 (합계: ?)\n\n"
            f"히트 / 스테이 / 더블 / 서렌더 중 하나를 골라."
        )
        embed = discord.Embed(
            title="🃏 블랙잭 - 시작",
            description=desc,
            color=0x228833
        )
        embed.add_field(name="베팅", value=f"{bet} 길", inline=True)
        embed.add_field(name="현재 잔액", value=f"{data['money']} 길", inline=True)
        embed.set_footer(text="…여긴 그냥 돈 태우는 곳이야. 알면서 들어온 거지?")

        view = BlackjackGameView(self.user_id, bet, player_cards, dealer_cards)
        await interaction.response.edit_message(embed=embed, view=view)


# ================================
# UI 뷰 (게임 선택 / 슬롯 / 바카라)
# ================================

class GameSelectView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("이건 네 도박장이 아니야.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🎰 슬롯", style=discord.ButtonStyle.primary)
    async def slot_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = self.user_id
        data = get_user(uid)
        money = data.get("money", 0)

        embed = discord.Embed(
            title="🎰 슬롯 머신",
            description=(
                f"베팅 금액을 골라.\n"
                f"현재 소지금: **{money} 길**\n\n"
                f"최소 베팅: {MIN_BET} 길"
            ),
            color=0x55FFAA
        )
        embed.set_footer(text="…진짜 할 거야? 후회해도 몰라.")

        view = SlotBetView(uid)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🎴 바카라", style=discord.ButtonStyle.danger)
    async def baccarat_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = self.user_id
        data = get_user(uid)
        money = data.get("money", 0)

        embed = discord.Embed(
            title="🎴 바카라",
            description=(
                f"베팅 금액부터 정해.\n"
                f"현재 소지금: **{money} 길**\n\n"
                f"최소 베팅: {MIN_BET} 길"
            ),
            color=0xAA2233
        )
        embed.set_footer(text="…규칙은 대충 알지?")

        view = BaccaratBetView(uid)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🃏 블랙잭", style=discord.ButtonStyle.success)
    async def blackjack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = self.user_id
        data = get_user(uid)
        money = data.get("money", 0)

        embed = discord.Embed(
            title="🃏 블랙잭",
            description=(
                f"베팅 금액을 골라.\n"
                f"현재 소지금: **{money} 길**\n\n"
                f"베팅 범위: {BJ_MIN_BET} ~ {BJ_MAX_BET} 길"
            ),
            color=0x228833
        )
        embed.set_footer(text="…진짜 카지노 들어온 느낌이지?")

        view = BlackjackBetView(uid)
        await interaction.response.edit_message(embed=embed, view=view)


class SlotBetView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("네 돈 아니잖아?", ephemeral=True)
            return False
        return True

    @discord.ui.select(
        placeholder="베팅 금액 선택",
        options=[
            discord.SelectOption(label="100 길"),
            discord.SelectOption(label="500 길"),
            discord.SelectOption(label="1000 길"),
            discord.SelectOption(label="5000 길"),
        ]
    )
    async def select_bet(self, interaction: discord.Interaction, select: discord.ui.Select):
        bet = int(select.values[0].split()[0])
        await start_slot_spin(interaction, self.user_id, bet)


class BaccaratBetView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("네 돈 아니잖아?", ephemeral=True)
            return False
        return True

    @discord.ui.select(
        placeholder="베팅 금액 선택",
        options=[
            discord.SelectOption(label="100 길"),
            discord.SelectOption(label="500 길"),
            discord.SelectOption(label="1000 길"),
            discord.SelectOption(label="5000 길"),
        ]
    )
    async def select_bet(self, interaction: discord.Interaction, select: discord.ui.Select):
        bet = int(select.values[0].split()[0])

        data = get_user(self.user_id)
        money = data.get("money", 0)
        if money < bet:
            return await interaction.response.send_message("돈 없는데 어디다 걸려고.", ephemeral=True)

        embed = discord.Embed(
            title="🎴 바카라 - 베팅 종류 선택",
            description=(
                f"베팅 금액: **{bet} 길**\n\n"
                "어디에 걸래?\n"
                "플레이어 / 뱅커 / 타이 / 페어"
            ),
            color=0xAA2233
        )
        bet_type_view = BaccaratTypeView(self.user_id, bet)
        await interaction.response.edit_message(embed=embed, view=bet_type_view)


class BaccaratTypeView(discord.ui.View):
    def __init__(self, user_id: int, bet: int):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.bet = bet

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("네 판 아니잖아.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="플레이어 (2배)", style=discord.ButtonStyle.primary)
    async def bet_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        await start_baccarat_game(interaction, self.user_id, self.bet, "player")

    @discord.ui.button(label="뱅커 (1.5배)", style=discord.ButtonStyle.success)
    async def bet_banker(self, interaction: discord.Interaction, button: discord.ui.Button):
        await start_baccarat_game(interaction, self.user_id, self.bet, "banker")

    @discord.ui.button(label="타이 (9배)", style=discord.ButtonStyle.secondary)
    async def bet_tie(self, interaction: discord.Interaction, button: discord.ui.Button):
        await start_baccarat_game(interaction, self.user_id, self.bet, "tie")

    @discord.ui.button(label="페어 (12배)", style=discord.ButtonStyle.danger)
    async def bet_pair(self, interaction: discord.Interaction, button: discord.ui.Button):
        await start_baccarat_game(interaction, self.user_id, self.bet, "pair")


# ================================
# COG
# ================================

class GamblingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="도박", description="체랑이 있는 도박장에 들어간다.")
    async def gambling_menu(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        embed = discord.Embed(
            title="🎰 도박장 입장",
            description="어떤 게임을 할래?",
            color=0xFFD700
        )
        embed.set_footer(text="…돈 잃고 울지만 마. 위로는 해줄 수도 있으니까.")

        view = GameSelectView(user_id)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(GamblingCog(bot))
    print("🎲 GamblingCog Loaded!")

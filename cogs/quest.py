# cogs/quest.py

import random
from datetime import datetime

import discord
from discord.ext import commands
from discord import app_commands

from utils.user_api import (
    get_user,
    update_user,
    add_money,
    add_love,
)

# ==========================
# 기본 설정
# ==========================

DATE_FMT = "%Y-%m-%d"


def today_str() -> str:
    return datetime.now().strftime(DATE_FMT)


# ==========================
# 일일 퀘스트 템플릿
# ==========================
# trigger: 내부에서 사용하는 행동 키
# target : 필요한 횟수
# money / love : 보상

DAILY_TEMPLATES = [
    {
        "id": "work_once",
        "trigger": "work",
        "name": "🧹 일하기 / 채집 1회",
        "desc": "!일하기 또는 !채집 한 번 하기",
        "target": 1,
        "money": 200,
        "love": 1,
    },
    {
        "id": "gather_3",
        "trigger": "gather",
        "name": "🌿 채집 3회",
        "desc": "!채집 세 번 다녀오기",
        "target": 3,
        "money": 400,
        "love": 2,
    },
    {
        "id": "gamble_1",
        "trigger": "gamble",
        "name": "🎰 도박장 이용 1회",
        "desc": "/도박으로 체랑 도박장 한 번 들어가기",
        "target": 1,
        "money": 300,
        "love": 0,
    },
    {
        "id": "craft_1",
        "trigger": "craft",
        "name": "🛠 제작 1회",
        "desc": "!제작으로 아이템 하나 만들기",
        "target": 1,
        "money": 0,
        "love": 3,
    },
    {
        "id": "weather_1",
        "trigger": "weather",
        "name": "🌦 날씨 확인",
        "desc": "/날씨로 오늘 기상 확인하기",
        "target": 1,
        "money": 100,
        "love": 1,
    },
    {
        "id": "love_1",
        "trigger": "love",
        "name": "❤️ 체랑 호감도 확인",
        "desc": "/호감도로 체랑과의 관계 한 번 보기",
        "target": 1,
        "money": 0,
        "love": 2,
    },
    {
        "id": "inventory_1",
        "trigger": "inventory",
        "name": "🎒 인벤 열어보기",
        "desc": "!인벤으로 인벤토리 확인",
        "target": 1,
        "money": 100,
        "love": 0,
    },
]


# ==========================
# 업적 정의
# ==========================
# stat: stats[stat] 누적 값 기준

ACHIEVEMENTS = {
    "worker_20": {
        "name": "노동의 노예",
        "desc": "일하기 / 채집 합산 20회 달성",
        "stat": "work",
        "target": 20,
        "money": 1000,
        "love": 5,
    },
    "gambler_10": {
        "name": "적당히 놀 줄 아는 손님",
        "desc": "도박장 10회 이용",
        "stat": "gamble",
        "target": 10,
        "money": 1500,
        "love": 0,
    },
    "crafter_10": {
        "name": "손재주 좋은 모험가",
        "desc": "제작 10회 완료",
        "stat": "craft",
        "target": 10,
        "money": 800,
        "love": 3,
    },
    "weather_10": {
        "name": "기상 관측 매니아",
        "desc": "날씨 확인 10회",
        "stat": "weather",
        "target": 10,
        "money": 500,
        "love": 2,
    },
    "love_50": {
        "name": "집요한 집착가",
        "desc": "체랑 호감도 확인 50회",
        "stat": "love",
        "target": 50,
        "money": 0,
        "love": 10,
    },
}


# ==========================
# 내부 헬퍼
# ==========================

def _get_quest_data(user_id: int) -> dict:
    """유저 데이터 안에 quests 블록 보장"""
    data = get_user(user_id)
    q = data.get("quests")
    if not isinstance(q, dict):
        q = {}
        data["quests"] = q
        update_user(user_id, data)
    return q


def _save_quest_data(user_id: int, q: dict):
    data = get_user(user_id)
    data["quests"] = q
    update_user(user_id, data)


def _ensure_daily(user_id: int) -> dict:
    """일일 퀘스트 없거나 날짜 바뀌었으면 새로 뽑기"""
    q = _get_quest_data(user_id)
    daily = q.get("daily")
    today = today_str()

    if not daily or daily.get("date") != today:
        # 오늘자 일일 퀘스트 새로 구성 (3개 랜덤)
        templates = DAILY_TEMPLATES[:]
        random.shuffle(templates)
        chosen = templates[:3]

        daily = {
            "date": today,
            "list": [],
        }
        for t in chosen:
            daily["list"].append(
                {
                    "id": t["id"],
                    "trigger": t["trigger"],
                    "name": t["name"],
                    "desc": t["desc"],
                    "target": t["target"],
                    "progress": 0,
                    "money": t["money"],
                    "love": t["love"],
                    "done": False,
                    "rewarded": False,
                }
            )
        q["daily"] = daily
        _save_quest_data(user_id, q)

    return daily


def _get_stats(user_id: int) -> dict:
    q = _get_quest_data(user_id)
    stats = q.get("stats")
    if not isinstance(stats, dict):
        stats = {}
        q["stats"] = stats
        _save_quest_data(user_id, q)
    return stats


def _get_achievements(user_id: int) -> dict:
    q = _get_quest_data(user_id)
    ach = q.get("achievements")
    if not isinstance(ach, dict):
        ach = {}
        q["achievements"] = ach
        _save_quest_data(user_id, q)
    return ach


def _increment_stat(user_id: int, stat: str, amount: int = 1):
    """stats[stat] 증가 + 업적 체크 + 일일 퀘스트 진행도 반영"""
    q = _get_quest_data(user_id)
    stats = q.get("stats")
    if not isinstance(stats, dict):
        stats = {}
        q["stats"] = stats

    stats[stat] = stats.get(stat, 0) + amount

    # 업적 체크
    achs = q.get("achievements")
    if not isinstance(achs, dict):
        achs = {}
        q["achievements"] = achs

    for ach_id, meta in ACHIEVEMENTS.items():
        req_stat = meta["stat"]
        target = meta["target"]

        if req_stat != stat:
            continue

        cur = stats.get(req_stat, 0)
        state = achs.get(ach_id) or {"done": False, "rewarded": False}

        if not state.get("done") and cur >= target:
            # 업적 달성 + 보상 지급
            state["done"] = True
            if not state.get("rewarded"):
                money = meta.get("money", 0)
                love = meta.get("love", 0)
                if money:
                    add_money(user_id, money)
                if love:
                    add_love(user_id, love)
                state["rewarded"] = True
            achs[ach_id] = state

    q["stats"] = stats
    q["achievements"] = achs
    _save_quest_data(user_id, q)


def _update_daily_progress(user_id: int, trigger: str):
    """행동 트리거에 따라 일일 퀘스트 진행도 업데이트"""
    q = _get_quest_data(user_id)
    daily = _ensure_daily(user_id)  # 날짜 보정 포함
    changed = False

    for quest in daily.get("list", []):
        if quest.get("trigger") != trigger:
            continue
        if quest.get("done"):
            continue

        quest["progress"] = quest.get("progress", 0) + 1
        if quest["progress"] >= quest["target"]:
            quest["done"] = True

            # 보상 지급 (자동)
            if not quest.get("rewarded"):
                money = quest.get("money", 0)
                love = quest.get("love", 0)
                if money:
                    add_money(user_id, money)
                if love:
                    add_love(user_id, love)
                quest["rewarded"] = True
        changed = True

    if changed:
        q["daily"] = daily
        _save_quest_data(user_id, q)


# ==========================
# Embed 빌더
# ==========================

def build_daily_embed(user: discord.abc.User) -> discord.Embed:
    daily = _ensure_daily(user.id)
    date = daily.get("date", today_str())
    quests = daily.get("list", [])

    if not quests:
        desc = "오늘은 줄 게 없나 봐."
    else:
        lines = []
        for q in quests:
            done = q.get("done", False)
            progress = q.get("progress", 0)
            target = q.get("target", 1)
            rewarded = q.get("rewarded", False)

            status = "✅ 완료" if done else "⏳ 진행 중"
            if done and rewarded:
                status += " / 보상 지급 완료"

            line = (
                f"**{q['name']}**\n"
                f"> {q['desc']}\n"
                f"> 진행도: {progress} / {target} — {status}"
            )
            reward_txt = []
            if q.get("money"):
                reward_txt.append(f"{q['money']} 길")
            if q.get("love"):
                reward_txt.append(f"호감도 {q['love']}")

            if reward_txt:
                line += f"\n> 보상: {', '.join(reward_txt)}"

            lines.append(line)

        desc = "\n\n".join(lines)

    embed = discord.Embed(
        title=f"🎯 {user.display_name} — 오늘의 일일 퀘스트",
        description=desc,
        color=0xF1C40F,
    )
    embed.set_footer(text=f"{date} 기준 — 자, 얼른 해.")
    return embed


def build_achievement_embed(user: discord.abc.User) -> discord.Embed:
    stats = _get_stats(user.id)
    achs = _get_achievements(user.id)

    lines = []
    for ach_id, meta in ACHIEVEMENTS.items():
        name = meta["name"]
        desc = meta["desc"]
        stat = meta["stat"]
        target = meta["target"]
        cur = stats.get(stat, 0)
        state = achs.get(ach_id) or {"done": False, "rewarded": False}

        done = state.get("done", False)
        rewarded = state.get("rewarded", False)

        if done and rewarded:
            status = "🏅 달성 / 보상 수령"
        elif done and not rewarded:
            status = "🏆 달성 / 보상 미지급 (자동 지급 대상인데… 뭔가 꼬였을지도?)"
        else:
            status = "⏳ 진행 중"

        reward_parts = []
        if meta.get("money"):
            reward_parts.append(f"{meta['money']} 길")
        if meta.get("love"):
            reward_parts.append(f"호감도 {meta['love']}")

        reward_txt = ", ".join(reward_parts) if reward_parts else "없음"

        line = (
            f"**{name}**\n"
            f"> {desc}\n"
            f"> 진행도: {cur} / {target} — {status}\n"
            f"> 보상: {reward_txt}"
        )
        lines.append(line)

    if not lines:
        desc = "아직 달성한 업적이 없네. 뭐, 그럴 수도 있지."
    else:
        desc = "\n\n".join(lines)

    embed = discord.Embed(
        title=f"🏆 {user.display_name} — 업적 현황",
        description=desc,
        color=0x9B59B6,
    )
    embed.set_footer(text="…생각보다 열심히네.")
    return embed


# ==========================
# UI View
# ==========================

class QuestMainView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "네 퀘스트 창 아니잖아.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="🎯 일일 퀘스트", style=discord.ButtonStyle.primary)
    async def daily_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = build_daily_embed(interaction.user)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🏆 업적 보기", style=discord.ButtonStyle.secondary)
    async def achievement_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = build_achievement_embed(interaction.user)
        await interaction.response.edit_message(embed=embed, view=self)


# ==========================
# Cog
# ==========================

class QuestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # /퀘스트 — 메인 UI
    @app_commands.command(name="퀘스트", description="일일 퀘스트와 업적 현황을 확인합니다.")
    async def quest(self, interaction: discord.Interaction):
        user = interaction.user
        # 일일 퀘스트를 기본 화면으로
        _ensure_daily(user.id)
        embed = build_daily_embed(user)
        view = QuestMainView(user.id)
        await interaction.response.send_message(embed=embed, view=view)

    # ==========================
    #   트리거 감지
    # ==========================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """프리픽스 기반 명령 감지 (!일하기 / !채집 / !제작 / !인벤 등)"""
        if message.author.bot:
            return
        content = message.content.strip()
        if not content.startswith("!"):
            return

        cmd = content.split()[0]

        uid = message.author.id

        if cmd in ("!일하기", "!채집"):
            # 일하기 계열 — work / gather 둘 다 work 누적에도 더해줌
            _increment_stat(uid, "work", 1)
            if cmd == "!채집":
                _increment_stat(uid, "gather", 1)
            _update_daily_progress(uid, "work")
            if cmd == "!채집":
                _update_daily_progress(uid, "gather")

        elif cmd == "!제작":
            _increment_stat(uid, "craft", 1)
            _update_daily_progress(uid, "craft")

        elif cmd == "!인벤":
            _increment_stat(uid, "inventory", 1)
            _update_daily_progress(uid, "inventory")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """
        슬래시 커맨드 기반 트리거 감지 (/도박, /날씨, /호감도 등)
        """
        if interaction.type != discord.InteractionType.application_command:
            return
        if not interaction.user or interaction.user.bot:
            return

        data = interaction.data or {}
        name = data.get("name")
        if not isinstance(name, str):
            return

        uid = interaction.user.id

        if name == "도박":
            _increment_stat(uid, "gamble", 1)
            _update_daily_progress(uid, "gamble")
        elif name == "날씨":
            _increment_stat(uid, "weather", 1)
            _update_daily_progress(uid, "weather")
        elif name == "호감도":
            _increment_stat(uid, "love", 1)
            _update_daily_progress(uid, "love")


async def setup(bot):
    await bot.add_cog(QuestCog(bot))
    print("🎯 QuestCog Loaded!")

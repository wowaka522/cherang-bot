# cogs/ai_chat.py
import os
import json
import random
import asyncio
from datetime import datetime
from pathlib import Path

import discord
import requests
from discord.ext import commands
from dotenv import load_dotenv

from utils.love_db import change_user_love, get_user_love
from utils.text_cleaner import extract_item_name, extract_city_name

load_dotenv()

AI_CHAT_CHANNEL_ID = int(os.getenv("AI_CHAT_CHANNEL_ID", "0"))
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

BAD_WORDS = ["시발", "씨발", "병신", "ㅅㅂ", "fuck"]
GOOD_WORDS = ["고마워", "사랑해", "좋아해", "예쁘네", "귀여워"]

DAILY_LIMIT = 50
USAGE_PATH = Path("data") / "ai_chat_usage.json"

LAST_CHAT_TIME = {}
IS_WAITING = set()


def _load_usage():
    USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not USAGE_PATH.exists():
        return {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0}
    try:
        return json.loads(USAGE_PATH.read_text("utf-8"))
    except Exception:
        return {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0}


def _save_usage(data: dict):
    USAGE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def can_use_ai() -> bool:
    today = datetime.now().strftime("%Y-%m-%d")
    data = _load_usage()
    if data.get("date") != today:
        data = {"date": today, "count": 0}
        _save_usage(data)
        return True
    return data.get("count", 0) < DAILY_LIMIT


def inc_usage():
    today = datetime.now().strftime("%Y-%m-%d")
    data = _load_usage()
    if data.get("date") != today:
        data = {"date": today, "count": 0}
    data["count"] = data.get("count", 0) + 1
    _save_usage(data)


def call_deepseek_reply(user_name: str, content: str, love: int, tone: str) -> str:
    if not DEEPSEEK_API_KEY:
        return "지금은 대답하기 힘들어. 나중에 불러."

    system_prompt = (
        "너는 '체랑봇'이고 고양이 수인 느낌의 쿨데레.\n"
        "한국어로 짧고 시니컬하게 답해.\n"
        "이모지 금지, 이름 부르지 마.\n"
        "욕 먹으면 욱하고, 칭찬 받으면 티 안 내며 살짝 기뻐해.\n"
    )

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        "max_tokens": 300,
    }

    if tone == "angry":
        payload["messages"].append({"role": "system", "content": "지금 너 기분 안 좋음"})
    elif tone == "happy":
        payload["messages"].append({"role": "system", "content": "기분 좋음. 다 티 내진 마"})

    try:
        r = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json=payload,
            timeout=12,
        )
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except:
        return "잠깐 멍해졌어. 다시 말해."


async def call_deepseek_proactive(love: int) -> str:
    """먼저 말 걸기 멘트 생성"""
    if not DEEPSEEK_API_KEY:
        return "…아무것도 아냐. 그냥."

    system_prompt = (
        "너는 '체랑봇'이고 쿨데레 고양이 수인 느낌.\n"
        "상대에게 먼저 말 걸려고 하는 상황.\n"
        "관심 없는 척, 건조하고 시니컬.\n"
        "한 문장으로만. 이모지 금지. 멘션 금지.\n"
    )

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "assistant",
                "content": f"(상대 호감도: {love})\n짧게 한 문장 만들어."
            },
        ],
        "max_tokens": 50,
    }

    try:
        r = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json=payload,
            timeout=10,
        )
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except:
        fallback = [
            "뭐야, 갑자기 잠수?",
            "말 안 하면… 나 심심한데.",
            "한마디도 안 해?",
            "대답해도 되고. 말고.",
            "왜 아무 말 없어."
        ]
        return random.choice(fallback)


# 아래 코드가 AIChatCog 클래스 안에 위치해야 합니다.
class AIChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _maybe_start_chat(self, channel: discord.TextChannel, user: discord.Member, love: int):
        if love < 10:
            return
        if user.id in IS_WAITING:
            return
        if channel.id != AI_CHAT_CHANNEL_ID:
            return

        if random.random() > 0.05:  # 5% 확률
            return

        IS_WAITING.add(user.id)
        await asyncio.sleep(random.randint(300, 600))  # 5~10분

        data = LAST_CHAT_TIME.get(user.id)
        if not data:
            IS_WAITING.discard(user.id)
            return

        channel_id, last_ts = data
        if channel_id != channel.id:
            IS_WAITING.discard(user.id)
            return

        msg = await call_deepseek_proactive(love)
        await channel.send(f"{user.mention} {msg}")

        IS_WAITING.discard(user.id)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return
        if msg.channel.id != AI_CHAT_CHANNEL_ID:
            return

        content = msg.content.strip()
        uid = str(msg.author.id)
        lowered = content.lower()

        # 자연어 명령어는 bot.py에서 처리
        if any(w in lowered for w in ["시세", "얼마", "가격", "날씨", "기상", "어때"]):
            return

        # AI 처리
        delta = 0
        tone = "normal"
        if any(b in lowered for b in BAD_WORDS):
            delta -= 2
            tone = "angry"
        if any(g in lowered for g in GOOD_WORDS):
            delta += 1
            tone = "happy" if tone != "angry" else "angry"

        change_user_love(uid, delta)
        love = get_user_love(uid)

        use_ai = can_use_ai()
        mention_prefix = msg.author.mention + " " if love >= 10 else ""

        if not use_ai:
            reply = "오늘은 여기까지. 내일 다시 불러."
        else:
            inc_usage()
            reply = call_deepseek_reply(msg.author.display_name, content, love, tone)

        await msg.reply(f"{mention_prefix}{reply}", mention_author=False)

        LAST_CHAT_TIME[msg.author.id] = (msg.channel.id, datetime.utcnow().timestamp())
        self.bot.loop.create_task(self._maybe_start_chat(msg.channel, msg.author, love))


async def setup(bot):
    await bot.add_cog(AIChatCog(bot))

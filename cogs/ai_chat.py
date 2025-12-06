# cogs/ai_chat.py
import os
import json
import random
import asyncio
from datetime import datetime
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests

from utils.love_db import change_user_love, get_user_love

load_dotenv()

AI_CHAT_CHANNEL_ID = int(os.getenv("AI_CHAT_CHANNEL_ID", "0"))
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

BAD_WORDS = ["시발", "씨발", "병신", "ㅅㅂ", "fuck"]
GOOD_WORDS = ["고마워", "사랑해", "좋아해", "예쁘네", "귀여워"]

DAILY_LIMIT = 50
USAGE_PATH = Path("data") / "ai_chat_usage.json"

LAST_CHAT_TIME: dict[int, tuple[int, float]] = {}
IS_WAITING = set()


def _load_usage():
    USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not USAGE_PATH.exists():
        return {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0}
    try:
        return json.loads(USAGE_PATH.read_text("utf-8"))
    except:
        return {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0}


def _save_usage(data: dict):
    USAGE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def can_use_ai():
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
    if not DEEPSEEK_API_KEY:
        return "…아무것도 아냐. 그냥."

    prompts = [
        "너는 '체랑봇'이고 쿨데레 고양이 수인 느낌.\n"
        "관심 없는 척, 건조하고 시니컬.\n"
        "먼저 말 거는 상황. 한 문장.\n"
        "이모지 금지. 멘션 금지.\n"
    ]

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": prompts[0]},
            {
                "role": "assistant",
                "content": f"(상대 호감도: {love})\n짧고 툭 던지는 한 문장."
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
            "말 안 해?",
            "왜 가만히 있어.",
            "…뭐.",
            "심심한데.",
        ]
        return random.choice(fallback)


class AIChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def handle_ai_chat(self, message: discord.Message):
        if message.author.bot:
            return True  # 처리로 간주

        content = message.content.strip()
        lowered = content.lower()

        uid = str(message.author.id)
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

        if not can_use_ai():
            reply = "오늘은 여기까지. 내일 다시 불러."
        else:
            inc_usage()
            reply = call_deepseek_reply(message.author.display_name, content, love, tone)

        mention_prefix = message.author.mention + " " if love >= 10 else ""
        await message.reply(f"{mention_prefix}{reply}", mention_author=False)

        LAST_CHAT_TIME[message.author.id] = (message.channel.id, datetime.utcnow().timestamp())
        self.bot.loop.create_task(call_deepseek_proactive(love))
        return True


async def setup(bot: commands.Bot):
    await bot.add_cog(AIChatCog(bot))

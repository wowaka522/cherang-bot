# cogs/ai_chat.py
import os
import json
import random
import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path

import discord
import requests
from discord.ext import commands
from dotenv import load_dotenv

print("📍 ai_chat.py imported")

from utils.love_db import change_user_love, get_user_love

load_dotenv()

AI_CHAT_CHANNEL_ID = int(os.getenv("AI_CHAT_CHANNEL_ID", "0"))
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

BAD_WORDS = ["시발", "씨발", "병신", "ㅅㅂ", "fuck"]
GOOD_WORDS = ["고마워", "사랑해", "좋아해", "예쁘네", "귀여워"]

# .env 없으면 기본 50
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "50"))
USAGE_PATH = Path("data") / "ai_chat_usage.json"

LAST_CHAT_TIME: dict[int, tuple[int, float]] = {}
IS_WAITING: set[int] = set()

# ==========================
# 말걸기 대화모드 상태
# ==========================

TALK_MAX_COUNT = 10           # AI가 10번 답하면 자동 종료
TALK_COOLDOWN = 60 * 60 * 6   # 6시간 쿨타임
# { user_id: {"active": bool, "count": int, "started_at": float} }
TALK_STATE: dict[int, dict] = {}

# ==========================
# 음악 추천용 간단 풀
# ==========================

MUSIC_RECOMMEND_RATE = 1 / 30  # 대충 30마디에 한 번 정도

SONG_POOL = [
    {
        "title": "못 죽는 기사와 비단 요람",
        "artist": "LUCY",
        "url": "https://youtu.be/y7jrpS8GHxs",
    },
    {
        "title": "추천곡 1",
        "artist": "",
        "url": "https://music.youtube.com/watch?v=CI2jytCXNqE&si=-LoKhP1BGwPYPXiR",
    },
    {
        "title": "추천곡 2",
        "artist": "",
        "url": "https://music.youtube.com/watch?v=Sj0q515EOM8&si=x7bhjx_YfEgdbu9_",
    },
    {
        "title": "추천곡 3",
        "artist": "",
        "url": "https://music.youtube.com/watch?v=LGJq1ITmfSs&si=vVTu0VohxvW1zQGe",
    },
    {
        "title": "추천곡 4",
        "artist": "",
        "url": "https://music.youtube.com/watch?v=uQDzdXse59Y&si=jaCZkdPutSaZ4dd2",
    },
    {
        "title": "추천곡 5",
        "artist": "",
        "url": "https://music.youtube.com/watch?v=QytVOi6H_ys&si=nA2RYMi-5jw6IGCn",
    },
    {
        "title": "추천곡 6",
        "artist": "",
        "url": "https://music.youtube.com/watch?v=HLMekAvGvOE&si=Wi17BbBTDmSymmvy",
    },
]


# ==========================
# 공용 유틸
# ==========================

def _load_usage():
    USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    if not USAGE_PATH.exists():
        data = {"date": today, "count": 0}
        _save_usage(data)
        return data

    try:
        data = json.loads(USAGE_PATH.read_text("utf-8"))
        if "date" not in data or "count" not in data:
            raise ValueError("invalid usage json")
        return data
    except Exception as e:
        print("⚠️ ai_chat_usage.json 오류, 초기화:", e)
        data = {"date": today, "count": 0}
        _save_usage(data)
        return data


def _save_usage(data: dict):
    USAGE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        "utf-8",
    )


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


def get_kst_hour() -> int:
    """한국 시간 기준 현재 시각 hour"""
    return (datetime.utcnow() + timedelta(hours=9)).hour


def time_tone_text() -> str:
    """시간대에 따른 말투 안내(시스템 프롬프트용 짧은 텍스트)"""
    h = get_kst_hour()
    if 7 <= h < 12:
        return "지금은 아침이고, 너는 엄청 졸리고 예민한 상태야."
    if 12 <= h < 18:
        return "지금은 낮이라 대충 적당히 시니컬하게 응답해."
    if 18 <= h < 23:
        return "지금은 저녁이고, 좀 더 말이 많아지고 장난도 섞이는 시간대야."
    if 23 <= h or h < 3:
        return "지금은 밤이니까 살짝 나긋나긋하고 감정이 묻어나게 말해."
    return "새벽이라 피곤하지만, 속마음이 살짝 새어나오는 느낌으로 말해."


def end_message_by_time() -> str:
    """대화 10회 종료 멘트 (시간대에 따라)"""
    h = get_kst_hour()
    if 7 <= h < 12:
        choices = [
            "그만 좀 괴롭혀. 아침엔 말 시키지 말라니까.",
            "됐어. 낮잠이나 잘 거니까 꺼져.",
        ]
    elif 12 <= h < 18:
        choices = [
            "오늘은 여기까지. 할 일도 없냐 너.",
            "흥. 이제 끝. 나 바쁘다고.",
        ]
    elif 18 <= h < 23:
        choices = [
            "오늘은 여기까지… 뭐, 나쁘진 않았어.",
            "됐어. 이 정도면 충분하잖아.",
        ]
    else:
        choices = [
            "너도 쉬어. …난 좀 더 깨어있을게.",
            "…됐어. 집에 가. 아니, 채팅 끄라고.",
            "이제 자라. 내가 그렇게까지 한가하진 않아.",
        ]
    return random.choice(choices)


def music_line_by_time() -> str:
    """노래 추천 앞에 붙는 멘트"""
    h = get_kst_hour()
    if 7 <= h < 12:
        return "아침에 시끄러운 건 싫은데… 이건 괜찮을지도."
    if 12 <= h < 18:
        return "심심하면, 이 정도는 들어봐도 되잖아."
    if 18 <= h < 23:
        return "너라면 이런 분위기 좋아할 것 같아서."
    return "이 시간엔… 이런 거 한 곡쯤은 괜찮지."


# ==========================
# 대화모드 제어 함수 (love.py에서 사용)
# ==========================

def can_start_talk_mode(user_id: int) -> tuple[bool, int]:
    """
    대화모드 시작 가능 여부, 남은 쿨타임(초)
    True, 0 이면 바로 가능
    """
    state = TALK_STATE.get(user_id)
    if not state:
        return True, 0

    started_at = state.get("started_at", 0)
    elapsed = time.time() - started_at

    if elapsed >= TALK_COOLDOWN:
        return True, 0

    remain = int(TALK_COOLDOWN - elapsed)
    # active 여부와 상관없이, 쿨타임 안이면 막는다
    return False, remain


def start_talk_mode(user_id: int):
    TALK_STATE[user_id] = {
        "active": True,
        "count": 0,
        "started_at": time.time(),
    }


def is_talk_active(user_id: int) -> bool:
    return TALK_STATE.get(user_id, {}).get("active", False)


# ==========================
# DeepSeek 호출
# ==========================

def call_deepseek_reply(user_name: str, content: str, love: int, tone: str) -> str:
    if not DEEPSEEK_API_KEY:
        return "지금은 대답하기 힘들어. 나중에 불러."

    base_system = (
        "너는 '체랑봇'이고 고양이 수인 느낌의 쿨데레.\n"
        "한국어로 짧고 시니컬하게 답해.\n"
        "이모지 금지, 이름 부르지 마.\n"
        "욕 먹으면 욱하고, 칭찬 받으면 티 안 내며 살짝 기뻐해.\n"
    )
    time_hint = time_tone_text()

    system_prompt = base_system + "\n" + time_hint

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
    ]

    if tone == "angry":
        messages.append({"role": "system", "content": "지금 너 기분 안 좋음. 말투에 짜증을 조금 섞어."})
    elif tone == "happy":
        messages.append({"role": "system", "content": "기분 좋지만 다 티 내지 말고 살짝만 드러내."})

    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "max_tokens": 300,
    }

    try:
        r = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json=payload,
            timeout=12,
        )
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("⚠️ DeepSeek 호출 실패:", e)
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
    except Exception as e:
        print("⚠️ DeepSeek proactive 실패:", e)
        fallback = [
            "뭐야, 갑자기 잠수?",
            "말 안 하면… 나 심심한데.",
            "한마디도 안 해?",
            "대답해도 되고. 말고.",
            "왜 아무 말 없어.",
        ]
        return random.choice(fallback)


async def maybe_send_music(channel: discord.TextChannel):
    """작게 확률로 음악 추천 임베드"""
    if random.random() > MUSIC_RECOMMEND_RATE:
        return

    song = random.choice(SONG_POOL)
    title = song.get("title") or "추천 곡"
    artist = song.get("artist") or ""
    url = song["url"]

    line = music_line_by_time()
    desc = f"[{title}]({url})"
    if artist:
        desc += f"\n{artist}"

    embed = discord.Embed(
        title="🎧 체랑 추천곡",
        description=desc,
        color=0x5865F2,
    )
    embed.set_footer(text="…듣든 말든 네 마음.")

    await channel.send(line, embed=embed)


# ==========================
# Cog
# ==========================

class AIChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _maybe_start_chat(self, channel: discord.TextChannel, user: discord.Member, love: int):
        # 기존 '먼저 말걸기' 로직 (원하면 나중에 조정)
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
        # AI 대화/대화모드 처리
        if msg.author.bot:
            return
        if msg.channel.id != AI_CHAT_CHANNEL_ID:
            return

        print("🔥 AIChatCog fired")

        uid = msg.author.id
        content = msg.content.strip()
        lowered = content.lower()

        # -------------------------------
        # 1) 말걸기 대화모드 우선 처리
        # -------------------------------
        state = TALK_STATE.get(uid)
        if state and state.get("active", False):
            # 10회 제한 체크
            if state.get("count", 0) >= TALK_MAX_COUNT:
                # 혹시 남아있으면 정리
                state["active"] = False
                return

            # 욕/칭찬에 따라 호감도 변화 + tone 결정
            tone = "normal"
            delta = 0
            if any(b in lowered for b in BAD_WORDS):
                delta -= 2
                tone = "angry"
            if any(g in lowered for g in GOOD_WORDS):
                delta += 1
                if tone != "angry":
                    tone = "happy"

            # 약간의 랜덤 호감도 보너스
            extra = random.randint(0, 3)
            delta += extra

            uid_str = str(uid)
            if delta != 0:
                change_user_love(uid_str, delta)
            love = get_user_love(uid_str)

            if not can_use_ai():
                reply = "오늘은 여기까지. 내일 다시 불러."
            else:
                inc_usage()
                reply = call_deepseek_reply(msg.author.display_name, content, love, tone)

            # 멘션 없이 자연스럽게
            await msg.channel.send(reply)

            # 카운트 증가
            state["count"] = state.get("count", 0) + 1

            # 가끔 음악 추천
            await maybe_send_music(msg.channel)

            # 10회 도달 시 종료
            if state["count"] >= TALK_MAX_COUNT:
                end_msg = end_message_by_time()
                await msg.channel.send(end_msg)
                state["active"] = False

            # 마지막 대화시간 기록 (먼저 말걸기용)
            LAST_CHAT_TIME[uid] = (msg.channel.id, datetime.utcnow().timestamp())
            return

        # -------------------------------
        # 2) 말걸기 모드가 아닐 때 → 기존 트리거 기반
        # -------------------------------
        # 시세/날씨/기상 관련이면 이쪽은 무시 (다른 봇용)
        if any(w in lowered for w in ["시세", "얼마", "가격", "날씨", "기상", "어때"]):
            return

        TRIGGERS = ["체랑", "체랑봇", "체랑냥", "냥이"]
        if not any(w in lowered for w in TRIGGERS):
            return

        uid_str = str(uid)

        delta = 0
        tone = "normal"
        if any(b in lowered for b in BAD_WORDS):
            delta -= 2
            tone = "angry"
        if any(g in lowered for g in GOOD_WORDS):
            delta += 1
            tone = "happy" if tone != "angry" else "angry"

        if delta != 0:
            change_user_love(uid_str, delta)
        love = get_user_love(uid_str)

        use_ai = can_use_ai()

        if not use_ai:
            reply = "오늘은 여기까지. 내일 다시 불러."
        else:
            inc_usage()
            reply = call_deepseek_reply(msg.author.display_name, content, love, tone)

        # 호감도 10 이상이면 멘션 한 번 넣는 것도 가능하지만
        # 지금은 자연스러운 톤 유지 위해 멘션 X
        try:
            await msg.reply(reply, mention_author=False)
            print("✅ reply sent (trigger mode)")
        except Exception as e:
            print("❌ Failed to send reply:", type(e).__name__, str(e))

        LAST_CHAT_TIME[uid] = (msg.channel.id, datetime.utcnow().timestamp())
        # 필요하면 여기서도 maybe_start_chat 호출 가능
        self.bot.loop.create_task(self._maybe_start_chat(msg.channel, msg.author, love))


async def setup(bot):
    await bot.add_cog(AIChatCog(bot))
    print("🧠 AIChatCog Loaded!")

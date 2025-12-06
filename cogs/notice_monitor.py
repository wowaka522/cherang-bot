import os
import re
import requests
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime, time

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

NOTICE_URL = "https://www.ff14.co.kr/news/notice"
EVENT_URL = "https://www.ff14.co.kr/news/event"  # 이벤트 공지 URL 추가
NOTICE_DATA_PATH = "data/last_notice_id.txt"
EVENT_DATA_PATH = "data/last_event_id.txt"  # 이벤트 공지 ID 저장 경로
NOTICE_CHANNEL_ID = int(os.getenv("NOTICE_CHANNEL_ID", "0"))

CHECK_TIMES = [time(12, 30)]  # 기본 체크: 12:30
UPDATE_DAY = 1  # 화요일 (월=0, 화=1 ...)
UPDATE_HOURS = range(9, 20, 1)  # 09 ~ 19 사이

class NoticeMonitorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_notice.start()

    def cog_unload(self):
        self.check_notice.cancel()

    def load_last_id(self, file_path: str) -> int:
        if os.path.exists(file_path):
            return int(open(file_path).read())
        return 0

    def save_last_id(self, file_path: str, nid: int):
        with open(file_path, "w") as f:
            f.write(str(nid))

    def fetch_latest_notice(self, url: str):
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "html.parser")

        first = soup.select_one(".news-list tbody tr")
        if not first:
            return None, None, None, None

        cols = first.find_all("td")
        notice_id = int(cols[0].text.strip())
        category = cols[1].text.strip()
        title = cols[2].text.strip()
        link_tag = cols[2].find("a")
        link = link_tag["href"] if link_tag else ""

        return notice_id, title, category, link

    @tasks.loop(minutes=30)
    async def check_notice(self):
        now = datetime.now()

        # 요일/시간 조건 체크
        if now.weekday() != UPDATE_DAY:
            # 평일 체크: 12:30만
            if not any(now.time().hour == t.hour and now.time().minute == t.minute for t in CHECK_TIMES):
                return
        else:
            # 패치날: 9~19시
            if now.hour not in UPDATE_HOURS:
                return

        # 공지와 이벤트 URL 각각 처리
        notice_id, title, category, link = self.fetch_latest_notice(NOTICE_URL)
        event_id, event_title, event_category, event_link = self.fetch_latest_notice(EVENT_URL)

        # 새 공지 및 이벤트 확인 후 처리
        last_notice_id = self.load_last_id(NOTICE_DATA_PATH)
        if notice_id and notice_id > last_notice_id:
            self.save_last_id(NOTICE_DATA_PATH, notice_id)
            await self.send_notification(notice_id, title, category, link)

        last_event_id = self.load_last_id(EVENT_DATA_PATH)
        if event_id and event_id > last_event_id:
            self.save_last_id(EVENT_DATA_PATH, event_id)
            await self.send_notification(event_id, event_title, event_category, event_link)

    async def send_notification(self, notice_id, title, category, link):
        # 알림 전송
        channel = self.bot.get_channel(NOTICE_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title=f"[{category}] {title}",
                description=f"**새 공지**가 올라왔어!",
                color=0xFFB301
            )
            embed.add_field(name="링크", value=f"https://www.ff14.co.kr{link}")
            embed.set_footer(text="📢 FF14 새 소식 알림")

            await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(NoticeMonitorCog(bot))

# views/ffxiv/tug_view.py
from __future__ import annotations

import time
import discord

from repositories.fish_alert_repo import FishAlert, FishAlertRepo
from services.ffxiv.tug_db import TugDB


def _format_remaining(now_ts: int, next_ts: int) -> str:
    sec = max(0, next_ts - now_ts)
    m = sec // 60
    if m <= 0:
        return "곧 시작!"
    return f"다음 기회까지 약 {m}분 남음"


class TugView(discord.ui.View):
    def __init__(self, bot, db: TugDB, alert_repo: FishAlertRepo, fish_id: int):
        super().__init__(timeout=120)
        self.bot = bot
        self.db = db
        self.alert_repo = alert_repo
        self.fish_id = fish_id

    @discord.ui.button(label="🔔 알림 받기", style=discord.ButtonStyle.primary)
    async def alert_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        disp = self.db.build_display(self.fish_id)
        if not disp:
            await interaction.response.send_message("❌ 알림 등록 실패 (데이터 없음)", ephemeral=True)
            return

        fish = disp.get("fish")
        spot = disp.get("spot")
        spot_key = disp.get("spot_key")

        if not fish or not spot or not spot_key:
            await interaction.response.send_message("❌ 알림 등록 실패 (위치/키 정보 없음)", ephemeral=True)
            return

        weather_service = getattr(self.bot, "weather_service", None)
        if not weather_service:
            await interaction.response.send_message(
                "❌ weather_service가 없어. (cogs.ffxiv.weather 로드 + WeatherCog에서 bot.weather_service 연결 필요)",
                ephemeral=True,
            )
            return

        now_ts = int(time.time())

        # Prefer: condition-based calculator
        next_ts = None
        if hasattr(weather_service, "get_next_window_ts_for_conditions"):
            try:
                next_ts = weather_service.get_next_window_ts_for_conditions(
                    zone_key=spot.territory,
                    prev_set=list(getattr(fish, "previous_weather", []) or []),
                    cur_set=list(getattr(fish, "weather", []) or []),
                    start_et=getattr(fish, "start", None),
                    end_et=getattr(fish, "end", None),
                )
            except Exception:
                next_ts = None

        # Fallback: generic API
        if not next_ts and hasattr(weather_service, "get_next_window_ts"):
            try:
                next_ts = weather_service.get_next_window_ts(fish_id=self.fish_id, spot_key=spot_key)
            except Exception:
                next_ts = None

        if not next_ts:
            await interaction.response.send_message(
                "❌ 다음 윈도우를 계산하지 못했어.\n"
                "• weather_service/get_next_window_ts_for_conditions 연결 확인\n"
                "• zone_key(territory) / 날씨 매핑(숫자↔영문) 확인",
                ephemeral=True,
            )
            return

        self.alert_repo.upsert(
            FishAlert(
                user_id=interaction.user.id,
                fish_id=self.fish_id,
                spot_key=spot_key,
                next_window_ts=int(next_ts),
            )
        )

        remain = _format_remaining(now_ts, int(next_ts))
        await interaction.response.send_message(f"✅ 알림 등록 완료! ({remain})", ephemeral=True)

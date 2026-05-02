# services/fish_alert_dispatcher.py
from __future__ import annotations

import asyncio
import time


class FishAlertDispatcher:
    def __init__(self, bot, alert_repo, tug_db: "TugDB"):
        self.bot = bot
        self.repo = alert_repo
        self.db = tug_db
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._running = False

        texts = getattr(bot, "texts", None)
        self.t = getattr(texts, "t", lambda k, **kw: k.format(**kw) if kw else k)

    def start(self):
        if self._task and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while self._running:
            try:
                await self.tick()
            except Exception:
                pass
            await asyncio.sleep(45)

    async def tick(self):
        async with self._lock:
            now_ts = int(time.time())
            due = self.repo.list_due(now_ts=now_ts)
            if not due:
                return

            for alert in due:
                try:
                    await self._notify_once(alert)
                finally:
                    # one-shot + auto delete (always)
                    self.repo.delete(alert)

    async def _notify_once(self, alert):
        disp = self.db.build_display(alert.fish_id)
        if not disp:
            return

        fish = disp["fish"]
        name = getattr(fish, "name_ko", None) or self.t("fish.alert.fallback_name", fish_id=alert.fish_id)
        loc = disp.get("location_line", "-")

        # ✅ 채널 고정 멘션
        try:
            ch = self.bot.get_channel(int(alert.channel_id))
            if ch is None:
                ch = await self.bot.fetch_channel(int(alert.channel_id))

            msg = self.t(
                "fish.alert.msg",
                user_id=int(alert.user_id),
                name=str(name),
                loc=str(loc),
            )
            await ch.send(msg)
        except Exception:
            # 채널 삭제/권한 없음 등: 그냥 드랍
            return
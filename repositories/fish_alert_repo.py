# repositories/fish_alert_repo.py
from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

from repositories.base_repo import BaseRepo


@dataclass
class FishAlert:
    user_id: int
    fish_id: int
    spot_key: str
    next_window_ts: int  # epoch seconds (UTC)
    channel_id: int      # ✅ 채널 고정 멘션용


class FishAlertRepo(BaseRepo):
    """
    저장 파일: <base_dir>/fish_alerts.json
    포맷:
      {"alerts":[{user_id, fish_id, spot_key, next_window_ts, channel_id}, ...]}
    """

    def __init__(self, base_dir: str = "data/ffxiv/fish/compiled"):
        super().__init__(base_dir)
        self.path = Path(base_dir) / "fish_alerts.json"

    def _load(self) -> dict:
        return self._load_json(self.path, default={"alerts": []})

    def _save(self, data: dict) -> None:
        self._atomic_save_json(self.path, data)

    def upsert(self, alert: FishAlert) -> None:
        data = self._load()
        alerts = data.get("alerts", [])

        for i, a in enumerate(alerts):
            if (
                int(a.get("user_id", -1)) == int(alert.user_id)
                and int(a.get("fish_id", -1)) == int(alert.fish_id)
                and str(a.get("spot_key", "")) == str(alert.spot_key)
                and int(a.get("channel_id", 0)) == int(alert.channel_id)
            ):
                alerts[i] = asdict(alert)
                data["alerts"] = alerts
                self._save(data)
                return

        alerts.append(asdict(alert))
        data["alerts"] = alerts
        self._save(data)

    def list_due(self, now_ts: Optional[int] = None) -> List[FishAlert]:
        now_ts = now_ts or int(time.time())
        data = self._load()

        out: List[FishAlert] = []
        for a in data.get("alerts", []):
            try:
                if int(a["next_window_ts"]) <= now_ts:
                    out.append(
                        FishAlert(
                            user_id=int(a["user_id"]),
                            fish_id=int(a["fish_id"]),
                            spot_key=str(a["spot_key"]),
                            next_window_ts=int(a["next_window_ts"]),
                            channel_id=int(a.get("channel_id") or 0),
                        )
                    )
            except Exception:
                continue
        return out

    def delete(self, alert: FishAlert) -> None:
        data = self._load()
        data["alerts"] = [
            a for a in data.get("alerts", [])
            if not (
                int(a.get("user_id", -1)) == int(alert.user_id)
                and int(a.get("fish_id", -1)) == int(alert.fish_id)
                and str(a.get("spot_key", "")) == str(alert.spot_key)
                and int(a.get("channel_id", 0)) == int(alert.channel_id)
            )
        ]
        self._save(data)
# services/ffxiv/market_service.py
from __future__ import annotations

import io
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

from services.http_client import HttpClient
from services.cache import TTLCache, RateLimiter


def format_price(n: int) -> str:
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)


_FONT_READY = False


def ensure_korean_font() -> None:
    global _FONT_READY
    if _FONT_READY:
        return

    font_path = "assets/fonts/NanumGothic-Regular.ttf"
    family_name = "NanumGothic"

    if os.path.exists(font_path):
        try:
            fm.fontManager.addfont(font_path)
            mpl.rcParams["font.family"] = family_name
        except Exception:
            pass

    mpl.rcParams["axes.unicode_minus"] = False
    _FONT_READY = True


def apply_chart_theme() -> None:
    # 기존 감성 유지(다크)
    mpl.rcParams["figure.facecolor"] = "#0b1020"
    mpl.rcParams["axes.facecolor"] = "#0f1630"
    mpl.rcParams["axes.edgecolor"] = "#d0d0d0"
    mpl.rcParams["axes.labelcolor"] = "#eaeaea"
    mpl.rcParams["text.color"] = "#eaeaea"
    mpl.rcParams["xtick.color"] = "#eaeaea"
    mpl.rcParams["ytick.color"] = "#eaeaea"
    mpl.rcParams["grid.color"] = "#ffffff"
    mpl.rcParams["grid.alpha"] = 0.25


@dataclass(slots=True)
class WorldMinPrice:
    server: str
    world_id: int
    hq: int | None
    nq: int | None
    last_upload_ms: int | None  # Universalis lastUploadTime (ms epoch) 추정


@dataclass(slots=True)
class GlobalMin:
    # 전체 월드 중 (HQ/NQ 각각) 최저가
    hq_price: int | None
    hq_server: str | None
    nq_price: int | None
    nq_server: str | None


class MarketService:
    """
    Universalis 연동 + 캐시/레이트리밋 + (선택) 그래프 생성
    """

    def __init__(
        self,
        http: HttpClient,
        cache: TTLCache,
        limiter: RateLimiter,
        *,
        base_url: str = "https://universalis.app/api/v2",
    ):
        self.http = http
        self.cache = cache
        self.limiter = limiter
        self.base_url = base_url

    async def get_price_data(self, world_id: int, item_id: int) -> Optional[dict[str, Any]]:
        key = f"price:{world_id}:{item_id}"

        async def _factory():
            await self.limiter.wait(key)
            url = f"{self.base_url}/{world_id}/{item_id}"
            return await self.http.get_json(url)

        try:
            return await self.cache.get_or_set(key, _factory, ttl=8.0)
        except Exception:
            return None

    def _extract_min_prices(self, data: dict[str, Any] | None) -> tuple[int | None, int | None, int | None]:
        """
        listings에서 HQ/NQ 최저가 뽑고, lastUploadTime(추정)을 같이 꺼냄.
        """
        if not data:
            return None, None, None

        # Universalis: lastUploadTime(밀리초 epoch) 필드가 흔함
        last_upload = data.get("lastUploadTime")
        try:
            if last_upload is not None:
                last_upload = int(last_upload)
        except Exception:
            last_upload = None

        hq = None
        nq = None
        listings = data.get("listings") or []
        for it in listings:
            price = it.get("pricePerUnit")
            if price is None:
                continue
            try:
                price = int(price)
            except Exception:
                continue

            if bool(it.get("hq")):
                hq = price if hq is None else min(hq, price)
            else:
                nq = price if nq is None else min(nq, price)

        return hq, nq, last_upload

    async def get_kr_world_mins(
        self,
        *,
        item_id: int,
        kr_worlds: dict[str, int],
    ) -> list[WorldMinPrice]:
        """
        월드별 HQ/NQ 최저가 + 마지막 업로드 시간까지 정규화해서 반환.
        """
        out: list[WorldMinPrice] = []
        for server, wid in kr_worlds.items():
            data = await self.get_price_data(wid, item_id)
            hq, nq, last_upload_ms = self._extract_min_prices(data)
            out.append(WorldMinPrice(server=server, world_id=wid, hq=hq, nq=nq, last_upload_ms=last_upload_ms))
        return out

    def compute_global_min(self, rows: list[WorldMinPrice]) -> GlobalMin:
        hq_price = None
        hq_server = None
        nq_price = None
        nq_server = None

        for r in rows:
            if r.hq is not None and (hq_price is None or r.hq < hq_price):
                hq_price = r.hq
                hq_server = r.server
            if r.nq is not None and (nq_price is None or r.nq < nq_price):
                nq_price = r.nq
                nq_server = r.server

        return GlobalMin(
            hq_price=hq_price, hq_server=hq_server,
            nq_price=nq_price, nq_server=nq_server,
        )

    async def _get_history(self, world_id: int, item_id: int) -> dict[str, Any] | None:
        key = f"hist:{world_id}:{item_id}"

        async def _factory():
            await self.limiter.wait(key)
            url = f"{self.base_url}/history/{world_id}/{item_id}"
            return await self.http.get_json(url, params={"entries": 500})

        try:
            return await self.cache.get_or_set(key, _factory, ttl=45.0)
        except Exception:
            return None

    async def build_kr_global_min_chart(
        self,
        *,
        item_id: int,
        kr_worlds: dict[str, int],
        title: str = "한국 서버 전체 최저가 (최근 7일)",
    ) -> Optional[io.BytesIO]:
        """
        ✅ 한섭 전체 최저가의 7일 변화:
        - 5개 월드 history를 전부 조회
        - 날짜별로 HQ/NQ 각각 "최저가(min)"만 뽑아서 그래프
        """
        import datetime as dt
        from collections import defaultdict

        import matplotlib.dates as mdates
        import matplotlib.ticker as mticker

        ensure_korean_font()
        apply_chart_theme()

        now = time.time()
        week_ago = now - 7 * 24 * 3600

        # day -> min
        min_hq: dict[dt.date, int] = defaultdict(lambda: 10**18)
        min_nq: dict[dt.date, int] = defaultdict(lambda: 10**18)
        seen_hq: set[dt.date] = set()
        seen_nq: set[dt.date] = set()

        for _server, wid in kr_worlds.items():
            data = await self._get_history(wid, item_id)
            entries = (data or {}).get("entries") or []
            for e in entries:
                ts = e.get("timestamp")
                price = e.get("pricePerUnit")
                hq = e.get("hq")
                if ts is None or price is None or hq is None:
                    continue

                try:
                    ts = float(ts)
                    if ts > 10_000_000_000:  # ms -> sec
                        ts /= 1000.0
                except Exception:
                    continue

                if ts < week_ago:
                    continue

                try:
                    price = int(price)
                except Exception:
                    continue

                day = dt.datetime.fromtimestamp(ts).date()
                if bool(hq):
                    seen_hq.add(day)
                    if price < min_hq[day]:
                        min_hq[day] = price
                else:
                    seen_nq.add(day)
                    if price < min_nq[day]:
                        min_nq[day] = price

        days = sorted(set(list(seen_hq) + list(seen_nq)))
        if len(days) < 2:
            return None

        xs = [dt.datetime.combine(d, dt.time(0, 0)) for d in days]

        y_hq = [min_hq[d] if d in seen_hq else None for d in days]
        y_nq = [min_nq[d] if d in seen_nq else None for d in days]

        def _filter_none(x, y):
            xx, yy = [], []
            for a, b in zip(x, y):
                if b is None:
                    continue
                xx.append(a)
                yy.append(b)
            return xx, yy

        x_nq, y_nq2 = _filter_none(xs, y_nq)
        x_hq, y_hq2 = _filter_none(xs, y_hq)

        if len(x_nq) < 2 and len(x_hq) < 2:
            return None

        fig, ax = plt.subplots(figsize=(10.5, 4.2), dpi=150)

        if x_nq:
            ax.plot(x_nq, y_nq2, marker="o", linewidth=2, label="NQ")
        if x_hq:
            ax.plot(x_hq, y_hq2, marker="o", linewidth=2, label="HQ")

        ax.set_title(title, fontsize=13, pad=10)
        ax.grid(True, linestyle="--", linewidth=1)
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, pos: f"{int(v):,}"))

        leg = ax.legend(loc="upper right", frameon=True)
        leg.get_frame().set_alpha(0.85)

        fig.tight_layout(pad=1.0)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf
# embeds/ffxiv/market_embed.py
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import discord

from services.ffxiv.market_service import WorldMinPrice, GlobalMin, format_price
from constants.ffxiv.market_emojis import EMOJI_HQ, EMOJI_NQ, EMOJI_LOWEST, TIME_ICON

# Text DB path (user changed)
_TEXT_PATH = Path("data/text/ffxiv/market.json")
_TEXT_CACHE: dict[str, str] | None = None

# Server emojis
SERVER_EMOJI: dict[str, str] = {
    "카벙클": "<:Carbuncle:1479491472406614037>",
    "모그리": "<:Moogle:1479491583589093406>",
    "초코보": "<:Chocobo:1479491773582676070>",
    "톤베리": "<:Tonberry:1479491875303063707>",
    "펜리르": "<:Fenrir:1479492096980418620>",
}


def _load_text() -> dict[str, str]:
    global _TEXT_CACHE
    if _TEXT_CACHE is not None:
        return _TEXT_CACHE

    if _TEXT_PATH.exists():
        try:
            obj = json.loads(_TEXT_PATH.read_text(encoding="utf-8"))
            if isinstance(obj, dict):
                _TEXT_CACHE = {str(k): str(v) for k, v in obj.items()}
                return _TEXT_CACHE
        except Exception:
            pass

    # EN fallback only (no KR hardcoding)
    _TEXT_CACHE = {
        "market.title_kr": "🇰🇷 KR Market Prices",
        "market.field_lowest": "Lowest",
        "market.field_servers": "Servers",
        "market.no_listings": "No listings found.",
        "market.graph_title_suffix": "Graph",
        "market.graph_desc": "KR global lowest price trend (last 7 days).",
        "time.unknown": "Unknown",
        "time.just_now": "Just now",
        "time.minutes_ago": "{m}m ago",
        "time.hours_ago": "{h}h ago",
        "time.days_ago": "{d}d ago",
        "time.date_fmt": "%Y-%m-%d",
        "market.updated_label": "updated",
        "market.updated_line": "╰ {time_icon} {age} ({label})",
        "market.lowest.sep": "━━━━━━━━━━",
        "market.lowest.gil": "길",
        "market.lowest.title": "현재 최저가",
    }
    return _TEXT_CACHE


def t(key: str, default: str) -> str:
    return _load_text().get(key, default)


def _age_text(last_upload_ms: int | None) -> str:
    if not last_upload_ms:
        return t("time.unknown", "Unknown")

    try:
        ts = int(last_upload_ms)
        if ts > 10_000_000_000:  # ms epoch
            dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        else:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:
        return t("time.unknown", "Unknown")

    now = datetime.now(tz=timezone.utc)
    s = int((now - dt).total_seconds())

    if s < 60:
        return t("time.just_now", "Just now")

    m = s // 60
    if m < 60:
        return t("time.minutes_ago", "{m}m ago").format(m=m)

    h = m // 60
    if h < 24:
        return t("time.hours_ago", "{h}h ago").format(h=h)

    d = h // 24
    if d < 30:
        return t("time.days_ago", "{d}d ago").format(d=d)

    return dt.strftime(t("time.date_fmt", "%Y-%m-%d"))


def _server_name_with_emoji(server_name: str) -> str:
    emo = SERVER_EMOJI.get(server_name, "")
    if emo:
        return f"{emo} {server_name}"
    return server_name


def build_market_embed(
    *,
    title: str,
    thumb_url: str | None,
    rows: list[WorldMinPrice],
    gmin: GlobalMin,
    note: str | None = None,
) -> discord.Embed:
    e = discord.Embed(
        title=title,
        description=t("market.title_kr", "🇰🇷 KR Market Prices"),
        color=0xFFD700,
    )

    if thumb_url:
        e.set_thumbnail(url=thumb_url)

    sep = t("market.lowest.sep", "━━━━━━━━━━")
    gil = t("market.lowest.gil", "길")
    lowest_header = f"{EMOJI_LOWEST} {t('market.lowest.title', '현재 최저가')}"

    lines = [sep, lowest_header]

    if gmin.nq_price is not None:
        lines.append(f"{EMOJI_NQ} **{format_price(gmin.nq_price)}{gil}** - **{gmin.nq_server}**")

    if gmin.hq_price is not None:
        lines.append(f"{EMOJI_HQ} **{format_price(gmin.hq_price)}{gil}** - **{gmin.hq_server}**")

    if len(lines) == 2:
        lines.append(t("market.no_listings", "No listings found."))

    lines.append(sep)

    e.add_field(name="\u200b", value="\n".join(lines), inline=False)

    updated_label = t("market.updated_label", "updated")
    updated_line_tpl = t("market.updated_line", "╰ {time_icon} {age} ({label})")

    server_blocks: list[str] = []
    for r in rows:
        name_line = _server_name_with_emoji(r.server)

        hq_text = f"{EMOJI_HQ} {format_price(r.hq)}" if r.hq is not None else f"{EMOJI_HQ} --"
        nq_text = f"{EMOJI_NQ} {format_price(r.nq)}" if r.nq is not None else f"{EMOJI_NQ} --"
        price_line = f"{hq_text} │ {nq_text}"

        age = _age_text(r.last_upload_ms)
        time_line = updated_line_tpl.format(
            time_icon=TIME_ICON,
            age=age,
            label=updated_label,
        )

        block = "\n".join([name_line, price_line, time_line])
        server_blocks.append(block)

    servers_value = "\n\n".join(server_blocks) if server_blocks else t("market.no_listings", "No listings found.")
    e.add_field(
        name=t("market.field_servers", "Servers"),
        value=servers_value,
        inline=False,
    )

    if note:
        e.set_footer(text=note)

    return e


def build_market_graph_embed(*, title: str, subtitle: str | None = None) -> discord.Embed:
    e = discord.Embed(
        title=f"{title} · {t('market.graph_title_suffix', 'Graph')}",
        description=t("market.graph_desc", "KR global lowest price trend (last 7 days)."),
        color=0x6EA8FE,
    )
    if subtitle:
        e.set_footer(text=subtitle)
    return e
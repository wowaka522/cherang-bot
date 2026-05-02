# embeds/ffxiv/weather_embed.py
from __future__ import annotations

import os
import discord


class WeatherEmbedFactory:
    def __init__(self, *, t):
        """
        t: callable (key:str, **kwargs)->str
        """
        self.t = t

    def build_now(
        self,
        *,
        zone_ko: str,
        w_now_ko: str,
        w_next_ko: str,
        w_after_ko: str,
        left_text: str,
        et_hour: int,
        icon_path: str | None,
    ) -> tuple[discord.Embed, list[discord.File]]:
        embed = discord.Embed(
            title=self.t("weather.embed.title", zone_ko=zone_ko),
            description=self.t("weather.embed.desc", left_text=left_text, et_hour=et_hour),
            color=0x55AAFF,
        )

        files: list[discord.File] = []
        if icon_path and os.path.exists(icon_path):
            files.append(discord.File(icon_path, filename="weather.png"))
            embed.set_thumbnail(url="attachment://weather.png")

        embed.add_field(name=self.t("weather.embed.field.now"), value=f"• {w_now_ko}", inline=True)
        embed.add_field(name=self.t("weather.embed.field.next"), value=f"• {w_next_ko}", inline=True)
        embed.add_field(name=self.t("weather.embed.field.next2"), value=f"• {w_after_ko}", inline=True)
        embed.set_footer(text=self.t("weather.embed.footer.hint"))

        return embed, files

    def build_forecast_list(self, *, zone_ko: str, rows: list[dict]) -> discord.Embed:
        """
        rows: [{start_unix,end_unix,weather_ko,et_hour}, ...]
        """
        embed = discord.Embed(
            title=self.t("weather.forecast.embed.title", zone_ko=zone_ko),
            description=self.t("weather.forecast.embed.desc"),
            color=0x55AAFF,
        )

        lines: list[str] = []
        for r in rows[:20]:
            su = int(r["start_unix"])
            w = str(r["weather_ko"])
            et = int(r.get("et_hour", 0))
            lines.append(self.t("weather.forecast.line", start_unix=su, et_hour=et, weather_ko=w))

        embed.add_field(
            name=self.t("weather.forecast.embed.field.list"),
            value="\n".join(lines) if lines else self.t("weather.forecast.embed.empty"),
            inline=False,
        )
        embed.set_footer(text=self.t("weather.ui.footer.back_hint"))
        return embed

    def build_track_prompt(self, *, zone_ko: str) -> discord.Embed:
        embed = discord.Embed(
            title=self.t("weather.track.embed.title", zone_ko=zone_ko),
            description=self.t("weather.track.embed.desc"),
            color=0x55AAFF,
        )
        embed.set_footer(text=self.t("weather.ui.footer.back_hint"))
        return embed

    def build_find_success(
        self,
        *,
        zone_ko: str,
        weather_ko: str,
        unix: int,
        et_hour: int,
    ) -> discord.Embed:
        embed = discord.Embed(
            title=self.t("weather.find.embed.title", zone_ko=zone_ko, weather_ko=weather_ko),
            description=self.t("weather.find.embed.desc", weather_ko=weather_ko, unix=unix, et_hour=et_hour),
            color=0x55AAFF,
        )
        embed.set_footer(text=self.t("weather.embed.footer.hint"))
        return embed
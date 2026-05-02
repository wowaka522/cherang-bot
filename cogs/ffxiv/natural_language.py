# cogs/ffxiv/natural_language.py
from __future__ import annotations

import os
import re
import discord
from discord.ext import commands


class NaturalLanguage(commands.Cog):
    """
    - Natural language triggers, limited to allowed channels
    - Weather find: "{zone} {weather} 언제?"
    - Market: contains one of ["시세", "얼마", "가격"]
    - Weather now: contains one of ["날씨", "기상", "어때"]
    """

    ALLOWED_CHANNEL_IDS = {int(os.getenv("NL_CHANNEL_ID", "0"))}
    ALLOW_DMS = False

    _FIND_WEATHER_RE = re.compile(
        r"^\s*(?P<zone>.+?)\s+(?P<weather>.+?)\s*(?:언제|몇\s*시|언제와|언제\s*옴)\s*\??\s*$"
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _is_allowed_channel(self, channel: discord.abc.GuildChannel | discord.abc.PrivateChannel) -> bool:
        if isinstance(channel, (discord.DMChannel, discord.GroupChannel)):
            return self.ALLOW_DMS

        ch_id = getattr(channel, "id", None)
        if ch_id in self.ALLOWED_CHANNEL_IDS:
            return True

        if isinstance(channel, discord.Thread):
            parent_id = getattr(channel, "parent_id", None)
            if parent_id in self.ALLOWED_CHANNEL_IDS:
                return True

        return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if not self._is_allowed_channel(message.channel):
            return

        content = (message.content or "").strip()
        if not content or content.startswith("/"):
            return

        lowered = content.lower()

        # 1) Weather find (no "날씨" keyword required)
        if self._FIND_WEATHER_RE.match(content):
            weather = self.bot.get_cog("WeatherCog")
            if weather and hasattr(weather, "reply_weather_find_from_message"):
                await weather.reply_weather_find_from_message(message)
                return

        # 2) Market triggers
        if any(w in lowered for w in ["시세", "얼마", "가격"]):
            market = self.bot.get_cog("MarketCog")
            if not market:
                return

            # ✅ New preferred method name (post-refactor)
            if hasattr(market, "reply_market_from_message"):
                await market.reply_market_from_message(message)
                return

            # ✅ Backward compatible (older MarketCog)
            if hasattr(market, "search_and_reply"):
                await market.search_and_reply(message)
                return

            # If neither exists, do nothing (no crash)
            return

        # 3) Weather now triggers
        if any(w in lowered for w in ["날씨", "기상", "어때"]):
            weather = self.bot.get_cog("WeatherCog")
            if weather and hasattr(weather, "reply_weather_from_message"):
                await weather.reply_weather_from_message(message)
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(NaturalLanguage(bot))
    print("✨ NaturalLanguage Loaded! (cogs.ffxiv.natural_language)")
# cogs/ffxiv/market.py
from __future__ import annotations

import re
import discord
from discord import app_commands
from discord.ext import commands

from utils.text_cleaner import extract_item_name
from services.ffxiv.item_index import ItemIndex
from services.ffxiv.market_service import MarketService
from embeds.ffxiv.market_embed import build_market_embed, t
from views.ffxiv.market_view import MarketResultView

try:
    from cogs.quest import quest_progress_add
except Exception:
    def quest_progress_add(*args, **kwargs):
        return


# ✅ No KR hardcoding here: server display names are loaded from Text-DB via t(...)
# World IDs are just numbers (safe).
_KR_WORLD_IDS = {
    "kr.world.moogle": 2077,
    "kr.world.chocobo": 2076,
    "kr.world.carbuncle": 2075,
    "kr.world.tonberry": 2078,
    "kr.world.fenrir": 2080,
}

# Natural language trigger words (non-user-facing; kept minimal)
_NL_KEYWORDS = ("시세", "가격", "얼마")


def _build_kr_worlds() -> dict[str, int]:
    """
    Returns {display_name: world_id}.
    display_name comes from Text-DB (data/text/ffxiv/market.json).
    """
    out: dict[str, int] = {}
    for key, wid in _KR_WORLD_IDS.items():
        # Default is EN to avoid KR hardcoding in code
        fallback = {
            "kr.world.moogle": "Moogle",
            "kr.world.chocobo": "Chocobo",
            "kr.world.carbuncle": "Carbuncle",
            "kr.world.tonberry": "Tonberry",
            "kr.world.fenrir": "Fenrir",
        }.get(key, key)
        out[t(key, fallback)] = wid
    return out


def _guess_item_query_from_message(content: str) -> str:
    """
    Heuristic:
    - Remove NL keywords ("시세/가격/얼마") and surrounding noise
    - Then reuse extract_item_name for additional cleanup
    """
    s = (content or "").strip()

    # remove keywords anywhere
    for kw in _NL_KEYWORDS:
        s = s.replace(kw, " ")

    # remove common trailing punctuation / extra spaces
    s = re.sub(r"[!?.,]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    # best-effort cleanup
    s = extract_item_name(s).strip()
    return s


class MarketCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Load item index if missing
        if not hasattr(bot, "item_index"):
            bot.item_index = ItemIndex("data/ffxiv/market/compiled/items.json")
            bot.item_index.load()

        # Cache KR worlds mapping (Text-DB driven names)
        self.kr_worlds = _build_kr_worlds()

        if not hasattr(bot, "market_svc") or bot.market_svc is None:
            print("[WARN] bot.market_svc is None. Check bot.py Step2 injection.")

    @app_commands.command(name="시세", description="한국 서버 FF14 아이템 시세 조회")  # 슬래시 설명은 예외 OK
    async def price_cmd(self, interaction: discord.Interaction, 아이템이름: str):
        await interaction.response.defer(thinking=True)
        await self._send_market_result(
            send_ctx=interaction,
            raw_query=아이템이름,
            use_reply=False,
        )

    # ✅ Natural language entry point (called by NaturalLanguage Cog)
    async def reply_market_from_message(self, message: discord.Message):
        """
        Natural-language handler. Replies in-channel with the same embed/view as /시세.
        """
        if message.author.bot:
            return

        query = _guess_item_query_from_message(message.content or "")
        if not query:
            return

        await self._send_market_result(
            send_ctx=message,
            raw_query=query,
            use_reply=True,
        )

    async def _send_market_result(self, *, send_ctx, raw_query: str, use_reply: bool):
        """
        Shared core path for /시세 and natural language.
        send_ctx: discord.Interaction | discord.Message
        """
        svc: MarketService | None = getattr(self.bot, "market_svc", None)
        if svc is None:
            # user-facing text via Text-DB
            msg = t("market.err.service_missing", "Market service is not configured.")
            if isinstance(send_ctx, discord.Interaction):
                return await send_ctx.followup.send(msg, ephemeral=True)
            return await send_ctx.reply(msg)

        item_name = extract_item_name(raw_query)
        item_id, real_name, similar = self.bot.item_index.search(item_name)
        if not item_id:
            msg = t("market.err.search_fail", "No similar items found for: {q}").format(q=item_name)
            if isinstance(send_ctx, discord.Interaction):
                return await send_ctx.followup.send(msg, ephemeral=True)
            return await send_ctx.reply(msg)

        entry = self.bot.item_index.get(item_id)

        thumb_url = None
        if entry and getattr(entry, "icon", None):
            thumb_url = (
                "https://xivapi.com/"
                + entry.icon.replace("ui/icon/", "i/").replace(".tex", ".png")
            )

        rows = await svc.get_kr_world_mins(item_id=item_id, kr_worlds=self.kr_worlds)
        gmin = svc.compute_global_min(rows)

        embed = build_market_embed(
            title=real_name,
            thumb_url=thumb_url,
            rows=rows,
            gmin=gmin,
            note=None,
        )

        view = MarketResultView(
            svc=svc,
            kr_worlds=self.kr_worlds,
            item_id=item_id,
            item_name=real_name,
            thumb_url=thumb_url,
            rows=rows,
            gmin=gmin,
            similar_names=similar,
            item_index=self.bot.item_index,
        )

        # Quest hook (not user-facing text)
        try:
            quest_progress_add(
                (send_ctx.user.id if isinstance(send_ctx, discord.Interaction) else send_ctx.author.id),
                "market_lookup",
                1,
                payload={"item_name": real_name},
            )
        except Exception:
            pass

        if isinstance(send_ctx, discord.Interaction):
            await send_ctx.followup.send(embed=embed, view=view)
        else:
            # Natural language: reply to the message (new message is expected here)
            if use_reply:
                await send_ctx.reply(embed=embed, view=view)
            else:
                await send_ctx.channel.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(MarketCog(bot))
    print("✨ MarketCog Loaded! (cogs.ffxiv.market)")
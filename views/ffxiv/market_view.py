# views/ffxiv/market_view.py
from __future__ import annotations

import discord

from services.ffxiv.market_service import MarketService, WorldMinPrice, GlobalMin
from embeds.ffxiv.market_embed import (
    build_market_embed,
    build_market_graph_embed,
    t,
)


def _copy_embed_with_footer(src: discord.Embed | None, footer_text: str) -> discord.Embed:
    if src is None:
        e = discord.Embed(description=footer_text)
        return e
    e = src.copy()
    e.set_footer(text=footer_text)
    return e


class AlertModal(discord.ui.Modal):
    def __init__(self, *, item_id: int, item_name: str):
        super().__init__(title=t("market.alert.modal.title", "Price Alert"))

        self.item_id = item_id
        self.item_name = item_name

        self.target_price = discord.ui.TextInput(
            label=t("market.alert.input.target.label", "Target price (notify when <=)"),
            placeholder=t("market.alert.input.target.placeholder", "e.g. 500000"),
            required=True,
            max_length=12,
        )
        self.add_item(self.target_price)

    async def on_submit(self, interaction: discord.Interaction):
        raw = str(self.target_price.value).replace(",", "").strip()
        try:
            price = int(raw)
            if price <= 0:
                raise ValueError()
        except Exception:
            return await interaction.response.send_message(
                t("market.alert.err.invalid_number", "Please enter a valid number."),
                ephemeral=True,
            )

        # TODO: Repo 연결
        await interaction.response.send_message(
            t("market.alert.ok.temp", "Alert created (temporary): {item} <= {price}")
            .format(item=self.item_name, price=f"{price:,}"),
            ephemeral=True,
        )


class MarketResultView(discord.ui.View):
    """
    Base market result view
    - row0: graph / alert
    - row1: similar buttons or select

    IMPORTANT:
    - Avoid defer(thinking=True) for Select; some libs create extra visible messages.
    - Instead: edit the same message immediately to show "loading".
    """

    def __init__(
        self,
        *,
        svc: MarketService,
        kr_worlds: dict[str, int],
        item_id: int,
        item_name: str,
        thumb_url: str | None,
        rows: list[WorldMinPrice],
        gmin: GlobalMin,
        similar_names: list[str],
        item_index,
        timeout: float = 180.0,
    ):
        super().__init__(timeout=timeout)
        self.svc = svc
        self.kr_worlds = kr_worlds
        self.item_id = item_id
        self.item_name = item_name
        self.item_index = item_index
        self.similar_names = similar_names or []

        self._base_payload = dict(
            title=item_name,
            thumb_url=thumb_url,
            rows=rows,
            gmin=gmin,
        )

        self.add_item(GraphButton(row=0))
        self.add_item(AlertButton(row=0))
        self._build_similar_row()

    def _build_similar_row(self):
        sims = self.similar_names[:25]
        if not sims:
            return
        if 1 <= len(sims) <= 3:
            for name in sims:
                self.add_item(SimilarButton(label=name, row=1))
        else:
            self.add_item(SimilarSelect(options=sims, row=1))

    def build_base_embed(self) -> discord.Embed:
        return build_market_embed(**self._base_payload)

    def _disable_all_children(self):
        # ✅ Compatible across discord.py forks/versions
        for child in self.children:
            try:
                child.disabled = True
            except Exception:
                pass

    async def _show_loading(self, interaction: discord.Interaction, *, footer_key: str, footer_fallback: str):
        """
        Show in-place loading:
        - disable all items
        - edit same message immediately (no extra messages)
        """
        self._disable_all_children()

        current = interaction.message.embeds[0] if interaction.message.embeds else None
        loading_embed = _copy_embed_with_footer(current, t(footer_key, footer_fallback))

        await interaction.response.edit_message(embed=loading_embed, view=self)

    async def rebuild_for_query(self, interaction: discord.Interaction, query: str):
        await self._show_loading(
            interaction,
            footer_key="market.loading.search",
            footer_fallback="Searching…",
        )

        item_id, real_name, similar = self.item_index.search(query)
        if not item_id:
            return await interaction.followup.send(
                t("market.err.item_not_found", "Item not found: {q}").format(q=query),
                ephemeral=True,
            )

        entry = self.item_index.get(item_id)
        thumb_url = None
        if entry and getattr(entry, "icon", None):
            thumb_url = (
                "https://xivapi.com/"
                + entry.icon.replace("ui/icon/", "i/").replace(".tex", ".png")
            )

        rows = await self.svc.get_kr_world_mins(item_id=item_id, kr_worlds=self.kr_worlds)
        gmin = self.svc.compute_global_min(rows)

        new_view = MarketResultView(
            svc=self.svc,
            kr_worlds=self.kr_worlds,
            item_id=item_id,
            item_name=real_name,
            thumb_url=thumb_url,
            rows=rows,
            gmin=gmin,
            similar_names=similar,
            item_index=self.item_index,
        )

        await interaction.edit_original_response(
            embed=new_view.build_base_embed(),
            attachments=[],
            view=new_view,
        )


class MarketGraphView(discord.ui.View):
    def __init__(self, *, base_view: MarketResultView, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.base_view = base_view
        self.add_item(BackButton(row=0))
        self.add_item(AlertButton(row=0))


class GraphButton(discord.ui.Button):
    def __init__(self, *, row: int = 0):
        super().__init__(label="📊 그래프 보기", style=discord.ButtonStyle.primary, row=row)

    async def callback(self, interaction: discord.Interaction):
        view: MarketResultView = self.view  # type: ignore

        await view._show_loading(
            interaction,
            footer_key="market.loading.graph",
            footer_fallback="Building graph…",
        )

        buf = await view.svc.build_kr_global_min_chart(item_id=view.item_id, kr_worlds=view.kr_worlds)
        if not buf:
            return await interaction.followup.send(
                t("market.graph_fail", "Not enough data to build a graph."),
                ephemeral=True,
            )

        file = discord.File(buf, filename="chart.png")
        e = build_market_graph_embed(title=view.item_name)
        e.set_image(url="attachment://chart.png")

        await interaction.edit_original_response(
            embed=e,
            attachments=[file],
            view=MarketGraphView(base_view=view),
        )


class BackButton(discord.ui.Button):
    def __init__(self, *, row: int = 0):
        super().__init__(label="↩ 시세로 돌아가기", style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, interaction: discord.Interaction):
        v: MarketGraphView = self.view  # type: ignore
        await interaction.response.edit_message(
            embed=v.base_view.build_base_embed(),
            attachments=[],
            view=v.base_view,
        )


class AlertButton(discord.ui.Button):
    def __init__(self, *, row: int = 0):
        super().__init__(label="🔔 알림 설정", style=discord.ButtonStyle.success, row=row)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        base = view.base_view if isinstance(view, MarketGraphView) else view  # type: ignore
        await interaction.response.send_modal(AlertModal(item_id=base.item_id, item_name=base.item_name))


class SimilarButton(discord.ui.Button):
    def __init__(self, *, label: str, row: int = 1):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, interaction: discord.Interaction):
        base: MarketResultView = self.view  # type: ignore
        await base.rebuild_for_query(interaction, self.label)


class SimilarSelect(discord.ui.Select):
    def __init__(self, *, options: list[str], row: int = 1):
        opts = [discord.SelectOption(label=o[:100]) for o in options[:25]]
        super().__init__(
            placeholder=t("market.similar.placeholder", "Choose a similar item"),
            options=opts,
            row=row,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        base: MarketResultView = self.view  # type: ignore
        await base.rebuild_for_query(interaction, self.values[0])
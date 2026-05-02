# views/ffxiv/weather_view.py
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

import discord

OnSelectFn = Callable[[discord.Interaction, str], Awaitable[None]]


@dataclass
class TugRow:
    fish_id: int
    name: str
    ok_now: bool
    next_ts: Optional[int]  # epoch seconds


def _safe_int(v) -> Optional[int]:
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None


class WeatherHomeView(discord.ui.View):
    def __init__(self, *, bot, zone_key: str, service, embed_factory, tug_db=None):
        super().__init__(timeout=180)
        self.bot = bot
        self.zone_key = zone_key
        self.service = service
        self.embed_factory = embed_factory
        self.tug_db = tug_db

        # 버튼 라벨도 TextDB로 (decorator 대신 런타임 생성)
        self.add_item(_HomeButton(self, kind="forecast"))
        self.add_item(_HomeButton(self, kind="tug"))
        self.add_item(_HomeButton(self, kind="track"))

    def t(self, key: str, **kwargs) -> str:
        return self.service.t(key, **kwargs)

    async def _back_to_home(self, interaction: discord.Interaction):
        payload = self.service.build_now_payload(zone_key=self.zone_key, user_id=interaction.user.id)
        if not payload.get("ok"):
            await interaction.response.edit_message(
                content=self.t("weather.ui.err.load_now"),
                embed=None,
                view=None,
                attachments=[],
            )
            return

        embed, files = self.embed_factory.build_now(
            zone_ko=payload["zone_ko"],
            w_now_ko=payload["w_now_ko"],
            w_next_ko=payload["w_next_ko"],
            w_after_ko=payload["w_after_ko"],
            left_text=payload["left_text"],
            et_hour=payload["et_hour"],
            icon_path=payload.get("icon_path"),
        )
        await interaction.response.edit_message(embed=embed, attachments=files, view=self)

    # -------- tug helpers --------
    def _calc_tug_status(self, *, fish, spot) -> tuple[bool, Optional[int]]:
        weather_service = getattr(self.bot, "weather_service", None)
        ok_now = False
        next_ts: Optional[int] = None

        zkey = getattr(self, "zone_key", None)

        if weather_service and hasattr(weather_service, "is_now_available_for_conditions"):
            try:
                ok_now = bool(
                    weather_service.is_now_available_for_conditions(
                        zone_key=zkey,
                        prev_set=list(getattr(fish, "previous_weather", []) or []),
                        cur_set=list(getattr(fish, "weather", []) or []),
                        start_et=getattr(fish, "start", None),
                        end_et=getattr(fish, "end", None),
                    )
                )
            except Exception:
                ok_now = False

        if weather_service and hasattr(weather_service, "get_next_window_ts_for_conditions"):
            try:
                next_ts = _safe_int(
                    weather_service.get_next_window_ts_for_conditions(
                        zone_key=zkey,
                        prev_set=list(getattr(fish, "previous_weather", []) or []),
                        cur_set=list(getattr(fish, "weather", []) or []),
                        start_et=getattr(fish, "start", None),
                        end_et=getattr(fish, "end", None),
                        horizon_hours=24 * 30,
                        include_now=False if ok_now else True,
                    )
                )
            except Exception:
                next_ts = None

        return ok_now, next_ts

    def _build_tug_rows(self, *, zone_ko: str) -> list[TugRow]:
        if not self.tug_db:
            return []

        try:
            ids = list(self.tug_db.list_teoju_ids_by_territory(zone_ko, limit=200) or [])
        except Exception:
            ids = []

        out: list[TugRow] = []
        for fish_id in ids:
            disp = self.tug_db.build_display(fish_id)
            if not disp:
                continue
            fish = disp.get("fish")
            spot = disp.get("spot")
            if not fish or not spot:
                continue

            name = getattr(fish, "name_ko", None) or self.t("weather.tug.fallback_name", fish_id=fish_id)
            ok_now, next_ts = self._calc_tug_status(fish=fish, spot=spot)
            out.append(TugRow(fish_id=int(fish_id), name=str(name), ok_now=ok_now, next_ts=next_ts))

        # 정렬: 지금 가능(🟢) 먼저 → next_ts 가까운 순 → name
        now_ts = int(time.time())

        def key(r: TugRow):
            ok_rank = 0 if r.ok_now else 1
            if r.next_ts is None:
                ts_rank = 10**18
            else:
                ts_rank = max(0, int(r.next_ts) - now_ts)
            return (ok_rank, ts_rank, r.name)

        out.sort(key=key)
        return out


class _HomeButton(discord.ui.Button):
    def __init__(self, parent: WeatherHomeView, *, kind: str):
        self.parent = parent
        self.kind = kind

        if kind == "forecast":
            label = parent.t("weather.ui.btn.forecast")
        elif kind == "tug":
            label = parent.t("weather.ui.btn.tug")
        else:
            label = parent.t("weather.ui.btn.track")

        super().__init__(label=label, style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        if self.kind == "forecast":
            payload = self.parent.service.build_forecast_list_payload(zone_key=self.parent.zone_key, windows=12)
            if not payload.get("ok"):
                await interaction.response.send_message(self.parent.t("weather.ui.err.load_forecast"), ephemeral=True)
                return
            embed = self.parent.embed_factory.build_forecast_list(zone_ko=payload["zone_ko"], rows=payload["rows"])
            await interaction.response.edit_message(embed=embed, view=WeatherSubView(parent=self.parent), attachments=[])
            return

        if self.kind == "track":
            now_payload = self.parent.service.build_now_payload(zone_key=self.parent.zone_key, user_id=None)
            zone_ko = now_payload.get("zone_ko") or self.parent.zone_key

            embed = self.parent.embed_factory.build_track_prompt(zone_ko=zone_ko)
            possible = sorted(list(self.parent.service.zone_possible_weathers_ko(self.parent.zone_key)))

            view = WeatherTrackSelectView(parent=self.parent, zone_key=self.parent.zone_key, possible_weathers=possible)
            await interaction.response.edit_message(embed=embed, view=view, attachments=[])
            return

        # kind == "tug"
        now_payload = self.parent.service.build_now_payload(zone_key=self.parent.zone_key, user_id=None)
        zone_ko = now_payload.get("zone_ko") or self.parent.zone_key

        rows = self.parent._build_tug_rows(zone_ko=zone_ko)
        view = TugListView(parent=self.parent, zone_key=self.parent.zone_key, zone_ko=zone_ko, rows=rows, page=0, page_size=10)
        await interaction.response.edit_message(embed=view.build_embed(), view=view, attachments=[])


class WeatherSubView(discord.ui.View):
    """예보/간단 화면: 뒤로가기만 제공"""

    def __init__(self, *, parent: WeatherHomeView):
        super().__init__(timeout=180)
        self.parent = parent
        self.add_item(_BackButton(parent))

class _BackButton(discord.ui.Button):
    def __init__(self, parent: WeatherHomeView):
        self.parent = parent
        super().__init__(label=parent.t("weather.ui.btn.back"), style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await self.parent._back_to_home(interaction)


# -------------------------
# Track (weather find) view
# -------------------------
class WeatherTrackSelect(discord.ui.Select):
    def __init__(self, *, parent: WeatherHomeView, zone_key: str, possible_weathers: list[str]):
        self.parent = parent
        self.zone_key = zone_key

        options = [discord.SelectOption(label=w) for w in possible_weathers[:25]]
        super().__init__(
            placeholder=self.parent.t("weather.track.ui.select.placeholder"),
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        target_ko = self.values[0]
        payload = self.parent.service.build_find_payload(zone_key=self.zone_key, target_ko=target_ko)

        if not payload.get("ok"):
            msg = payload.get("content") or self.parent.t("weather.track.ui.err.fail_default")
            await interaction.response.edit_message(
                content=msg,
                embed=None,
                view=WeatherSubView(parent=self.parent),
                attachments=[],
            )
            return

        embed = self.parent.embed_factory.build_find_success(
            zone_ko=payload["zone_ko"],
            weather_ko=payload["weather_ko"],
            unix=int(payload["unix"]),
            et_hour=int(payload["et_hour"]),
        )
        await interaction.response.edit_message(embed=embed, view=WeatherSubView(parent=self.parent), attachments=[])


class WeatherTrackSelectView(discord.ui.View):
    def __init__(self, *, parent: WeatherHomeView, zone_key: str, possible_weathers: list[str]):
        super().__init__(timeout=180)
        self.parent = parent
        self.add_item(WeatherTrackSelect(parent=parent, zone_key=zone_key, possible_weathers=possible_weathers))
        self.add_item(_BackButton(parent))


# -------------------------
# Tug list/detail views
# -------------------------
class TugPickSelect(discord.ui.Select):
    def __init__(self, *, parent: WeatherHomeView, list_view: "TugListView", page_rows: list[TugRow]):
        self.parent = parent
        self.list_view = list_view

        options: list[discord.SelectOption] = []
        for r in page_rows[:25]:
            options.append(discord.SelectOption(label=r.name[:100], value=str(r.fish_id)))

        super().__init__(
            placeholder=self.parent.t("weather.tug.ui.select.placeholder"),
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        fish_id = _safe_int(self.values[0])
        if fish_id is None:
            await interaction.response.send_message(self.parent.t("weather.tug.ui.err.bad_pick"), ephemeral=True)
            return

        idx = self.list_view.find_index(fish_id)
        if idx < 0:
            await interaction.response.send_message(self.parent.t("weather.tug.ui.err.bad_pick"), ephemeral=True)
            return

        detail = TugDetailView(
            parent=self.parent,
            zone_key=self.list_view.zone_key,
            zone_ko=self.list_view.zone_ko,
            rows=self.list_view.rows,
            index=idx,
            return_page=self.list_view.page,
            page_size=self.list_view.page_size,
        )
        await interaction.response.edit_message(embed=detail.build_embed(), view=detail, attachments=[])


class TugListView(discord.ui.View):
    def __init__(
        self,
        *,
        parent: WeatherHomeView,
        zone_key: str,
        zone_ko: str,
        rows: list[TugRow],
        page: int,
        page_size: int = 10,
    ):
        super().__init__(timeout=180)
        self.parent = parent
        self.zone_key = zone_key
        self.zone_ko = zone_ko
        self.rows = rows
        self.page = max(0, int(page))
        self.page_size = max(1, int(page_size))

        page_rows = self._page_rows()
        if page_rows:
            self.add_item(TugPickSelect(parent=self.parent, list_view=self, page_rows=page_rows))

        # 페이지 버튼 (TextDB 라벨)
        self.add_item(_PageButton(self, dir_="prev"))
        self.add_item(_PageButton(self, dir_="next"))
        self.add_item(_BackButton(parent))

    def t(self, key: str, **kwargs) -> str:
        return self.parent.t(key, **kwargs)

    def total_pages(self) -> int:
        if not self.rows:
            return 1
        return max(1, (len(self.rows) + self.page_size - 1) // self.page_size)

    def _page_rows(self) -> list[TugRow]:
        start = self.page * self.page_size
        end = start + self.page_size
        return self.rows[start:end]

    def find_index(self, fish_id: int) -> int:
        for i, r in enumerate(self.rows):
            if int(r.fish_id) == int(fish_id):
                return i
        return -1

    def _format_row_line(self, r: TugRow) -> str:
        if r.ok_now:
            return self.t("weather.tug.line.available", name=r.name)
        if r.next_ts:
            return self.t("weather.tug.line.next", name=r.name, next_ts=int(r.next_ts))
        return self.t("weather.tug.line.unknown", name=r.name)

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.t("weather.tug.embed.title", zone_ko=self.zone_ko),
            description=self.t("weather.tug.embed.desc", max_show=self.page_size),
            color=0x55AAFF,
        )

        if not self.rows:
            embed.add_field(
                name=self.t("weather.tug.embed.field.result"),
                value=self.t("weather.tug.msg.none"),
                inline=False,
            )
            embed.set_footer(text=self.t("weather.tug.embed.footer.back"))
            return embed

        lines = [self._format_row_line(r) for r in self._page_rows()]
        embed.add_field(
            name=self.t("weather.tug.embed.field.list"),
            value="\n".join(lines) if lines else self.t("weather.tug.msg.none"),
            inline=False,
        )

        p = self.total_pages()
        embed.set_footer(text=self.t("weather.tug.embed.footer.page", page=self.page + 1, pages=p))
        return embed

    def _rebuild(self, *, page: int) -> "TugListView":
        return TugListView(
            parent=self.parent,
            zone_key=self.zone_key,
            zone_ko=self.zone_ko,
            rows=self.rows,
            page=page,
            page_size=self.page_size,
        )


class _PageButton(discord.ui.Button):
    def __init__(self, list_view: TugListView, *, dir_: str):
        self.list_view = list_view
        self.dir_ = dir_

        label = list_view.t("weather.ui.btn.prev") if dir_ == "prev" else list_view.t("weather.ui.btn.next")
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction):
        if self.dir_ == "prev":
            if self.list_view.page <= 0:
                await interaction.response.defer()
                return
            new_view = self.list_view._rebuild(page=self.list_view.page - 1)
        else:
            if self.list_view.page >= self.list_view.total_pages() - 1:
                await interaction.response.defer()
                return
            new_view = self.list_view._rebuild(page=self.list_view.page + 1)

        await interaction.response.edit_message(embed=new_view.build_embed(), view=new_view, attachments=[])


class TugDetailView(discord.ui.View):
    def __init__(
        self,
        *,
        parent: WeatherHomeView,
        zone_key: str,
        zone_ko: str,
        rows: list[TugRow],
        index: int,
        return_page: int,
        page_size: int,
    ):
        super().__init__(timeout=180)
        self.parent = parent
        self.zone_key = zone_key
        self.zone_ko = zone_ko
        self.rows = rows
        self.index = max(0, min(int(index), max(0, len(rows) - 1)))
        self.return_page = max(0, int(return_page))
        self.page_size = max(1, int(page_size))

        # 디테일 네비 버튼도 TextDB 라벨
        self.add_item(_DetailNavButton(self, kind="prev"))
        self.add_item(_DetailNavButton(self, kind="next"))
        self.add_item(_TugAlertButton(self))
        self.add_item(_DetailNavButton(self, kind="list"))
        self.add_item(_DetailNavButton(self, kind="home"))

    def t(self, key: str, **kwargs) -> str:
        return self.parent.t(key, **kwargs)

    def _row(self) -> TugRow:
        return self.rows[self.index]

    def _build_embed_from_disp(self, *, row: TugRow, disp: dict, next_ts: Optional[int]) -> discord.Embed:
        ok_now = bool(row.ok_now)
        embed_color = 0x2ECC71 if ok_now else 0xE74C3C

        embed = discord.Embed(
            title=self.t("weather.tug.detail.embed.title", fish_name=row.name),
            description=self.t(
                "weather.tug.detail.embed.desc",
                status=self.t("weather.tug.detail.status.ok") if ok_now else self.t("weather.tug.detail.status.no"),
            ),
            color=embed_color,
        )

        thumb_url = disp.get("thumb_url") or "https://xivapi.com/i/060000/060445.png"
        embed.set_thumbnail(url=thumb_url)

        embed.add_field(
            name=self.t("weather.tug.detail.field.location"),
            value=f"`{disp.get('location_line', '-')}`",
            inline=True,
        )
        embed.add_field(
            name=self.t("weather.tug.detail.field.time"),
            value=f"`{disp.get('time_line', '-')}`",
            inline=True,
        )
        embed.add_field(
            name=self.t("weather.tug.detail.field.condition"),
            value=f"`{disp.get('condition_line', '-')}`",
            inline=False,
        )

        if next_ts:
            ts_val = int(next_ts)
            embed.add_field(
                name=self.t("weather.tug.detail.field.next_window"),
                value=self.t("weather.tug.detail.value.next_window", ts=ts_val),
                inline=False,
            )

        if disp.get("intuition_line"):
            embed.add_field(
                name=self.t("weather.tug.detail.field.intuition"),
                value=f"```fix\n{disp['intuition_line']}\n```",
                inline=False,
            )

        # ✅ 방법
        embed.add_field(
            name=self.t("weather.tug.detail.field.method"),
            value=self.t("weather.tug.detail.value.method", method=disp.get("method_line", "-")),
            inline=False,
        )


        embed.set_footer(text=self.t("weather.tug.detail.footer.index", index=self.index + 1, total=len(self.rows)))
        return embed

    def build_embed(self) -> discord.Embed:
        row = self._row()

        if not self.parent.tug_db:
            return discord.Embed(
                title=self.t("weather.tug.detail.embed.title", fish_name=row.name),
                description=self.t("weather.tug.ui.err.no_db"),
                color=0xE74C3C,
            )

        disp = self.parent.tug_db.build_display(row.fish_id)
        if not disp:
            return discord.Embed(
                title=self.t("weather.tug.detail.embed.title", fish_name=row.name),
                description=self.t("weather.tug.ui.err.bad_data"),
                color=0xE74C3C,
            )

        next_ts = row.next_ts
        return self._build_embed_from_disp(row=row, disp=disp, next_ts=next_ts)

    def _rebuild(self, *, index: int) -> "TugDetailView":
        return TugDetailView(
            parent=self.parent,
            zone_key=self.zone_key,
            zone_ko=self.zone_ko,
            rows=self.rows,
            index=index,
            return_page=self.return_page,
            page_size=self.page_size,
        )


class _DetailNavButton(discord.ui.Button):
    def __init__(self, detail_view: TugDetailView, *, kind: str):
        self.detail_view = detail_view
        self.kind = kind

        if kind == "prev":
            label = detail_view.t("weather.ui.btn.prev")
            style = discord.ButtonStyle.secondary
            row = 1
        elif kind == "next":
            label = detail_view.t("weather.ui.btn.next")
            style = discord.ButtonStyle.secondary
            row = 1
        elif kind == "list":
            label = detail_view.t("weather.ui.btn.list")
            style = discord.ButtonStyle.secondary
            row = 2
        else:
            label = detail_view.t("weather.ui.btn.home")
            style = discord.ButtonStyle.primary
            row = 2

        super().__init__(label=label, style=style, row=row)

    async def callback(self, interaction: discord.Interaction):
        dv = self.detail_view

        if self.kind == "prev":
            if dv.index <= 0:
                await interaction.response.defer()
                return
            nv = dv._rebuild(index=dv.index - 1)
            await interaction.response.edit_message(embed=nv.build_embed(), view=nv, attachments=[])
            return

        if self.kind == "next":
            if dv.index >= len(dv.rows) - 1:
                await interaction.response.defer()
                return
            nv = dv._rebuild(index=dv.index + 1)
            await interaction.response.edit_message(embed=nv.build_embed(), view=nv, attachments=[])
            return

        if self.kind == "list":
            lv = TugListView(
                parent=dv.parent,
                zone_key=dv.zone_key,
                zone_ko=dv.zone_ko,
                rows=dv.rows,
                page=dv.return_page,
                page_size=dv.page_size,
            )
            await interaction.response.edit_message(embed=lv.build_embed(), view=lv, attachments=[])
            return

        # home
        await dv.parent._back_to_home(interaction)

class _TugAlertButton(discord.ui.Button):
    def __init__(self, detail_view: TugDetailView):
        self.detail_view = detail_view
        label = detail_view.t("weather.ui.btn.alert")  # TextDB
        super().__init__(label=label, style=discord.ButtonStyle.success, row=1)

    async def callback(self, interaction: discord.Interaction):
        dv = self.detail_view
        parent = dv.parent

        repo = getattr(parent.bot, "fish_alert_repo", None)
        if repo is None:
            await interaction.response.send_message(parent.t("fish.alert.err.no_repo"), ephemeral=True)
            return

        if not parent.tug_db:
            await interaction.response.send_message(parent.t("weather.tug.ui.err.no_db"), ephemeral=True)
            return

        row = dv._row()
        disp = parent.tug_db.build_display(row.fish_id)
        if not disp:
            await interaction.response.send_message(parent.t("weather.tug.ui.err.bad_data"), ephemeral=True)
            return

        spot_key = disp.get("spot_key")
        if not spot_key:
            await interaction.response.send_message(parent.t("fish.alert.err.no_spot"), ephemeral=True)
            return

        next_ts = row.next_ts
        now = int(time.time())

        # weather_service가 include_now 옵션을 지원하면 그걸로 다시 계산
        weather_service = getattr(parent.bot, "weather_service", None)
        fish = disp.get("fish")

        if weather_service and fish and hasattr(weather_service, "get_next_window_ts_for_conditions"):
            try:
                # ok_now면 include_now=False로 재계산 시도 (즉시 울림 방지)
                if row.ok_now:
                    next_ts2 = weather_service.get_next_window_ts_for_conditions(
                        zone_key=dv.zone_key,
                        prev_set=list(getattr(fish, "previous_weather", []) or []),
                        cur_set=list(getattr(fish, "weather", []) or []),
                        start_et=getattr(fish, "start", None),
                        end_et=getattr(fish, "end", None),
                        horizon_hours=24 * 30,
                        include_now=False,
                    )
                    if next_ts2:
                        next_ts = int(next_ts2)
            except TypeError:
                # include_now 파라미터 아직 없으면 무시(그래도 기존 next_ts로 등록)
                pass
            except Exception:
                pass

        if not next_ts or int(next_ts) <= now + 5:
            await interaction.response.send_message(parent.t("fish.alert.err.no_future_window"), ephemeral=True)
            return

        from repositories.fish_alert_repo import FishAlert

        repo.upsert(
            FishAlert(
                user_id=interaction.user.id,
                fish_id=int(row.fish_id),
                spot_key=str(spot_key),
                next_window_ts=int(next_ts),
                channel_id=int(interaction.channel.id),
            )
        )

        await interaction.response.send_message(
            parent.t("fish.alert.ok", ts=int(next_ts)),
            ephemeral=True,
        )

# -------------------------
# Zone select views
# -------------------------
class ZoneSelect(discord.ui.Select):
    def __init__(
        self,
        *,
        placeholder: str,
        options: list[discord.SelectOption],
        on_select: OnSelectFn,
    ):
        super().__init__(placeholder=placeholder, options=options[:25], min_values=1, max_values=1)
        self._on_select = on_select

    async def callback(self, inter: discord.Interaction):
        zone_key = self.values[0]
        await self._on_select(inter, zone_key)


class ZoneSelectView(discord.ui.View):
    def __init__(
        self,
        *,
        title: str,
        desc: str,
        placeholder: str,
        zone_options: list[tuple[str, str]],  # [(label, value), ...]
        on_select: OnSelectFn,
        timeout: float = 60.0,
    ):
        super().__init__(timeout=timeout)
        self.title = title
        self.desc = desc

        opts: list[discord.SelectOption] = []
        for label, value in zone_options[:25]:
            opts.append(discord.SelectOption(label=label[:100], value=value))

        self.add_item(ZoneSelect(placeholder=placeholder, options=opts, on_select=on_select))

    def build_prompt_embed(self, *, color: int = 0x55AAFF) -> discord.Embed:
        return discord.Embed(title=self.title, description=self.desc, color=color)
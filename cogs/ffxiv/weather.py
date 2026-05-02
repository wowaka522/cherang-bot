# cogs/ffxiv/weather.py
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.fish_alert_dispatcher import FishAlertDispatcher
from utils.text_cleaner import extract_city_name

from services.ffxiv.weather_service import WeatherService
from embeds.ffxiv.weather_embed import WeatherEmbedFactory
from views.ffxiv.weather_view import ZoneSelectView, WeatherHomeView
from services.ffxiv.weather_logic import to_korean_zone
from services.ffxiv.tug_db import TugDB
from repositories.fish_alert_repo import FishAlertRepo
from services.fish_alert_dispatcher import FishAlertDispatcher


class WeatherCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.service = WeatherService(bot)
        self.embed_factory = WeatherEmbedFactory(t=self.service.t)
        db_path = getattr(bot, "tug_db_path", r"data/ffxiv/fish/compiled/final_fishing_db.json")
        self.tug_db = TugDB(db_path)

        # tug 쪽에서 접근하는 weather_service는 "Cog"가 아니라 "Service"로 노출
        self.bot.weather_service = self.service

        
        # ===================== Fish alert (channel mention only) =====================
        # repo를 bot에 붙여서 View/버튼에서 접근 가능하게 함
        if getattr(self.bot, "fish_alert_repo", None) is None:
            self.bot.fish_alert_repo = FishAlertRepo(base_dir="data/ffxiv/fish/compiled")

        # dispatcher도 1회만 생성/시작
        if getattr(self.bot, "fish_alert_dispatcher", None) is None:
            self.bot.fish_alert_dispatcher = FishAlertDispatcher(
                self.bot,
                self.bot.fish_alert_repo,
                self.tug_db,
            )
            self.bot.fish_alert_dispatcher.start()

    async def _send(
        self,
        inter: discord.Interaction,
        *,
        content: str | None = None,
        embed: discord.Embed | None = None,
        files: list[discord.File] | None = None,
        view: discord.ui.View | None = None,
        ephemeral: bool = False,
    ):
        files = files or []
        kwargs = {"content": content, "embed": embed, "ephemeral": ephemeral}
        if files:
            kwargs["files"] = files
        if view is not None:
            kwargs["view"] = view
        return await inter.followup.send(**kwargs)

    async def _prompt_zone_select(
        self,
        inter_or_msg,  # discord.Interaction 또는 discord.Message
        *,
        candidates: list[str],
        mode: str,  # "now" | "find"
        target_ko: str | None = None,
    ):
        title = self.service.t("weather.ui.choose_zone_title")
        desc = self.service.t("weather.msg.ask_where")
        placeholder = self.service.t("weather.ui.select.placeholder")

        zone_options: list[tuple[str, str]] = []
        for en in candidates[:25]:
            label = to_korean_zone(en) or en
            zone_options.append((label, en))

        async def on_select(inter2: discord.Interaction, zone_key: str):
            if mode == "now":
                await self._send_now(inter2, zone_key)
            else:
                await self._send_find(inter2, zone_key, target_ko or "")

        view = ZoneSelectView(
            title=title,
            desc=desc,
            placeholder=placeholder,
            zone_options=zone_options,
            on_select=on_select,
        )

        # ✅ 슬래시(interaction) / 자연어(message) 둘 다 지원
        if isinstance(inter_or_msg, discord.Message):
            await inter_or_msg.reply(embed=view.build_prompt_embed(), view=view, mention_author=False)
        else:
            await self._send(inter_or_msg, embed=view.build_prompt_embed(), view=view, ephemeral=True)

    async def _send_now(self, inter: discord.Interaction, zone_key: str):
        payload = self.service.build_now_payload(zone_key=zone_key, user_id=inter.user.id)

        if not payload.get("ok"):
            msg = self.service.t("weather.err.zone_not_found", zone_ko=payload.get("zone_ko") or zone_key)

            # ✅ Select에서 온 interaction이면: 선택창 메시지 자체를 수정
            if getattr(inter, "message", None) is not None:
                await inter.response.edit_message(content=msg, embed=None, view=None)
                return

            # ✅ 슬래시에서 온 interaction이면: original response 수정
            return await inter.edit_original_response(content=msg, embed=None, view=None, attachments=[])

        embed, files = self.embed_factory.build_now(
            zone_ko=payload["zone_ko"],
            w_now_ko=payload["w_now_ko"],
            w_next_ko=payload["w_next_ko"],
            w_after_ko=payload["w_after_ko"],
            left_text=payload["left_text"],
            et_hour=payload["et_hour"],
            icon_path=payload["icon_path"],
        )

        view = WeatherHomeView(
            bot=self.bot,
            zone_key=zone_key,
            service=self.service,
            embed_factory=self.embed_factory,
            tug_db=getattr(self, "tug_db", None),
        )

        # ✅ Select에서 온 interaction이면: 선택창 메시지를 결과로 덮어쓰기
        if getattr(inter, "message", None) is not None:
            # discord.py 버전에 따라 attachments/files 차이가 있어서 try/except
            try:
                await inter.response.edit_message(
                    content=None,
                    embed=embed,
                    view=view,
                    attachments=files if files else [],
                )
            except TypeError:
                await inter.response.edit_message(
                    content=None,
                    embed=embed,
                    view=view,
                    files=files or [],
                )
            return

        # ✅ 슬래시: original response 덮어쓰기
        try:
            return await inter.edit_original_response(
                content=None,
                embed=embed,
                view=view,
                attachments=files if files else [],
            )
        except TypeError:
            return await inter.edit_original_response(
                content=None,
                embed=embed,
                view=view,
            )

    async def _send_find(self, inter: discord.Interaction, zone_key: str, target_ko: str):
        payload = self.service.build_find_payload(zone_key=zone_key, target_ko=target_ko)

        if not payload.get("ok"):
            msg = payload["content"]

            if getattr(inter, "message", None) is not None:
                await inter.response.edit_message(content=msg, embed=None, view=None)
                return

            return await inter.edit_original_response(content=msg, embed=None, view=None, attachments=[])

        embed = self.embed_factory.build_find_success(
            zone_ko=payload["zone_ko"],
            weather_ko=payload["weather_ko"],
            unix=payload["unix"],
            et_hour=payload["et_hour"],
        )

        if getattr(inter, "message", None) is not None:
            await inter.response.edit_message(content=None, embed=embed, view=None)
            return

        return await inter.edit_original_response(content=None, embed=embed, view=None, attachments=[])

    # ===================== Natural language bridge =====================

    async def reply_weather_from_message(self, message: discord.Message):
        """natural_language.py -> 일반 날씨 응답"""
        if not message or not message.content or message.author.bot:
            return

        content = (message.content or "").strip()

        zone_input = extract_city_name(content)
        zone_input = self.service.normalize_zone_input(zone_input)

        res = self.service.resolve_zone(zone_input)

        # ✅ now(일반 날씨)에서 후보 2개 이상이면 선택창(롤백 원하는 UX)
        if len(res.candidates) >= 2:
            return await self._prompt_zone_select(
                message,
                candidates=res.candidates,
                mode="now",
            )

        # 후보 0이면 실패
        if not res.zone_key and not res.candidates:
            await message.reply(self.service.t("weather.msg.not_found", text=zone_input), mention_author=False)
            return

        # zone_key 없으면 후보 1개 채택
        if not res.zone_key and res.candidates:
            res.zone_key = res.candidates[0]

        payload = self.service.build_now_payload(zone_key=res.zone_key, user_id=message.author.id)
        if not payload.get("ok"):
            await message.reply(self.service.t("weather.msg.not_found", text=zone_input), mention_author=False)
            return

        embed, files = self.embed_factory.build_now(
            zone_ko=payload["zone_ko"],
            w_now_ko=payload["w_now_ko"],
            w_next_ko=payload["w_next_ko"],
            w_after_ko=payload["w_after_ko"],
            left_text=payload["left_text"],
            et_hour=payload["et_hour"],
            icon_path=payload["icon_path"],
        )

        # ✅ 자연어도 /날씨와 동일 UI (홈 버튼들)
        view = WeatherHomeView(
            bot=self.bot,
            zone_key=res.zone_key,
            service=self.service,
            embed_factory=self.embed_factory,
            tug_db=getattr(self, "tug_db", None),
        )
        await message.reply(embed=embed, files=files, view=view, mention_author=False)

    async def reply_weather_find_from_message(self, message: discord.Message):
        """natural_language.py -> '지역 날씨 언제' 응답"""
        if not message or not message.content or message.author.bot:
            return

        import re  # 붙여넣기 실수 줄이려고 여기 둠(싫으면 파일 맨 위로 빼도 됨)

        content = (message.content or "").strip()

        # 예: "림사 안개 언제", "커르다스 눈보라 몇 시?"
        m = re.match(
            r"^\s*(?P<zone>.+?)\s+(?P<weather>.+?)\s*(?:언제|몇\s*시)\s*\??\s*$",
            content,
        )
        if not m:
            await message.reply(self.service.t("weather.find.fail_parse"), mention_author=False)
            return

        zone_input = self.service.normalize_zone_input(m.group("zone").strip())
        target_ko = self.service.normalize_weather_input_ko(m.group("weather").strip())

        res = self.service.resolve_zone(zone_input)

        # ✅ 후보가 여러개면(=애매하면) 무조건 선택창
        if len(res.candidates) >= 2:
            return await self._prompt_zone_select(
                message,
                candidates=res.candidates,
                mode="find",
                target_ko=target_ko,
            )

        # ✅ 후보가 0이면 실패
        if not res.zone_key and not res.candidates:
            await message.reply(self.service.t("weather.msg.not_found", text=zone_input), mention_author=False)
            return

        # ✅ zone_key 없으면 후보 1개를 채택
        if not res.zone_key and res.candidates:
            res.zone_key = res.candidates[0]

        payload = self.service.build_find_payload(zone_key=res.zone_key, target_ko=target_ko)
        if not payload.get("ok"):
            await message.reply(payload["content"], mention_author=False)
            return

        embed = self.embed_factory.build_find_success(
            zone_ko=payload["zone_ko"],
            weather_ko=payload["weather_ko"],
            unix=payload["unix"],
            et_hour=payload["et_hour"],
        )
        await message.reply(embed=embed, mention_author=False)

    # ===================== Slash Commands =====================

    @app_commands.command(name="날씨", description="FFXIV 지역의 현재 날씨 정보를 표시합니다.")
    async def cmd_weather(self, inter: discord.Interaction, 지역: str):
        await inter.response.defer(thinking=True)

        zone_input = extract_city_name(지역) if 지역 else ""
        zone_input = self.service.normalize_zone_input(zone_input)

        res = self.service.resolve_zone(zone_input)

        # ✅ 후보가 2개 이상이면 zone_key가 있어도 선택창 우선
        if len(res.candidates) >= 2:
            return await self._prompt_zone_select(inter, candidates=res.candidates, mode="now")

        # ✅ 후보 1개면 그걸로, zone_key 있으면 그대로
        zone_key = res.zone_key or (res.candidates[0] if res.candidates else None)
        if zone_key:
            return await self._send_now(inter, zone_key)

        # 못 찾음
        return await self._send(
            inter,
            content=self.service.t("weather.err.zone_not_found", zone_ko=zone_input),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(WeatherCog(bot))
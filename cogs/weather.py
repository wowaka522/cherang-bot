# cogs/weather.py
import os
import time
import discord
from discord import app_commands
from discord.ext import commands

from ffxiv_weather import (
    WEATHER_WINDOW_MS,
    find_zone_matches,
    get_weather,
    get_weather_at,
    to_korean_zone,
    to_korean_weather,
    get_weather_icon_filename
)

from utils.text_cleaner import extract_city_name


class WeatherCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==========================
    # /날씨 슬래시
    # ==========================
    @commands.Cog.listener()
    @app_commands.command(name="날씨", description="파판14 지역 날씨를 보여준다냥")
    @app_commands.describe(지역="지역 일부를 입력해줘 (예: 림사 / 라노시아)")
    async def weather_cmd(self, interaction: discord.Interaction, 지역: str):
        await self.send_weather_from_text(interaction, 지역, followup=False)

    # ==========================
    # 자연어: AIChat에서 호출
    # ==========================
    async def reply_weather_from_message(self, msg: discord.Message, city: str = None):
        city = extract_city_name(msg.content)
        if not city:
            return await msg.reply("어디 날씨를 알려줘야 하는 건데?")

        class DummyInteraction:
            def __init__(self, msg):
                self.msg = msg
                self.followup = self

            async def send(self, embed=None, files=None, **kwargs):
                await self.msg.reply(embed=embed, files=files, mention_author=False)

        dummy = DummyInteraction(msg)
        await self.send_weather_from_text(dummy, city, followup=True)

    # ==========================
    # 공통 UI 처리
    # ==========================
    async def send_weather_from_text(self, inter: discord.Interaction, text: str, followup: bool):
        matches = find_zone_matches(text)

        if not matches:
            return await inter.response.send_message(
                f"❌ '{text}' 지역을 찾지 못했다냥.",
                ephemeral=True
            ) if not followup else await inter.followup.send(f"❌ '{text}' 지역을 찾지 못했다냥.")

        # 후보 여러 개 → 선택 메뉴
        if len(matches) > 1:
            view = discord.ui.View()
            options = [
                discord.SelectOption(label=to_korean_zone(z), value=z)
                for z in matches[:25]
            ]
            select = discord.ui.Select(
                placeholder="지역을 선택해줘!",
                options=options,
                min_values=1, max_values=1,
            )
            view.add_item(select)

            async def select_callback(inter2: discord.Interaction):
                zone_key = select.values[0]
                await inter2.response.defer()
                await self.send_weather_embed(inter2, zone_key, followup=True)

            select.callback = select_callback

            return await inter.response.send_message(
                "🔎 다음 중에서 선택해줘!",
                view=view,
                ephemeral=True,
            ) if not followup else await inter.followup.send(
                "🔎 다음 중에서 선택해줘!",
                view=view,
            )

        # 1개면 바로 출력
        zone_key = matches[0]
        await self.send_weather_embed(inter, zone_key, followup=followup)

    # ==========================
    # Embed 실제 출력
    # ==========================
    async def send_weather_embed(self, inter: discord.Interaction, zone_key: str, followup: bool):
        now_ms = int(time.time() * 1000)

        w_now = get_weather(zone_key)
        w_next = get_weather_at(zone_key, now_ms + WEATHER_WINDOW_MS)
        w_next2 = get_weather_at(zone_key, now_ms + 2 * WEATHER_WINDOW_MS)

        zone_ko = to_korean_zone(zone_key)
        remain_ms = (WEATHER_WINDOW_MS - (now_ms % WEATHER_WINDOW_MS))
        remain_sec = remain_ms // 1000
        m, s = divmod(remain_sec, 60)
        left_text = f"{m:02d}:{s:02d}"
        et_hour = int((now_ms / 175000) % 24)

        embed = discord.Embed(
            title=f"🌤️ {zone_ko} 날씨 정보",
            description=f"⏳ 다음 날씨까지 **{left_text}** 남음\n🔹 **ET** {et_hour:02d}:00\n",
            color=0x00AEEF,
        )

        # 아이콘
        icon_filename = get_weather_icon_filename(w_now)
        icon_path = os.path.join("assets", "weather_icons", icon_filename)
        files = []
        if os.path.exists(icon_path):
            files.append(discord.File(icon_path, filename=icon_filename))
            embed.set_thumbnail(url=f"attachment://{icon_filename}")

        embed.add_field(name="지금", value=to_korean_weather(w_now))
        embed.add_field(name="다음", value=to_korean_weather(w_next))
        embed.add_field(name="다다음", value=to_korean_weather(w_next2))

        if followup:
            await inter.followup.send(embed=embed, files=files)
        else:
            await inter.response.send_message(embed=embed, files=files)


async def setup(bot):
    await bot.add_cog(WeatherCog(bot))
    print("✨ WeatherCog Loaded!")

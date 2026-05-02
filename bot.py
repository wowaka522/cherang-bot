from __future__ import annotations

import logging
import os
import traceback
from dataclasses import dataclass
from typing import List, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands

from dotenv import load_dotenv

# ✅ Step 1: Repositories 주입
from repositories import GuildRepo, SessionRepo, UserRepo

# ✅ Texts(문구/대사) 로더
from services.texts import Texts

# ✅ Step 2: 공통 유틸 서비스 레이어
from services.http_client import HttpClient
from services.cache import TTLCache, RateLimiter
from services.ffxiv.market_service import MarketService
from services.ffxiv.tug_db import TugDB
from repositories.fish_alert_repo import FishAlertRepo
from services.fish_alert_dispatcher import FishAlertDispatcher

# -----------------------------
# .env load
# -----------------------------
load_dotenv()


# -----------------------------
# Config
# -----------------------------
@dataclass(frozen=True)
class BotConfig:
    token: str
    guild_id: Optional[int] = None  # DEV_GUILD_ID
    log_level: str = "INFO"


def load_config() -> BotConfig:
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise RuntimeError("DISCORD_TOKEN이 비어있음 (.env 확인)")

    guild_id_raw = os.getenv("DEV_GUILD_ID", "").strip()
    guild_id = int(guild_id_raw) if guild_id_raw else None

    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    return BotConfig(token=token, guild_id=guild_id, log_level=log_level)


# -----------------------------
# Logging
# -----------------------------
def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("discord").setLevel(logging.INFO)


log = logging.getLogger("cherangbot")


# -----------------------------
# Extensions (LIST MODE FIXED)
# -----------------------------
EXTENSIONS: List[str] = [
    "cogs.ffxiv.market",
    "cogs.ffxiv.weather",
    "cogs.ffxiv.natural_language",
]


async def load_extensions(
    bot: commands.Bot,
    extensions: List[str],
) -> Tuple[List[str], List[Tuple[str, str]]]:
    loaded: List[str] = []
    failed: List[Tuple[str, str]] = []

    for ext in extensions:
        try:
            await bot.load_extension(ext)
            loaded.append(ext)
            log.info("Loaded: %s", ext)
        except Exception as e:
            reason = "".join(traceback.format_exception(type(e), e, e.__traceback__)).strip()
            failed.append((ext, reason))
            log.error("FAILED: %s\n%s", ext, reason)

    return loaded, failed


# -----------------------------
# Step 1: Repos Container
# -----------------------------
@dataclass
class Repos:
    user: UserRepo
    guild: GuildRepo
    session: SessionRepo


# -----------------------------
# Bot
# -----------------------------
class CherangBot(commands.Bot):
    def __init__(self, config: BotConfig):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        self.config = config

        self.repos = Repos(
            user=UserRepo(),
            guild=GuildRepo(),
            session=SessionRepo(),
        )

        # ✅ 슬래시 커맨드 에러 공통 처리
        self.tree.on_error = self.on_app_command_error  # type: ignore

        # ✅ Step 2 서비스들 (setup_hook에서 초기화)
        self.http_client: Optional[HttpClient] = None
        self.cache: Optional[TTLCache] = None
        self.rate: Optional[RateLimiter] = None
        self.market_svc: Optional[MarketService] = None

        # ✅ Tug DB 경로 (compiled)
        self.tug_db_path = r"data/ffxiv/fish/compiled/final_fishing_db.json"

        # ✅ 알림 디스패처(1회 알림)
        self.tug_db: Optional[TugDB] = None
        self.alert_repo: Optional[FishAlertRepo] = None
        self.fish_alert_dispatcher: Optional[FishAlertDispatcher] = None

    async def setup_hook(self) -> None:
        # ✅ Texts 로드
        self.texts = Texts("data/text")
        try:
            self.texts.load_folder("common")
        except Exception:
            pass
        try:
            self.texts.load_folder("ffxiv")
        except Exception:
            pass

        # ✅ Step 2: 공통 HTTP/캐시/마켓 서비스 준비
        # (중요) self.http 절대 금지! discord.py 내부 필드랑 충돌함.
        self.http_client = HttpClient(timeout_sec=10)
        await self.http_client.start()

        self.cache = TTLCache(default_ttl=10, max_items=2048)
        self.rate = RateLimiter(interval_sec=0.25)
        self.market_svc = MarketService(self.http_client, self.cache, self.rate)

        log.info("Load mode=list (fixed). extensions=%d", len(EXTENSIONS))

        loaded, failed = await load_extensions(self, EXTENSIONS)

        if failed:
            log.error("---- Extension Load Failures (%d) ----", len(failed))
            for ext, reason in failed:
                log.error("[FAIL] %s\n%s", ext, reason)
            log.error("--------------------------------------")
        else:
            log.info("All extensions loaded successfully. (%d)", len(loaded))

        # ✅ 슬래시 sync (길드 전용 운영)
        try:
            if self.config.guild_id:
                guild = discord.Object(id=self.config.guild_id)

                # ⭐ 개발/운영 모두 길드만 쓸 거면 이 조합이 제일 안정적
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)

                log.info("Slash synced to guild(%s): %d", self.config.guild_id, len(synced))
                log.info("Tree commands now (guild): %s", [c.name for c in self.tree.get_commands(guild=guild)])
            else:
                log.warning("DEV_GUILD_ID 없음: 글로벌 publish 방지 위해 sync 스킵")
        except Exception as e:
            reason = "".join(traceback.format_exception(type(e), e, e.__traceback__)).strip()
            log.error("Slash sync FAILED\n%s", reason)

    async def close(self) -> None:
        # ✅ Step 2: aiohttp 세션 종료
        try:
            if self.http_client:
                await self.http_client.close()
        except Exception:
            log.exception("Failed to close http_client")

        await super().close()

    async def on_ready(self) -> None:
        log.info("Logged in as %s (id=%s)", self.user, self.user.id if self.user else "N/A")

        # ✅ dispatcher는 1번만
        if self.fish_alert_dispatcher:
            return

        try:
            self.tug_db = TugDB(self.tug_db_path)
            self.alert_repo = FishAlertRepo("data/ffxiv/fish/compiled")
            self.fish_alert_dispatcher = FishAlertDispatcher(self, self.alert_repo, self.tug_db)
            self.fish_alert_dispatcher.start()
            log.info("Fish alert dispatcher started.")
        except Exception:
            log.exception("Failed to start Fish alert dispatcher")

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        base = getattr(error, "original", error)
        reason = "".join(traceback.format_exception(type(base), base, base.__traceback__)).strip()
        log.error(
            "AppCommandError: user=%s cmd=%s\n%s",
            interaction.user if interaction else None,
            interaction.command.qualified_name if interaction and interaction.command else None,
            reason,
        )

        try:
            msg = "⚠️ 처리 중 오류가 발생했어. (로그를 확인해줘)"
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            log.exception("Failed to send error response")

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        log.error("Event error in %s", event_method)
        log.error(traceback.format_exc())


# -----------------------------
# Entrypoint
# -----------------------------
def main() -> None:
    config = load_config()
    setup_logging(config.log_level)

    bot = CherangBot(config)

    try:
        bot.run(config.token, log_handler=None)
    except KeyboardInterrupt:
        log.info("KeyboardInterrupt: shutting down.")
    except Exception:
        log.exception("Bot crashed unexpectedly")


if __name__ == "__main__":
    main()
"""
logging.py
----------------
Structured logging setup with async Slack notification support.

Usage:
    from app.core.logging import setup_logging, get_logger

    setup_logging()  # Call once at app startup (e.g. in main.py or lifespan)
    logger = get_logger(__name__)

    logger.info("Starting up")
    logger.success("Order processed", extra={"channel": "sales"})
    logger.warning("Retrying payment")
    logger.error("Unhandled exception", exc_info=True)
"""

from __future__ import annotations

import asyncio
import logging
import logging.config
from typing import Optional

import httpx

from app.config import settings

SUCCESS_LEVEL_NUM = 25
SUCCESS_LEVEL_NAME = "SUCCESS"

logging.addLevelName(SUCCESS_LEVEL_NUM, SUCCESS_LEVEL_NAME)


def _success(self: logging.Logger, message: str, *args, **kwargs) -> None:
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kwargs)


logging.Logger.success = _success  # type: ignore[attr-defined]


_http_client: Optional[httpx.AsyncClient] = None


def _get_http_client() -> httpx.AsyncClient:
    """Return the shared AsyncClient, creating it on first call."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=httpx.Timeout(5.0))
    return _http_client


async def close_http_client() -> None:
    """Gracefully close the shared client. Call during app shutdown."""
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


_TITLE_MAP: dict[str, str] = {
    "info":     "INFO",
    "warning":  "WARNING",
    "error":    "ERROR",
    "critical": "CRITICAL",
    "debug":    "DEBUG",
    "success":  "SUCCESS",
}

_EMOJI_MAP: dict[str, str] = {
    "info":     "ℹ️",
    "warning":  "⚠️",
    "error":    "🔴",
    "critical": "🚨",
    "success":  "✅",
    "debug":    "🐛",
}

_COLOR_MAP: dict[str, str] = {
    "info":     "#36a64f",
    "warning":  "#FFC107",
    "error":    "#FF0000",
    "critical": "#8B0000",
    "debug":    "#555555",
    "success":  "#2ECC71",
}


def _build_slack_payload(text: str, level: str) -> dict:
    """Build a Slack attachment payload for *text* at *level*."""
    level = level.lower()
    title = f"{_EMOJI_MAP.get(level, 'ℹ️')} {_TITLE_MAP.get(level, 'NOTIFICATION')}"
    return {
        "attachments": [
            {
                "fallback": text,
                "color": _COLOR_MAP.get(level, "#FF0000"),
                "title": title,
                "text": text,
            }
        ]
    }

_CHANNEL_MAP_ATTR = "SLACK_ALERTS"  # resolved lazily so settings isn't read at import


def _resolve_url(channel: str, webhook_url: Optional[str]) -> Optional[str]:
    if webhook_url:
        return webhook_url
    channel_map = {
        "alerts": getattr(settings, "SLACK_ALERTS", None),
        "orders": getattr(settings, "SLACK_ORDERS", None),
    }
    return channel_map.get(channel)


async def send_slack_message(
    text: str,
    *,
    level: str = "info",
    channel: str = "alerts",
    webhook_url: Optional[str] = None,
) -> bool:
    """
    Send *text* to Slack asynchronously.

    Returns True on HTTP 200, False on any failure (never raises).
    """
    url = _resolve_url(channel, webhook_url)
    if not url:
        logging.getLogger(__name__).error(
            "No Slack webhook configured for channel %r", channel
        )
        return False

    payload = _build_slack_payload(text, level)
    try:
        client = _get_http_client()
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return True
    except httpx.HTTPStatusError as exc:
        logging.getLogger(__name__).error(
            "Slack returned %s for channel %r: %s",
            exc.response.status_code,
            channel,
            exc.response.text,
        )
    except Exception:
        logging.getLogger(__name__).exception(
            "Unexpected error sending Slack message to channel %r", channel
        )
    return False


class SlackLogHandler(logging.Handler):
    """
    Async-safe logging handler that forwards log records to Slack.

    Works in both sync and async contexts:
      - Inside a running event loop: schedules a fire-and-forget task.
      - Outside a running event loop (e.g. startup scripts): runs synchronously
        via asyncio.run().

    Only records at or above SUCCESS_LEVEL_NUM (25) are forwarded.

    Per-record channel override:
        logger.error("Payment failed", extra={"channel": "orders"})
    """

    def __init__(self, channel: str = "alerts") -> None:
        super().__init__(level=SUCCESS_LEVEL_NUM)
        self.channel = channel
        self._pending_tasks: set[asyncio.Task] = set()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            channel = getattr(record, "channel", self.channel)
            level = record.levelname.lower()

            coro = send_slack_message(message, level=level, channel=channel)
            self._dispatch(coro)
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        """Cancel any pending tasks and close the handler."""
        for task in list(self._pending_tasks):
            task.cancel()
        super().close()

    def _dispatch(self, coro) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop — safe to block (e.g. CLI scripts, pytest)
            asyncio.run(coro)
            return

        task = loop.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._on_task_done)

    def _on_task_done(self, task: asyncio.Task) -> None:
        self._pending_tasks.discard(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            # Use handleError-style logging to avoid infinite recursion
            logging.getLogger(__name__).error(
                "SlackLogHandler background task raised: %s", exc
            )


# ---------------------------------------------------------------------------
# Logging configuration dict
# ---------------------------------------------------------------------------

LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "standard",
        },
        "slack_alerts": {
            # "()" lets dictConfig call SlackLogHandler(channel="alerts")
            "()": SlackLogHandler,
            "level": SUCCESS_LEVEL_NUM,
            "formatter": "standard",
            "channel": "alerts",
        },
    },
    "loggers": {
        # Root logger: console only, warnings and above
        "": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        # Application logger: full pipeline including Slack
        "app": {
            "handlers": ["console", "slack_alerts"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}


def setup_logging() -> None:
    """
    Apply the logging configuration.

    Call this ONCE at application startup — not at import time.

        # main.py or lifespan
        from app.core.logging_slack import setup_logging
        setup_logging()
    """
    logging.config.dictConfig(LOGGING_CONFIG)


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger namespaced under 'app.' so it inherits the full pipeline.

    Example:
        logger = get_logger(__name__)   # e.g. app.services.payments
    """
    if not name.startswith("app."):
        name = f"app.{name}"
    return logging.getLogger(name)


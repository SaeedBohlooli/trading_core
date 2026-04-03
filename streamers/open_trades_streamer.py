import asyncio
import hashlib
import json
import logging
import time

from trading_core import engine_cycle
from trading_utils import date_utils
from trading_utils import streaming_util

logger = logging.getLogger(__name__)


class OpenTradesStreamer:
    """
    Emits type 'open_trades' from application_state['open_trades_dic'].
    Broadcasts when the sanitized payload changes (MD5 of stable JSON).
    """

    def __init__(self, app_config, app_state, ws_server, interval_sec=1):
        self.app_config = app_config
        self.app_state = app_state
        self.ws = ws_server
        self.interval_sec = interval_sec
        self._last_hash = None

    def _open_trades_body(self):
        otd = self.app_state.get("open_trades_dic") or {}
        return streaming_util.sanitize_for_json(dict(otd))

    def _payload_hash(self, body: dict) -> str:
        raw = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    async def run(self):
        if not self.app_config.get("streams", {}).get("enable_open_trades", True):
            logger.info("[OpenTradesStreamer] disabled via config")
            return

        while True:
            if engine_cycle.should_exit(application_state=self.app_state):
                logger.info("[OpenTradesStreamer] Exiting as requested.")
                break
            loop_start = time.monotonic()
            try:
                body = {"open_trades_dic": self._open_trades_body()}
                h = self._payload_hash(body)
                changed = h != self._last_hash
                n = len(body["open_trades_dic"])
                if changed:
                    self._last_hash = h
                    packet = {
                        "type": "open_trades",
                        "data": body,
                        "timestamp": date_utils.time_now_yyyy_mm_dd_hh_mm_ss(),
                    }
                    await self.ws.broadcast(packet)
                    logger.info(f"[OpenTradesStreamer] changed=True size={n}")
                else:
                    logger.debug(f"[OpenTradesStreamer] changed=False size={n}")
            except Exception as e:
                logger.error(f"[OpenTradesStreamer] error: {e}", exc_info=True)

            elapsed = time.monotonic() - loop_start
            sleep_for = max(0.0, float(self.interval_sec) - elapsed)
            await asyncio.sleep(sleep_for)

import asyncio
import hashlib
import json
import logging
import time

from trading_core import engine_cycle
from trading_utils import date_utils
from trading_utils import global_state
from trading_utils import streaming_util

logger = logging.getLogger(__name__)


class QuoteCacheStreamer:
    """
    Emits type 'quote_cache' with a JSON snapshot of the quote map from **application_state**
    (key ``global_state.quote_cache``), populated by ``application_state_router.populate_global_state``
    — same underlying data as ``global_state.quote_cache`` when the router has run.
    Keys are conId strings; values match ib_pricing_async.on_ticker_update rows.
    Broadcasts when payload hash changes, and on a periodic interval for resync.
    """

    def __init__(self, app_config, app_state, ws_server, interval_sec=1):
        self.app_config = app_config
        self.app_state = app_state
        self.ws = ws_server
        self.interval_sec = interval_sec
        self._last_hash = None
        self._last_emit_at = None
        force = app_config.get("interval_seconds", {}).get("quote_cache_force_emit")
        self._force_emit_sec = float(force) if force is not None else 15.0

    def _build_data(self) -> dict:
        qc = self.app_state.get("global_state.quote_cache")
        if qc is None:
            qc = global_state.quote_cache
        out: dict[str, dict] = {}
        for con_id, row in qc.items():
            key = str(con_id)
            if isinstance(row, dict):
                out[key] = streaming_util.sanitize_for_json(dict(row))
            else:
                out[key] = streaming_util.sanitize_for_json(row)
        return {
            "global_state.quote_cache": out,
            "count": len(out),
        }

    def _payload_hash(self, data: dict) -> str:
        raw = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    async def run(self):
        if not self.app_config.get("streams", {}).get("enable_quote_cache", True):
            logger.info("[QuoteCacheStreamer] disabled via config")
            return

        while True:
            if engine_cycle.should_exit(application_state=self.app_state):
                logger.info("[QuoteCacheStreamer] Exiting as requested.")
                break
            loop_start = time.monotonic()
            try:
                now = time.monotonic()
                data = self._build_data()
                h = self._payload_hash(data)
                changed = h != self._last_hash
                initial = self._last_emit_at is None
                periodic = (
                    self._last_emit_at is not None
                    and (now - self._last_emit_at) >= self._force_emit_sec
                )
                if initial or changed or periodic:
                    if changed:
                        self._last_hash = h
                    packet = {
                        "type": "quote_cache",
                        "data": data,
                        "timestamp": date_utils.time_now_yyyy_mm_dd_hh_mm_ss(),
                    }
                    await self.ws.broadcast(packet)
                    self._last_emit_at = now
                    logger.info(
                        f"[QuoteCacheStreamer] broadcast changed={changed} "
                        f"initial={initial} periodic={periodic} count={data['count']}"
                    )
            except Exception as e:
                logger.error(f"[QuoteCacheStreamer] error: {e}", exc_info=True)

            elapsed = time.monotonic() - loop_start
            sleep_for = max(0.0, float(self.interval_sec) - elapsed)
            await asyncio.sleep(sleep_for)

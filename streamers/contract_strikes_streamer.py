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


class ContractStrikesStreamer:
    """
    Emits type 'contract_strikes' from global_state.option_contract_cache
    (stringified for JSON). Broadcasts on change and on a periodic snapshot
    interval (contract_strikes_force_emit) so clients can resync.
    """

    def __init__(self, app_config, app_state, ws_server, interval_sec=1):
        self.app_config = app_config
        self.app_state = app_state
        self.ws = ws_server
        self.interval_sec = interval_sec
        self._last_hash = None
        self._last_emit_at = None
        force = app_config.get("interval_seconds", {}).get("contract_strikes_force_emit")
        self._force_emit_sec = float(force) if force is not None else 15.0

    def _build_data(self) -> dict:
        stringified = global_state.stringify_option_cache(global_state.option_contract_cache)
        stringified = streaming_util.sanitize_for_json(stringified)
        count = len(stringified)
        by_symbol: dict[str, int] = {}
        for k in stringified:
            sym = k.split("|")[0] if "|" in str(k) else str(k)
            by_symbol[sym] = by_symbol.get(sym, 0) + 1
        return {
            "option_contract_cache": stringified,
            "count": count,
            "bySymbol": by_symbol,
        }

    def _payload_hash(self, data: dict) -> str:
        raw = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    async def run(self):
        if not self.app_config.get("streams", {}).get("enable_contract_strikes", True):
            logger.info("[ContractStrikesStreamer] disabled via config")
            return

        while True:
            if engine_cycle.should_exit(application_state=self.app_state):
                logger.info("[ContractStrikesStreamer] Exiting as requested.")
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
                        "type": "contract_strikes",
                        "data": data,
                        "timestamp": date_utils.time_now_yyyy_mm_dd_hh_mm_ss(),
                    }
                    await self.ws.broadcast(packet)
                    self._last_emit_at = now
                    logger.info(
                        f"[ContractStrikesStreamer] broadcast changed={changed} "
                        f"initial={initial} periodic={periodic} count={data['count']}"
                    )
            except Exception as e:
                logger.error(f"[ContractStrikesStreamer] error: {e}", exc_info=True)

            elapsed = time.monotonic() - loop_start
            sleep_for = max(0.0, float(self.interval_sec) - elapsed)
            await asyncio.sleep(sleep_for)

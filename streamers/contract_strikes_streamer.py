import asyncio
import hashlib
import json
import logging
import time
from typing import Any

from trading_core import engine_cycle
from trading_utils import date_utils
from trading_utils import global_state
from trading_utils import streaming_util

logger = logging.getLogger(__name__)

_CONTRACT_FIELDS = (
    "conId",
    "symbol",
    "lastTradeDateOrContractMonth",
    "strike",
    "right",
    "multiplier",
    "exchange",
    "currency",
    "localSymbol",
    "tradingClass",
    "secType",
)


def _contract_to_dict(contract: Any) -> dict:
    out: dict[str, Any] = {}
    for f in _CONTRACT_FIELDS:
        v = getattr(contract, f, None)
        if v is not None and v != "":
            out[f] = v
    if "strike" in out and out["strike"] is not None:
        out["strike"] = float(out["strike"])
    if "conId" in out and out["conId"] is not None:
        out["conId"] = int(out["conId"])
    return streaming_util.sanitize_for_json(out)


class ContractStrikesStreamer:
    """
    Emits type 'contract_strikes' from global_state.option_contract_cache.
    Payload is grouped by symbol: each symbol has one object with all contracts
    (strikes / expiries / ids) derived from qualified IB contract objects.
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
        cache = global_state.option_contract_cache
        by_conid: dict[int, dict] = {}

        for _key, contract in cache.items():
            row = _contract_to_dict(contract)
            cid = row.get("conId")
            if cid is None:
                continue
            by_conid[cid] = row

        grouped: dict[str, list[dict]] = {}
        for row in by_conid.values():
            sym = row.get("symbol") or "?"
            grouped.setdefault(sym, []).append(row)

        symbols_payload: dict[str, dict] = {}
        total = 0
        for sym in sorted(grouped.keys()):
            rows = grouped[sym]
            rows.sort(
                key=lambda r: (
                    str(r.get("lastTradeDateOrContractMonth") or ""),
                    float(r.get("strike") or 0.0),
                    str(r.get("right") or ""),
                    int(r.get("conId") or 0),
                )
            )
            exps = sorted(
                {str(r.get("lastTradeDateOrContractMonth")) for r in rows if r.get("lastTradeDateOrContractMonth")}
            )
            symbols_payload[sym] = {
                "symbol": sym,
                "contractCount": len(rows),
                "expirations": exps,
                "contracts": rows,
            }
            total += len(rows)

        return {
            "count": total,
            "symbolCount": len(symbols_payload),
            "symbols": symbols_payload,
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
                        f"initial={initial} periodic={periodic} count={data['count']} "
                        f"symbols={data['symbolCount']}"
                    )
            except Exception as e:
                logger.error(f"[ContractStrikesStreamer] error: {e}", exc_info=True)

            elapsed = time.monotonic() - loop_start
            sleep_for = max(0.0, float(self.interval_sec) - elapsed)
            await asyncio.sleep(sleep_for)

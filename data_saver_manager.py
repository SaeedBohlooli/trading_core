import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any

from trading_core.file_manager import FileManager
from trading_utils import ib_posttrade
from trading_core import engine_cycle
logger = logging.getLogger(__name__)


@dataclass
class DataSaverManager:
    ib_dir: str
    app_config: Dict[str, Any]
    application_state: Dict[str, Any]
    _last_save_times: Dict[str, float] = field(default_factory=dict)

    # -------------------------------------------------
    # Internal throttling logic
    # -------------------------------------------------
    def _should_run(self, key: str, min_interval_sec: int, force: bool) -> bool:
        if force:
            self._last_save_times[key] = time.time()
            return True

        now = time.time()
        last = self._last_save_times.get(key)

        if last is None or (now - last) >= min_interval_sec:
            self._last_save_times[key] = now
            return True

        return False

    # -------------------------------------------------
    # One-shot save (callable manually if needed)
    # -------------------------------------------------
    async def save_once(self, ib, force: bool = False) -> None:
        # 1) application_state (cheap)
        FileManager.save_named_json(self.application_state, "application_state")

        # 2) IB post-trade dfs (expensive → throttled)
        ib_interval = self.app_config.get("intervals", {}).get("ib_posttrade", 300)

        if self._should_run("ib_posttrade", ib_interval, force):
            logger.info("[DataSaverManager] Saving IB dataframes ...")
            await ib_posttrade.save_ib_dfs_async(self.ib_dir, ib)

        logger.info(f"[DataSaverManager] Save completed (force={force})")

    # -------------------------------------------------
    # Background loop (manager-owned)
    # -------------------------------------------------
    async def run(self, ib, interval_sec: int = 60) -> None:
        while True:
            if engine_cycle.should_exit(application_state=self.application_state):
                logger.info("[market_session_guard_loop] Exiting as requested.")
                break
            try:
                if self.application_state.get("is_busy_time", False):
                    logger.info("[DataSaverManager] Busy time ... skipping save")
                    await asyncio.sleep(30)
                    continue

                await self.save_once(ib, force=False)
                await asyncio.sleep(interval_sec)

            except Exception as e:
                logger.exception(f"@@@ [DataSaverManager] Unexpected error {e}")
                await asyncio.sleep(interval_sec)

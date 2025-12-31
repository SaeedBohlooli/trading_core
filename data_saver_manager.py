import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any

from trading_core.file_manager import FileManager
from trading_core.trading_ledger import TradingLedger
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
    def _should_run(self, key: str, min_interval_sec: int, force: bool, skip_first: bool = False) -> bool:
        if force:
            self._last_save_times[key] = time.time()
            return True

        now = time.time()
        last = self._last_save_times.get(key)

        if last is None:
            self._last_save_times[key] = now
            if skip_first:
                logger.debug(f"[DataSaver] {key} first call skipped")
                return False
            return True

        if (now - last) >= min_interval_sec:
            self._last_save_times[key] = now
            return True

        return False
    # -------------------------------------------------
    # One-shot save (callable manually if needed)
    # -------------------------------------------------

    def save_application_state(self, ib, force: bool = False) -> None:
        # 1) application_state (cheap)
        FileManager.save_named_json(self.application_state, "application_state")
        return

    async def save_once(self, ib, force: bool = False) -> None:

        # 2) IB post-trade dfs (expensive → throttled)
        ib_interval = self.app_config.get("intervals", {}).get("ib_posttrade", 300)

        if self._should_run("ib_posttrade", ib_interval, force, skip_first=True):
            logger.info("[DataSaverManager] Saving IB dataframes ...")
            await ib_posttrade.save_ib_dfs_async(self.ib_dir, ib)
            logger.info("[DataSaverManager] Finished Saving IB dataframes ...")

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
                self.save_application_state(ib)

                if not self.application_state.get("is_save_time", True):
                    logger.info("[DataSaverManager] not is_save_time ... skipping save")
                    await asyncio.sleep(interval_sec)
                    continue

                logger.info("[DataSaverManager] Running save_dfs_from_trading_ledger ...")
                self.save_dfs_from_trading_ledger()
                logger.info("[DataSaverManager] Finished save_dfs_from_trading_ledger ...")

                logger.info("DataSaverManager] Running save_once ...")
                await self.save_once(ib, force=False)
                logger.info("[DataSaverManager] Finished save_once ...")

                await asyncio.sleep(interval_sec)

            except Exception as e:
                logger.exception(f"@@@ [DataSaverManager] Unexpected error {e}")
                await asyncio.sleep(interval_sec)

    def save_dfs_from_trading_ledger(self):
        for df_stat in TradingLedger.get_all_dataframe_stats():
            df_name = df_stat['name']
            df = TradingLedger.get_dataframe(df_name)
            logger.info(f"[DataSaverManager] Saving from TradingLedger {df_name} ...")
            FileManager.save_my_df(df, df_name, mode='a', drop_duplicates=True, save_tabular=True, min_interval_sec=60)
from trading_utils import *
import logging
logger = logging.getLogger(__name__)
import sys
sys.path.insert(0, f'../')

from trading_core.ws_server import WSServer
from trading_core.streamers.state_streamer import StateStreamer
from trading_core.streamers.config_streamer import ConfigStreamer
from trading_core.ib_connector import IBConnector
from trading_core.file_manager import FileManager
from trading_core.market_data_store import MarketDataStore

from trading_utils import user_request_fetcher
from trading_utils import user_request_router


class TradingEngine:

    def __init__(self, boot):
        self.boot = boot
        self.logger = boot.logger
        self.app_config = boot.app_config
        self.application_state = boot.application_state
        self.ws = WSServer(host="0.0.0.0", port=self.app_config.get('ws_port', 6666))
        self.runtime = boot.runtime
        self.market_data = MarketDataStore()

        # generic per-target throttling
        self._last_custom_save_times: dict[str, float] = {}


    def _should_run_save(self, key: str, min_interval_sec: int, force: bool) -> bool:
        if force:
            self._last_custom_save_times[key] = time.time()
            return True

        now = time.time()
        last = self._last_custom_save_times.get(key)
        if last is None or (now - last) >= min_interval_sec:
            self._last_custom_save_times[key] = now
            return True
        return False

    async def save_all_all(self, ib, force=False):

        # self.runtime.save_application_state()
        FileManager.save_named_json(self.application_state, "application_state")

        ib_dir = self.boot.dirs.ib
        ib_interval = self.app_config.get('intervals',{}).get('ib_posttrade', 300)
        if self._should_run_save("ib_posttrade", ib_interval, force=force):
            # one place where ib_posttrade is called
            logger.info("[save_all_dataframes] Saving IB dataframes ...")
            await ib_posttrade.save_ib_dfs_async(ib_dir, ib)

        self.logger.info(f"[save_all_dataframes] Completed save (force={force})")


    # --------------------------
    # BELOW ARE YOUR LOOP HANDLERS
    # --------------------------

    async def engine_loop(self, ib):
        run_number = 0
        initial_setup = False
        while True:
            try:
                start_time = time.time()
                run_number += 1
                current_hh_mm_ny = self.runtime.now_hhmm()
                unique_run_number =  self.runtime.generate_unique_run_number(run_number)

                logger.warning(f"==================== unique_run_number: {unique_run_number}, current_hh_mm_ny: {current_hh_mm_ny}")
                if ib is None:
                    logger.warning("ib is None... so gie a try to reconnect ...")
                    await asyncio.sleep(3)
                    continue
                self.app_config = self.runtime.reload_config()

                end_time = time.time()
                run_time_spent = round(end_time - start_time, 2)
                logger.warning(f'==================== unique_run_number: {unique_run_number}, run_spent_time: {run_time_spent} seconds, no sleep ...')

                await asyncio.sleep(self.app_config['interval_seconds']['engine_loop'])
            except Exception as e:
                logger.warning(f"@@@ Unexpected error in engine_loop: {e}")
                logger.error(f"@@@ error: {traceback.format_exc()}" )
                await asyncio.sleep(self.app_config['interval_seconds']['engine_loop'])


    async def test_loop(self, ib):
        while True:
            try:
                logger.info("test_loop...")
                await asyncio.sleep(10)
            except Exception as e:
                logger.warning(f"Unexpected error: {e}")
                logger.error(f"@@@ error: {traceback.format_exc()}" )

    async def user_request_loop(self, ib):
        while True:
            try:
                user_request_fetcher.fetch_user_request(self.app_config, self.application_state)
                user_request_router.process_user_requests(ib, self.app_config, self.application_state)
                #user_request_helper.process_user_requests(self.app_config, self.application_state)

                logger.info("user_request_loop...")
                await asyncio.sleep(3)
            except Exception as e:
                logger.warning(f"Unexpected error: {e}")
                logger.error(f"@@@ error: {traceback.format_exc()}" )


    async def data_saver_loop(self, ib):
        while True:
            try:

                if self.application_state.get('is_busy_time', False):
                    self.logger.info("[data_saver] Busy hour -> skip save")
                    await asyncio.sleep(30)
                    continue

                await self.save_all_all(ib, force=False)

                await asyncio.sleep(60)

            except Exception as e:
                self.logger.error(f"@@@ [data_saver] Error: {e}")
                await asyncio.sleep(10)

    async def run(self):
        logger.info("Starting Trading Engine")
        ib = await IBConnector.connect_from_config(self.app_config)

        ws_server = await self.ws.start()

        state_streamer = StateStreamer(self.application_state, self.ws, interval=5)
        config_streamer = ConfigStreamer(self.app_config, self.ws, interval=12)

        self.logger.info("WebSocket server is starting...")

        await asyncio.gather(
            ws_server,
            state_streamer.run(),
            config_streamer.run(),
            self.engine_loop(ib),
            self.test_loop(ib),
            self.user_request_loop(ib),
            self.data_saver_loop(ib)
        )
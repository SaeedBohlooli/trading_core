import asyncio
import logging
import pprint

from trading_utils import date_utils
from trading_core import engine_cycle
from trading_utils import streaming_util
logger = logging.getLogger(__name__)

class StateStreamer:
    """
    Streams the application_state to all WebSocket clients.
    Reusable across all projects.
    """

    def __init__(self, app_config, app_state, ws_server, interval_sec=5):
        self.app_config = app_config
        self.app_state = app_state
        self.ws = ws_server
        self.interval_sec = interval_sec

    async def run(self):
        while True:
            if engine_cycle.should_exit(application_state=self.app_state):
                logger.info("[StateStreamer] Exiting as requested.")
                break
            state = self.app_state.copy()
            # state.pop('global_state.contract_cache', None)
            # state.pop('global_state.option_contract_cache', None)
            state = streaming_util.sanitize_for_json(state)
            try:
                packet = {
                    "type": "application_state",
                    "data": state,
                    "timestamp": date_utils.time_now_yyyy_mm_dd_hh_mm_ss(),
                }
                logger.info(f"[StateStreamer] Streaming ....unique_run_number: {self.app_state.get('unique_run_number')}")

                await self.ws.broadcast(packet)
                logger.info("[StateStreamer] Application state streamed.")

                await asyncio.sleep(self.interval_sec)

            except Exception as e:
                logger.error(f"[StateStreamer] @@@@ Unexpected error: {e}")
                logger.info(pprint.pformat(packet))
                logger.info(f"[StateStreamer] Retrying in 10 seconds...Check the message: {self.app_state} ")
                await asyncio.sleep(self.interval_sec)




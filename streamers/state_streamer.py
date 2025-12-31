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

    def __init__(self, app_config, app_state, ws_server, interval=5):
        self.app_config = app_config
        self.app_state = app_state
        self.ws = ws_server

    async def run(self):
        while True:
            if engine_cycle.should_exit(application_state=self.app_state):
                logger.info("[StateStreamer] Exiting as requested.")
                break
            self.interval = self.app_state.get('interval_seconds',{}).get('app_config_streamer', 5)
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
                logger.info("[StateStreamer] Streaming ....")

                await self.ws.broadcast(packet)
                logger.info("[StateStreamer] Application state streamed.")

                await asyncio.sleep(self.interval)

            except Exception as e:
                logger.error(f"[StateStreamer] @@@@ Unexpected error: {e}")
                print(pprint.pformat(packet))
                logger.info(f"[StateStreamer] Retrying in 10 seconds...Check the message: {self.app_state} ")
                await asyncio.sleep(self.interval)




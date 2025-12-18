import asyncio
import logging
from trading_utils import date_utils
from trading_core import engine_cycle
logger = logging.getLogger(__name__)

class ConfigStreamer:
    """
    Streams the application config to WebSocket clients.
    """

    def __init__(self, app_config, application_state, ws_server, interval=12):
        self.app_config = app_config
        self.application_state = application_state
        self.ws = ws_server
        self.interval = interval

    async def run(self):
        while True:
            if engine_cycle.should_exit(application_state=self.application_state):
                logger.info("[ConfigStreamer] Exiting as requested.")
                break
            self.interval = self.app_config.get('interval_seconds',{}).get('state_streamer', 10)
            try:
                packet = {
                    "type": "app_config",
                    "data": self.app_config,
                    "timestamp": date_utils.time_now_yyyy_mm_dd_hh_mm_ss(),
                }
                logger.info("[ConfigStreamer] App config streaming ....")
                await self.ws.broadcast(packet)
                logger.info("[ConfigStreamer] App config streamed.")

                await asyncio.sleep(self.interval)

            except Exception as e:
                logger.error(f"[ConfigStreamer] @@@@ Unexpected error: {e}")
                logger.info(f"[ConfigStreamer] Retrying in 10 seconds...Check the message: {self.app_config} ")

                await asyncio.sleep(self.interval)


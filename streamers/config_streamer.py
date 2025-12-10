import asyncio
import logging
from trading_utils import date_utils

logger = logging.getLogger(__name__)

class ConfigStreamer:
    """
    Streams the application config to WebSocket clients.
    """

    def __init__(self, app_config, ws_server, interval=12):
        self.app_config = app_config
        self.ws = ws_server
        self.interval = interval

    async def run(self):
        while True:
            try:
                packet = {
                    "type": "app_config",
                    "data": self.app_config,
                    "timestamp": date_utils.time_now_yyyy_mm_dd_hh_mm_ss(),
                }

                await self.ws.broadcast(packet)
                logger.info("[ConfigStreamer] App config streamed.")

                await asyncio.sleep(self.interval)

            except Exception as e:
                logger.error(f"[ConfigStreamer] Unexpected error: {e}")

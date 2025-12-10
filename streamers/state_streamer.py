import asyncio
import logging
from trading_utils import date_utils

logger = logging.getLogger(__name__)

class StateStreamer:
    """
    Streams the application_state to all WebSocket clients.
    Reusable across all projects.
    """

    def __init__(self, app_state, ws_server, interval=5):
        self.app_state = app_state
        self.ws = ws_server
        self.interval = interval

    async def run(self):
        while True:
            try:
                packet = {
                    "type": "application_state",
                    "data": self.app_state,
                    "timestamp": date_utils.time_now_yyyy_mm_dd_hh_mm_ss(),
                }

                await self.ws.broadcast(packet)
                logger.info("[StateStreamer] Application state streamed.")

                await asyncio.sleep(self.interval)

            except Exception as e:
                logger.error(f"[StateStreamer] Unexpected error: {e}")

import logging
logger = logging.getLogger(__name__)
import asyncio
import traceback
from trading_utils import user_request_fetcher



async def user_request_loop(app_config, application_state, interval_sec=3):
    while True:
        try:
            user_request_fetcher.fetch_user_request(app_config, application_state)
            logger.info("request_router...")
            await asyncio.sleep(interval_sec)
        except Exception as e:
            logger.warning(f"Unexpected error: {e}")
            logger.error(f"@@@ error: {traceback.format_exc()}" )
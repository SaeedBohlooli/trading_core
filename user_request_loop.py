import logging
logger = logging.getLogger(__name__)
import asyncio
import traceback
from trading_utils import user_request_fetcher
from trading_utils import user_request_router
from trading_core import engine_cycle


async def fetch_user_request_loop(app_config, application_state, interval_sec=3):
    while True:
        try:
            if engine_cycle.should_exit(application_state=application_state):
                logger.info("[fetch_user_request_loop] Exiting as requested.")
                break
            user_request_fetcher.fetch_user_request(app_config, application_state)
            logger.info("[fetch_user_request_loop] user requests are fetched.")
            await asyncio.sleep(interval_sec)
        except Exception as e:
            logger.warning(f"Unexpected error: {e}")
            logger.error(f"@@@ fetch_user_request_loop error: {traceback.format_exc()}" )
            await asyncio.sleep(interval_sec)

async def process_common_user_request_loop(ib, app_config, application_state, interval_sec=3):
    while True:
        if engine_cycle.should_exit(application_state=application_state):
            logger.info("[process_common_user_request_loop] Exiting as requested.")
            break
        try:

            await user_request_router.process_user_requests(ib, app_config, application_state)
            user_request_router.save_archived_user_requests(application_state)

            logger.info("[process_common_user_request_loop]...")
            await asyncio.sleep(interval_sec)
        except Exception as e:
            logger.warning(f"Unexpected error: {e}")
            logger.error(f"@@@ process_common_user_request_loop error: {traceback.format_exc()}")
            await asyncio.sleep(interval_sec)



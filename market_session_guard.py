import asyncio
import logging
import datetime

from trading_utils import market_session

logger = logging.getLogger(__name__)


async def market_session_guard_loop(ib, application_state, interval_sec=600):
    """
    Background task:
    - refreshes market session ONLY when needed
    - runs independently from engine loop
    """
    while True:
        try:
            await refresh_market_session_if_needed(ib, application_state)
        except Exception as e:
            logger.exception(f"[MarketSession] refresh failed: {e}")

        await asyncio.sleep(interval_sec)


async def init_market_session_time(ib, app_config, application_state):
    application_state["market_session"] = await market_session.calculate_market_session(ib)


async def refresh_market_session_if_needed(ib, application_state):
    ms = application_state.get("market_session")
    today = datetime.date.today().isoformat()

    if not ms or ms["date"] != today:
        application_state["market_session"] = await market_session.calculate_market_session(ib)
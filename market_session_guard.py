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
        logger.info(f"[MarketSession] Refreshing market session for date: {today}")
        application_state["market_session"] = await market_session.calculate_market_session(ib)

def is_market_open_based_on_ib(application_state):
    """
    {
  "date": "2025-12-16",
  "is_open": false,
  "start": "2025-12-16T04:00:00-05:00",
  "end": "2025-12-16T20:00:00-05:00",
  "timestamp": "2025-12-16 01:11:09"
    }
    :param application_state:
    :return:
    """
    ms = application_state.get("market_session", {})
    if not ms:
        logger.info(f"[MarketSession] No market session info available, assuming market is closed.")
        return False

    start = ms.get("start")
    end = ms.get("end")
    if start is None and end is None:
        logger.info(f"[MarketSession] No start/end info in market session: {ms}, assuming market is closed.")
        return False

    start = datetime.datetime.fromisoformat(ms["start"])
    end = datetime.datetime.fromisoformat(ms["end"])

    # example: now (timezone-aware, same offset as start/end)
    now = datetime.datetime.now(start.tzinfo)

    is_between = start <= now <= end

    return is_between



def is_trading_hours_based_on_config(app_config, application_state):
    """Determine if current time is within trading hours based on config."""
    now = datetime.datetime.now()
    current_hh_mm_ny = int(now.strftime("%H%M"))  # used in config
    trading_hours_cond = app_config.get('market').get('trading_hours')

    if eval(trading_hours_cond):
        return True
    else:
        return False

def can_do_trade_now(app_config, application_state):
    """Determine if trading can be done now based on config and state."""
    now = datetime.datetime.now()
    current_hh_mm_ny = int(now.strftime("%H%M"))  # used in config
    trading_hours_cond = app_config.get('market').get('trading_hours')
    market_is_open = application_state.get('market_session', {}).get('is_open', False)

    if eval(trading_hours_cond) and market_is_open:
        return True

    return False
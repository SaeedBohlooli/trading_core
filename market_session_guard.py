import asyncio
import logging
import datetime

from trading_utils import market_session
from trading_core import engine_cycle
import pytz
logger = logging.getLogger(__name__)


async def market_session_guard_loop(ib, application_state, runtime, interval_sec=60*5):
    """
    Background task:
    - refreshes market session ONLY when needed
    - runs independently from engine loop
    """
    while True:
        if engine_cycle.should_exit(application_state=application_state):
            logger.info("[market_session_guard_loop] Exiting as requested.")
            break
        try:
            if (application_state.get('is_busy_time', False)  == False and
                    runtime.is_due("market_session_refresh", interval_sec=60*60)): # each 1 hr
                await refresh_market_session(ib, application_state)

            await asyncio.sleep(interval_sec)
        except Exception as e:
            logger.exception(f"[market_session_guard_loop] refresh failed: {e}")
            await asyncio.sleep(interval_sec)


async def init_market_session_time(ib, app_config, application_state):
    application_state["market_session"] = await market_session.calculate_market_session(ib)
    logger.info(f"[init_market_session_time] Initialized market session: {application_state['market_session']}")


async def refresh_market_session_once_date_changed(ib, application_state):
    ms = application_state.get("market_session")
    today = datetime.date.today().isoformat()

    if not ms or ms["date"] != today:
        logger.info(f"[refresh_market_session_once_date_changed] Refreshing market session for date: {today}")
        application_state["market_session"] = await market_session.calculate_market_session(ib)

async def refresh_market_session(ib, application_state):
    today = datetime.date.today().isoformat()
    logger.info(f"[refresh_market_session_once_date_changed] Refreshing market session for date: {today}")
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
        logger.info(f"[is_market_open_based_on_ib] No market session info available, assuming market is closed.")
        return False

    start = ms.get("start")
    end = ms.get("end")
    if start is None and end is None:
        logger.info(f"[is_market_open_based_on_ib] No start/end info in market session: {ms}, assuming market is closed.")
        return False

    start = datetime.datetime.fromisoformat(ms["start"])
    end = datetime.datetime.fromisoformat(ms["end"])

    # example: now (timezone-aware, same offset as start/end)
    now = datetime.datetime.now(start.tzinfo)

    is_between = start <= now <= end

    return is_between



def is_trading_hours_based_on_config(app_config, application_state):
    """Determine if current time is within trading hours based on config."""
    if app_config.get('market_session_guard_skip', False) == True:
        return True
    now = datetime.datetime.now(pytz.timezone("America/New_York"))
    current_hh_mm_ny = int(now.strftime("%H%M"))  # used in config
    trading_hours_cond = app_config.get('market').get('trading_hours')

    if eval(trading_hours_cond):
        return True
    else:
        return False

def can_do_trade_now(app_config, application_state):
    """Determine if trading can be done now based on IB session  """
    if app_config.get('market_session_guard_skip', False) == True:
        return True

    market_is_open = application_state.get('market_session', {}).get('is_open', False)
    if market_is_open == False:
        # market is closed
        logger.info(f"[can_do_trade_now] Market is closed according to IB data. {application_state.get('market_session', {})}")
        return False

    now = datetime.datetime.now()
    current_hh_mm_ny = int(now.strftime("%H%M"))  # used in config

    market_start_hhmm = application_state.get('market_session', {}).get('start_hhmm',0)
    market_end_hhmm = application_state.get('market_session', {}).get('end_hhmm',0)

    if current_hh_mm_ny > market_end_hhmm or current_hh_mm_ny < market_start_hhmm:
        # now is before or after market hours
        logger.info(f"[can_do_trade_now] Current time {current_hh_mm_ny} is outside market hours {market_start_hhmm}-{market_end_hhmm}.")
        return False

    trading_hours_cond = app_config.get('market', {}).get('trading_hours', '1 == 1')

    if not eval(trading_hours_cond):
        logger.info(f"[can_do_trade_now] Current time {current_hh_mm_ny} does not satisfy trading hours condition: {trading_hours_cond}.")
        return False


    return True


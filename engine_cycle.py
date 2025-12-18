
import logging
logger = logging.getLogger(__name__)


async def shutdown(ib,ws):
    logger.warning("TradingEngine shutdown started")

    try:
        if ib:
            logger.info("Disconnecting IB...")
            ib.disconnect()
    except Exception as e:
        logger.error(f"Error disconnecting IB: {e}")

    try:
        logger.info("Stopping WebSocket server...")
        # await ws.stop()
    except Exception as e:
        logger.error(f"Error stopping WS: {e}")

    logger.warning("TradingEngine shutdown complete")


def should_exit(application_state):
    return application_state.get("engine", {}).get("exit_requested", False)
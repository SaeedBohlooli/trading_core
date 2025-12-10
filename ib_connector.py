import logging
from trading_utils import ib_utils_async
from trading_utils import ib_posttrade

logger = logging.getLogger(__name__)

class IBConnector:
    """
    Reusable connector for Interactive Brokers API.
    Handles:
        - async connection
        - registering events (commission, portfolio update)
        - reconnection logic if needed (optional future expansion)
    """

    @staticmethod
    async def connect(ip: str, port: int, client_id: int):
        logger.info(f"[IBConnector] Connecting to IB on {ip}:{port}, client_id={client_id}")

        ib = await ib_utils_async.create_ib_async(ip, port, client_id=client_id)

        # Register standard event handlers
        ib.commissionReportEvent += ib_posttrade.on_commission_report
        ib.updatePortfolioEvent += ib_posttrade.on_portfolio_update

        logger.info("[IBConnector] IB connection established.")
        return ib

    @staticmethod
    async def connect_from_config(app_config: dict):
        """
        Convenience method to connect using app_config.
        """
        ip = app_config["ip"]
        port = app_config["port"]
        client_id = app_config["client_id"]

        return await IBConnector.connect(ip, port, client_id)

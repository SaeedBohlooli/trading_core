# trading_core/logging_manager.py

import logging
import logging.handlers
import datetime
import os

class LoggingManager:

    @staticmethod
    def setup(log_dir: str, portfolio_id: str, logging_level: str, alias: str = None):
        os.makedirs(log_dir, exist_ok=True)
        alias = f'{alias}-' if alias else ''

        file = f'{portfolio_id}{alias}.log'
        log_file = f"{log_dir}/{file}"

        handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=200
        )

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        handler.setFormatter(formatter)

        logging.basicConfig(
            level=logging_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[handler, logging.StreamHandler()]
        )
        logger = logging.getLogger(__name__)
        logger.info(f"logger is created ....")
        return logger

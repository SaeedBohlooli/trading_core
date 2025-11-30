# trading_core/bootstrap.py

import os
import datetime
import logging
import logging.handlers
from trading_core.directory_manager import DirectoryManager
from trading_core.config_manager import ConfigManager
from trading_core.logging_manager import LoggingManager
from trading_core.file_manager import FileManager


class Boot:

    def __init__(self, portfolio_id: str):
        self.portfolio_id = portfolio_id

        # Directories
        self.dirs = DirectoryManager(portfolio_id, "live")

        self.app_config = ConfigManager.load(portfolio_id)

        # Config


        # Logging
        self.logger = LoggingManager.setup(
            log_dir=self.dirs.log_dir,
            portfolio_id=portfolio_id,
            # logging_level=self.app_config.get("logging_level", "INFO")
            logging_level=logging.INFO
        )
        FileManager.set_dirs(self.dirs)

        self.logger.info(f"App config loaded: {portfolio_id}, {self.app_config}")
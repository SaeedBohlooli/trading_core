# trading_core/bootstrap.py

import os
import datetime
import logging
import logging.handlers
from trading_core.directory_manager import DirectoryManager
from trading_core.config_manager import ConfigManager
from trading_core.logging_manager import LoggingManager
from trading_core.file_manager import FileManager
from trading_core.runtime_manager import RuntimeManager

class Boot:

    def __init__(self, portfolio_id: str):
        self.portfolio_id = portfolio_id
        self.dirs = DirectoryManager(portfolio_id, "live")
        self.app_config = ConfigManager.load(portfolio_id)
        self.application_state = {} # This will hold the state of the application

        # Logging
        self.logger = LoggingManager.setup(
            log_dir=self.dirs.log_dir,
            portfolio_id=portfolio_id,
            # logging_level=self.app_config.get("logging_level", "INFO")
            logging_level=logging.INFO
        )

        FileManager.set_dirs(self.dirs) # Set dirs for FileManager. it needs to know where to read/write files
        FileManager.set_boot(self) # Set boot for FileManager. it may need access to config or logger

        self.logger.info(f"App config loaded: {portfolio_id}, {self.app_config}")


        # Load previous state
        self.application_state = FileManager.load_named_json("application_state")
        self.application_state['portfolio_id'] = portfolio_id
        self.application_state['temp'] = 'Here is in the boot ...'

        self.runtime = RuntimeManager(self)


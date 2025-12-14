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

        # 1) Load config FIRST
        self.app_config = ConfigManager.load(portfolio_id)

        # 2) Then build dirs using config
        self.dirs = DirectoryManager(
            portfolio_id=portfolio_id,
            mode="live",
            app_config=self.app_config,
        )


        self.application_state = {} # This will hold the state of the application

        # Logging
        self.logger = LoggingManager.setup(
            log_dir=self.dirs.log_dir,
            portfolio_id=portfolio_id,
            # logging_level=self.app_config.get("logging_level", "INFO")
            logging_level=logging.INFO
        )

        FileManager.set_dirs(self.dirs)
        FileManager.set_files_config(self.app_config["files"])

        # The reason we are not creating obejt is
        # this FileManager.save_my_df(df) will be  boot.file_manager.save_my_df(df)

        self.logger.info(f"App config loaded: {portfolio_id}, {self.app_config}")


        # Load previous state
        self.application_state = FileManager.load_named_json("application_state")
        self.application_state['portfolio_id'] = portfolio_id
        self.application_state['temp'] = 'Here is in the boot ...'

        self.runtime = RuntimeManager(self)


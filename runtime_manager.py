import datetime
import logging
from trading_core.file_manager import FileManager
from trading_core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class RuntimeManager:
    """
    Handles:
      - config reload
      - saving application state
      - generating unique run numbers
      - attaching runtime metadata
    Reusable for ALL engines.
    """

    def __init__(self, boot):
        self.boot = boot
        self.portfolio_id = boot.portfolio_id
        self.app_config = boot.app_config
        self.application_state = boot.application_state

    # -------------------------------------------------------
    # CONFIG HANDLING
    # -------------------------------------------------------
    def reload_config(self):
        """Reload config for this portfolio_id."""
        self.app_config = ConfigManager.load(self.portfolio_id)
        self.boot.app_config = self.app_config
        logger.info(f"[RuntimeManager] Config reloaded for portfolio {self.portfolio_id}")
        return self.app_config


    # -------------------------------------------------------
    # RUN NUMBER / METADATA
    # -------------------------------------------------------
    def generate_unique_run_number(self, run_number: int) -> str:
        now = datetime.datetime.now()
        unique = f"{now:%Y%m%d-%H%M%S}-{run_number}"
        self.application_state['unique_run_number'] = unique
        return unique

    # -------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------
    @staticmethod
    def now_hhmm():
        return int(datetime.datetime.now().strftime("%H%M"))

    @staticmethod
    def now_hour():
        return int(datetime.datetime.now().strftime("%H"))

    @staticmethod
    def now_date():
        return datetime.datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def now_timestamp():
        return datetime.datetime.now().strftime("%Y-%m-%d__%H-%M")

    @staticmethod
    def now_Y_M_D_H_S():
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
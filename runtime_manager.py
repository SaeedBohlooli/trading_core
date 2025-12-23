import datetime
import logging
from trading_core.file_manager import FileManager
from trading_core.config_manager import ConfigManager
from trading_utils import config_utils
from trading_utils import ruamel_confg_util
from typing import Dict
import time
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
    _last_update_times: Dict[str, float] = {}
    DEFAULT_INTERVAL = 60.0  # seconds

    def __init__(self, boot):
        self.boot = boot
        self.portfolio_id = boot.portfolio_id
        self.app_config = boot.app_config
        self.application_state = boot.application_state

    @classmethod
    def is_due(
            cls,
            key: str,
            interval_sec: float | None = None,
            skip_first: bool = False,
    ) -> bool:
        now = time.time()
        interval_sec = interval_sec or cls.DEFAULT_INTERVAL

        last = cls._last_update_times.get(key)

        # -----------------------------
        # First time ever
        # -----------------------------
        if last is None:
            cls._last_update_times[key] = now
            if skip_first:
                logger.debug(f"[RuntimeManager] {key} first call skipped")
                return False
            return True

        # -----------------------------
        # Normal timing logic
        # -----------------------------
        if now - last >= interval_sec:
            logger.info(f"[RuntimeManager] {key} is due, now-last: {now - last}")
            cls._last_update_times[key] = now
            return True

        return False

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
    # RUNTIME CONTROL (EXIT, PAUSE, ETC.)
    # -------------------------------------------------------
    def reload_runtime_config(self):
        """
        Load runtime control flags (exit, pause, etc)
        and project them into application_state.
        """
        try:
            runtime_cfg = config_utils.load_runtime_config(self.application_state.get("portfolio_id"))
        except FileNotFoundError:
            runtime_cfg = {}

        if runtime_cfg.get('exit', False) == True:
            ruamel_confg_util.update_runtime_config_and_save(self.application_state.get('portfolio_id'),'exit', False)
            engine_state = self.application_state.setdefault("engine", {})

            engine_state["exit_requested"] = True
            engine_state["exit_requested_at"] = self.now_Y_M_D_H_S()

        return runtime_cfg

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

    @staticmethod
    def now_day_of_week():
        return datetime.datetime.now().strftime("%A")
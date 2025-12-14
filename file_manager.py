import os
import json
import inspect
import logging
import time
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class FileManager:
    """
    Simple, config-driven FileManager.

    Config format (ONLY supported format):

    files:
      screening_df: "{intermediate}/screening.csv"
      application_state: "{intermediate}/application_state.json"

    Directories come from DirectoryManager and are injected at boot.
    """

    # Injected once at bootstrap
    dirs = None
    files_config: Dict[str, str] = {}

    # throttling
    _last_df_save_times: dict[str, float] = {}

    # -------------------------------------------------
    # Bootstrap wiring
    # -------------------------------------------------

    @staticmethod
    def set_dirs(dirs_instance: Any) -> None:
        FileManager.dirs = dirs_instance

    @staticmethod
    def set_files_config(files_config: Dict[str, str]) -> None:
        FileManager.files_config = files_config

    # -------------------------------------------------
    # Internal helpers
    # -------------------------------------------------

    @staticmethod
    def _ensure_parent_dir(path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)

    @staticmethod
    def _detect_df_name(df: pd.DataFrame, explicit_name: Optional[str]) -> str:
        if explicit_name:
            return explicit_name

        frame = inspect.currentframe()
        caller = frame.f_back.f_back if frame else None

        if caller is None:
            raise ValueError("Cannot detect df_name. Pass it explicitly.")

        for name, value in caller.f_locals.items():
            if value is df:
                return name

        raise ValueError(
            "FileManager: Could not auto-detect df_name. "
            "Pass df_name explicitly."
        )

    @staticmethod
    def _resolve_path(name: str) -> str:
        if name not in FileManager.files_config:
            raise ValueError(f"File '{name}' not found in config files section.")

        template = FileManager.files_config[name]
        if not isinstance(template, str):
            raise TypeError(
                f"File '{name}' must be defined as a string path."
            )

        path = template
        for key, value in FileManager.dirs.__dict__.items():
            path = path.replace(f"{{{key}}}", value)

        return path

    # -------------------------------------------------
    # DataFrame API
    # -------------------------------------------------

    @staticmethod
    def save_my_df(
        df: pd.DataFrame,
        df_name: Optional[str] = None,
        min_rows: int = 0,
    ) -> str:
        df_name = FileManager._detect_df_name(df, df_name)
        path = FileManager._resolve_path(df_name)

        if min_rows and len(df) < min_rows:
            logger.info(
                f"Skipping save of '{df_name}' "
                f"(rows={len(df)} < min_rows={min_rows})"
            )
            return path

        FileManager._ensure_parent_dir(path)
        df.to_csv(path, index=False)
        return path

    @staticmethod
    def load_my_df(df_name: str) -> pd.DataFrame:
        path = FileManager._resolve_path(df_name)
        if not os.path.exists(path):
            return pd.DataFrame()
        return pd.read_csv(path)

    # -------------------------------------------------
    # JSON API
    # -------------------------------------------------

    @staticmethod
    def save_named_json(data: Any, name: str) -> str:
        path = FileManager._resolve_path(name)
        FileManager._ensure_parent_dir(path)

        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, default=str)

        os.replace(tmp, path)
        return path

    @staticmethod
    def load_named_json(name: str) -> Any:
        path = FileManager._resolve_path(name)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Malformed JSON in {path}: {e}")
            return {}

    # -------------------------------------------------
    # Throttled save
    # -------------------------------------------------

    @staticmethod
    def save_my_df_throttled(
        df: pd.DataFrame,
        df_name: Optional[str] = None,
        min_interval_sec: int = 300,
        key: Optional[str] = None,
    ) -> Optional[str]:

        df_name = FileManager._detect_df_name(df, df_name)
        throttle_key = key or df_name

        now = time.time()
        last = FileManager._last_df_save_times.get(throttle_key)

        if last and (now - last) < min_interval_sec:
            return None

        path = FileManager.save_my_df(df, df_name)
        FileManager._last_df_save_times[throttle_key] = now
        return path

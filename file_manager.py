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
      scaning_df: "{intermediate}/scaning.csv"
      application_state: "{intermediate}/application_state.json"

    Directories come from DirectoryManager and are injected at boot.
    """

    # Injected once at bootstrap
    dirs = None
    files_config: Dict[str, str] = {}

    # Shared throttling state
    _last_save_times: dict[str, float] = {}

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

        file_path_template = FileManager.files_config[name]  # e.g., "{results}/scaning.csv"
        if not isinstance(file_path_template, str):
            raise TypeError(
                f"File '{name}' must be defined as a string path."
            )

        file_path_template = file_path_template

        for key, value in FileManager.dirs.paths.__dict__.items(): # ex: ib: ../../portfolios/p106-1/ib
            logger.info(f"_resolve_path, Key: {key}, Value: {value}")  # Debugging line  # Key: results, Value: ../../portfolios/p106-1/results
            k = "{" + key + "}"   # e.g., {results}
            if k in file_path_template: # e.g.,{result}/scaning.csv
                file_path_template = file_path_template.replace(k, value) # e.g., ../../portfolios/p106-1/results/scaning.csv
        return file_path_template

    def _resolve_dir(dir: str) -> str:

        for key, value in FileManager.dirs.paths.__dict__.items(): # ex: ib: ../../portfolios/p106-1/ib
            logger.info(f"_resolve_path, Key: {key}, Value: {value}")  # Debugging line  # Key: results, Value: ../../portfolios/p106-1/results

            if key == dir: # e.g.,result
                return value
        return None

    # -------------------------------------------------
    # Unified DataFrame save (with optional throttling)
    # -------------------------------------------------

    @staticmethod
    def save_my_df(
        df: pd.DataFrame,
        df_name: Optional[str] = None,
        dir: Optional[str] = None,
        min_interval_sec: Optional[int] = None,
    ) -> Optional[str]:
        """
        Save DataFrame to CSV.

        - min_interval_sec=None → always save
        - min_interval_sec=N    → save at most once every N seconds
        """
        if df_name is None:
            df_name = FileManager._detect_df_name(df, df_name)

        if min_interval_sec is not None:
            now = time.time()
            last = FileManager._last_save_times.get(df_name)
            if last and (now - last) < min_interval_sec:
                return None

        if dir is None: # is not set, read it ....
            path = FileManager._resolve_path(df_name)
            FileManager._ensure_parent_dir(path)
        else:
            path = FileManager._resolve_dir(dir)


        df.to_csv(path, index=False)

        FileManager._last_save_times[df_name] = time.time()
        return path

    # -------------------------------------------------
    # Load DataFrame
    # -------------------------------------------------

    @staticmethod
    def load_my_df(df_name: str) -> pd.DataFrame:
        path = FileManager._resolve_path(df_name)
        if not os.path.exists(path):
            return pd.DataFrame()
        return pd.read_csv(path)

    # -------------------------------------------------
    # JSON save/load (with optional throttling)
    # -------------------------------------------------

    @staticmethod
    def save_named_json(
        data: Any,
        name: str,
        min_interval_sec: Optional[int] = None,
    ) -> Optional[str]:
        """
        Save JSON data to disk.

        - min_interval_sec=None → always save
        - min_interval_sec=N    → save at most once every N seconds
        """

        if min_interval_sec is not None:
            now = time.time()
            last = FileManager._last_save_times.get(name)
            if last and (now - last) < min_interval_sec:
                return None

        path = FileManager._resolve_path(name)
        FileManager._ensure_parent_dir(path)

        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, default=str)

        os.replace(tmp, path)

        FileManager._last_save_times[name] = time.time()
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

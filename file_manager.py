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
    Centralized file I/O manager.

    - Knows WHERE to save each named artifact (based on files config).
    - Uses DirectoryManager instance (set via set_dirs) to resolve base folders.
    - Saves DataFrames as CSV.
    - Saves JSON atomically.
    - Can auto-detect df_name from caller scope if not explicitly provided.
    """

    # Injected once at bootstrap
    dirs = None
    boot = None  # TODO need to be removed. . ...
    files_config: Dict[str, Dict[str, str]] = {}

    # internal store of last save timestamp per key (throttling)
    _last_df_save_times: dict[str, float] = {}

    # -------------------------------------------------
    # Bootstrap wiring
    # -------------------------------------------------

    @staticmethod
    def set_dirs(dirs_instance: Any) -> None:
        FileManager.dirs = dirs_instance

    @staticmethod
    def set_files_config(files_config: Dict[str, Dict[str, str]]) -> None:
        FileManager.files_config = files_config

    @staticmethod
    def set_boot(boot_instance):
        FileManager.boot = boot_instance

    # -------------------------------------------------
    # Internal helpers
    # -------------------------------------------------

    @staticmethod
    def _ensure_dir_for_path(path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)

    @staticmethod
    def _detect_df_name(df: pd.DataFrame, explicit_name: Optional[str]) -> str:
        if explicit_name:
            return explicit_name

        frame = inspect.currentframe()
        if frame is None:
            raise ValueError("Cannot inspect frame for df name detection.")

        save_frame = frame.f_back
        caller_frame = save_frame.f_back if save_frame else None

        if caller_frame is None:
            raise ValueError("Cannot detect caller frame for df name detection.")

        for var_name, var_value in caller_frame.f_locals.items():
            if var_value is df:
                return var_name

        raise ValueError(
            "FileManager: Could not auto-detect df_name. "
            "Pass df_name explicitly (recommended)."
        )

    @staticmethod
    def _get_folder_from_dirs(dir_key: str) -> str:
        if FileManager.dirs is None:
            raise RuntimeError(
                "FileManager.dirs is not set. Call FileManager.set_dirs(dirs) in bootstrap."
            )

        if not hasattr(FileManager.dirs, dir_key):
            raise AttributeError(
                f"DirectoryManager has no directory key '{dir_key}'."
            )

        return getattr(FileManager.dirs, dir_key)

    @staticmethod
    def _get_file_rule(name: str) -> Dict[str, str]:
        if name not in FileManager.files_config:
            raise ValueError(
                f"FileManager: '{name}' not found in config files section."
            )
        return FileManager.files_config[name]

    # -------------------------------------------------
    # DataFrame save/load API
    # -------------------------------------------------

    @staticmethod
    def save_my_df(
        df: pd.DataFrame,
        df_name: Optional[str] = None,
        file_name: Optional[str] = None,
        dir: Optional[str] = None,
    ) -> str:
        logger.info(
            f"FileManager.save_my_df called "
            f"(df_name={df_name}, file_name={file_name}, dir={dir})"
        )

        df_name = FileManager._detect_df_name(df, df_name)

        if df_name in FileManager.files_config:
            rule = FileManager._get_file_rule(df_name)
            folder_key = rule["dir"]
            file_name = rule["filename"]
        elif dir is not None:
            folder_key = dir
            file_name = file_name or f"{df_name}.csv"
        else:
            raise ValueError(
                f"FileManager.save_my_df: df_name '{df_name}' not found in config files "
                f"and no dir override provided."
            )

        folder_path = FileManager._get_folder_from_dirs(folder_key)
        full_path = os.path.join(folder_path, file_name)

        FileManager._ensure_dir_for_path(full_path)
        df.to_csv(full_path, index=False)

        return full_path

    @staticmethod
    def load_my_df(df_name: str) -> pd.DataFrame:
        rule = FileManager._get_file_rule(df_name)

        folder_path = FileManager._get_folder_from_dirs(rule["dir"])
        full_path = os.path.join(folder_path, rule["filename"])

        if not os.path.exists(full_path):
            return pd.DataFrame()

        return pd.read_csv(full_path)

    # -------------------------------------------------
    # JSON save/load API
    # -------------------------------------------------

    @staticmethod
    def save_named_json(data: Any, name: str) -> str:
        rule = FileManager._get_file_rule(name)

        folder_path = FileManager._get_folder_from_dirs(rule["dir"])
        full_path = os.path.join(folder_path, rule["filename"])

        FileManager._ensure_dir_for_path(full_path)

        logger.info(f"Saving JSON data to {full_path}")

        tmp_path = full_path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=4, default=str)

        os.replace(tmp_path, full_path)
        return full_path

    @staticmethod
    def load_named_json(name: str) -> Any:
        rule = FileManager._get_file_rule(name)

        folder_path = FileManager._get_folder_from_dirs(rule["dir"])
        full_path = os.path.join(folder_path, rule["filename"])

        if not os.path.exists(full_path):
            return {}

        try:
            with open(full_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Malformed JSON in {full_path}: {e}")
            return {}

    # -------------------------------------------------
    # Throttled save
    # -------------------------------------------------

    @staticmethod
    def save_my_df_throttled(
        df: pd.DataFrame,
        df_name: Optional[str] = None,
        file_name: Optional[str] = None,
        dir: Optional[str] = None,
        min_interval_sec: int = 300,
        key: Optional[str] = None,
    ) -> Optional[str]:

        df_name = FileManager._detect_df_name(df, df_name)
        throttle_key = key or df_name

        now = time.time()
        last = FileManager._last_df_save_times.get(throttle_key)

        if last and (now - last) < min_interval_sec:
            return None

        full_path = FileManager.save_my_df(
            df=df,
            df_name=df_name,
            file_name=file_name,
            dir=dir,
        )

        FileManager._last_df_save_times[throttle_key] = now
        return full_path

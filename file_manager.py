import os
import json
import inspect
from typing import Any, Dict, Optional
import logging
import pandas as pd
logger = logging.getLogger(__name__)
import time

class FileManager:
    """
    Centralized file I/O manager.

    - Knows WHERE to save each named DataFrame (based on DF_SAVE_MAP).
    - Uses DirectoryManager instance (set via set_dirs) to resolve base folders.
    - Saves DataFrames as CSV (as requested).
    - Can auto-detect df_name from the caller's variable name if not provided.
    """

    # Will hold an instance of DirectoryManager (set once in bootstrap)
    dirs = None
    boot = None

    # internal store of last save timestamp per key
    _last_df_save_times: dict[str, float] = {}

    # Map: df_name -> { folder_attr (DirectoryManager attribute), filename }
    DF_SAVE_MAP: Dict[str, Dict[str, str]] = {
        "stop_loss_df": {
            "folder": "results_dir",          # -> dirs.results_dir
            "filename": "stop_loss.csv",
        },
        "live_portfolio_df": {
            "folder": "results_dir",          # -> dirs.results_dir
            "filename": "live_portfolio.csv",
        },
        "screening_df": {
            "folder": "intermediate_dir",     # -> dirs.intermediate_dir
            "filename": "screening.csv",
        },
        "open_trades_df": {
            "folder": "intermediate_dir",
            "filename": "open_trades.csv",
        },
        # Add more here as needed...
    }

    # Optional: mappings for JSON-based data (application_state, logs, etc.)
    JSON_SAVE_MAP: Dict[str, Dict[str, str]] = {
        "application_state": {
            "folder": "intermediate_dir",
            "filename": "application_state.json",
        },
        "stop_loss_events": {
            "folder": "results_dir",
            "filename": "stop_loss_events.json",
        },
        # Add more named JSON artifacts here...
    }

    # ---------- Core setup ----------

    @staticmethod
    def set_dirs(dirs_instance: Any) -> None:
        """
        Set the DirectoryManager instance once (usually in bootstrap).

        Example in bootstrap:
            from trading_core.file_manager import FileManager
            FileManager.set_dirs(boot.dirs)
        """
        FileManager.dirs = dirs_instance

    @staticmethod
    def set_boot(boot_instance):
        FileManager.boot = boot_instance

    # ---------- Internal helpers ----------

    @staticmethod
    def _ensure_dir_for_path(path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)

    @staticmethod
    def _detect_df_name(df: pd.DataFrame, explicit_name: Optional[str]) -> str:
        """
        If explicit_name is provided, use it.
        Otherwise, try to infer the variable name of `df` in the caller's locals.
        """
        # TODO just for testing
        if explicit_name:
            return explicit_name

        # current frame -> _detect_df_name
        # f_back -> save_my_df
        # f_back.f_back -> actual caller of save_my_df
        frame = inspect.currentframe()
        if frame is None:
            raise ValueError("Cannot inspect frame for df name detection.")

        save_my_df_frame = frame.f_back
        if save_my_df_frame is None:
            raise ValueError("Cannot get caller frame for df name detection.")

        caller_frame = save_my_df_frame.f_back
        if caller_frame is None:
            raise ValueError("Cannot get caller frame for df name detection.")

        for var_name, var_value in caller_frame.f_locals.items():
            if var_value is df:
                logger.info(f"@@@ Auto-detected df_name: {var_name}")
                return var_name

        raise ValueError(
            "FileManager: Could not auto-detect df_name. "
            "Pass df_name explicitly, e.g. save_my_df(df, 'stop_loss_df')."
        )

    @staticmethod
    def _get_folder_from_dirs(folder_attr: str) -> str:
        """
        folder_attr is something like 'results_dir' or 'intermediate_dir'.
        We resolve it to the actual path via DirectoryManager instance.
        """
        if FileManager.dirs is None:
            raise RuntimeError(
                "FileManager.dirs is not set. Call FileManager.set_dirs(dirs) in bootstrap."
            )

        if not hasattr(FileManager.dirs, folder_attr):
            raise AttributeError(
                f"DirectoryManager has no attribute '{folder_attr}'. "
                f"Check DF_SAVE_MAP / JSON_SAVE_MAP or DirectoryManager."
            )

        return getattr(FileManager.dirs, folder_attr)

    # ---------- DataFrame save/load API ----------

    @staticmethod
    def register_df_mapping(df_name: str, folder_attr: str, filename: str) -> None:
        """
        Dynamically register or override a DataFrame mapping.
        Example:
            FileManager.register_df_mapping("diagnostics_df", "intermediate_dir", "diagnostics.csv")
        """
        FileManager.DF_SAVE_MAP[df_name] = {
            "folder": folder_attr,
            "filename": filename,
        }

    @staticmethod
    def save_my_df(df: pd.DataFrame, df_name: Optional[str] = None, file_name: Optional[str] = None, dir: Optional[str] = None) -> str:
        """
        Save a DataFrame to CSV using DF_SAVE_MAP rules.

        You can call either:
            FileManager.save_my_df(stop_loss_df, "stop_loss_df")
        or (auto-detect variable name):
            FileManager.save_my_df(stop_loss_df)

        Returns:
            Full path of the written file.
        """
        # Detect df_name if not provided
        logger.info(f"FileManager.save_my_df called for df_name: {df_name}, file_name: {file_name}, dir: {dir}")
        df_name = FileManager._detect_df_name(df, df_name)

        if df_name in FileManager.DF_SAVE_MAP:  # df_name is not here and also dir is not provided
            rule = FileManager.DF_SAVE_MAP[df_name]
            folder_attr = rule["folder"]
            file_name = rule["filename"]
        elif dir is not None:  # dir is provided, use it directly
            file_name = file_name or f"{df_name}.csv"
            folder_attr = dir
        else:
            raise ValueError(
                f"FileManager.save_my_df: df_name '{df_name}' not found in DF_SAVE_MAP. "
                f"Please provide df_name explicitly or register it via register_df_mapping.")

        folder_path = FileManager._get_folder_from_dirs(folder_attr)
        full_path = os.path.join(folder_path, file_name)

        FileManager._ensure_dir_for_path(full_path)
        df.to_csv(full_path, index=False)

        return full_path

    @staticmethod
    def load_my_df(df_name: str) -> pd.DataFrame:
        """
        Load a DataFrame from CSV using DF_SAVE_MAP rules.
        Returns an empty DataFrame if the file does not exist.
        """
        if df_name not in FileManager.DF_SAVE_MAP:
            raise ValueError(
                f"FileManager.load_my_df: df_name '{df_name}' not found in DF_SAVE_MAP."
            )

        rule = FileManager.DF_SAVE_MAP[df_name]
        folder_attr = rule["folder"]
        filename = rule["filename"]

        folder_path = FileManager._get_folder_from_dirs(folder_attr)
        full_path = os.path.join(folder_path, filename)

        if not os.path.exists(full_path):
            # No file yet → return empty DF
            return pd.DataFrame()

        return pd.read_csv(full_path)

    # ---------- JSON save/load API ----------

    @staticmethod
    def save_named_json(data: Any, name: str) -> str:
        """
        Save a JSON-serializable object using JSON_SAVE_MAP.

        Example:
            FileManager.save_named_json(application_state, "application_state")
        """
        if name not in FileManager.JSON_SAVE_MAP:
            raise ValueError(
                f"FileManager.save_named_json: name '{name}' not found in JSON_SAVE_MAP."
            )

        rule = FileManager.JSON_SAVE_MAP[name]
        folder_attr = rule["folder"]
        filename = rule["filename"]

        folder_path = FileManager._get_folder_from_dirs(folder_attr)
        full_path = os.path.join(folder_path, filename)

        FileManager._ensure_dir_for_path(full_path)

        logger.info(f"Saving JSON data to {full_path}")

        tmp_path = full_path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=4, default=str)
        os.replace(tmp_path, full_path)

        return full_path

    @staticmethod
    def load_named_json(name: str) -> Any:
        """
        Load JSON data using JSON_SAVE_MAP.
        Returns {} if the file does not exist.
        """
        if name not in FileManager.JSON_SAVE_MAP:
            raise ValueError(
                f"FileManager.load_named_json: name '{name}' not found in JSON_SAVE_MAP."
            )

        rule = FileManager.JSON_SAVE_MAP[name]
        folder_attr = rule["folder"]
        filename = rule["filename"]

        folder_path = FileManager._get_folder_from_dirs(folder_attr)
        full_path = os.path.join(folder_path, filename)

        if not os.path.exists(full_path):
            return {}

        with open(full_path, "r") as f:
            return json.load(f)

    @staticmethod
    def save_my_df_throttled(
            df: pd.DataFrame,
            df_name: Optional[str] = None,
            file_name: Optional[str] = None,
            dir: Optional[str] = None,
            min_interval_sec: int = 300,
            key: Optional[str] = None,
    ) -> Optional[str]:

        logger.info(f"FileManager.save_my_df_throttled called for df_name: {df_name}, key: {key}")
        # 2) Throttle logic
        df_name = FileManager._detect_df_name(df, df_name)
        throttle_key = key or df_name

        now = time.time()
        last = FileManager._last_df_save_times.get(throttle_key)

        if last and (now - last) < min_interval_sec:
            return None

        # 3) Actually save
        full_path = FileManager.save_my_df(
            df=df,
            df_name=df_name,
            file_name=file_name,
            dir=dir,
        )

        FileManager._last_df_save_times[throttle_key] = now
        return full_path
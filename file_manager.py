import os
import json
import inspect
import logging
import time
from typing import Any, Dict, Optional
from trading_utils import df_utils
import pandas as pd

logger = logging.getLogger(__name__)


class FileManager:
    """
    Simple, config-driven FileManager.

    Config format (ONLY supported format):

    files:
      scanning_df: "{intermediate}/scanning.csv"
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
            file_path_template = '{default}/' + name + '.csv'  # e.g., "{default}/scanning.csv"
        else:
            file_path_template = FileManager.files_config[name]  # e.g., "{results}/scanning.csv"
        if not isinstance(file_path_template, str):
            raise TypeError(
                f"File '{name}' must be defined as a string path."
            )

        file_path_template = file_path_template

        for key, value in FileManager.dirs.paths.__dict__.items(): # ex: ib: ../../portfolios/p106-1/ib
            logger.debug(f"_resolve_path, Key: {key}, Value: {value}")  # Debugging line  # Key: results, Value: ../../portfolios/p106-1/results
            k = "{" + key + "}"   # e.g., {results}
            if k in file_path_template: # e.g.,{result}/scanning.csv
                file_path_template = file_path_template.replace(k, value) # e.g., ../../portfolios/p106-1/results/scanning.csv
        return file_path_template

    def _resolve_dir(dir: str) -> str:

        for key, value in FileManager.dirs.paths.__dict__.items(): # ex: ib: ../../portfolios/p106-1/ib
            logger.debug(f"_resolve_path, Key: {key}, Value: {value}")  # Debugging line  # Key: results, Value: ../../portfolios/p106-1/results

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
        file_name: Optional[str] = None, # dir and file_name are used together
        dir: Optional[str] = None, # dir and file_name are used together dir goes back to FileManager.dirs
        min_interval_sec: Optional[int] = None,
        mode: str = "w",
        save_tabular: bool = False,
        drop_duplicates: bool = False,
        unique_subset: Optional[list] = None,
        keep: str = "last", # for drop_duplicates
    ) -> Optional[str]:
        """
        Save DataFrame to CSV.

        - min_interval_sec=None → always save
        - min_interval_sec=N    → save at most once every N seconds
        """
        if type(df) is not pd.DataFrame:
            try:
                logger.info(f"[save_my_df] We are converting {df_name} to pd.DataFrame, type(df): {type(df)}")
                if isinstance(df, dict):
                    # one logical row
                    df =  pd.DataFrame([df])

                if isinstance(df, list):
                    # list of rows (dicts)
                    df =  pd.DataFrame(df)
            except Exception as e:
                logger.error(f"[save_my_df] Failed to convert {df_name} to pd.DataFrame: {e}")
                return None

        if df is None :
            logger.warning(f"[save_my_df] Empty df {df_name}, nothing to save.")
            return None
        if df.empty and mode=="a" :
            logger.warning(f"[save_my_df] Empty df {df_name}, nothing to save.")
            return None

        if min_interval_sec is not None:
            key = df_name if df_name is not None else file_name
            now = time.time()
            last = FileManager._last_save_times.get(key)
            if last and (now - last) < min_interval_sec:
                return None

        if df_name is None:
            df_name = FileManager._detect_df_name(df, df_name)


        if dir is None: # is not set, read it ....
            path = FileManager._resolve_path(df_name)
            FileManager._ensure_parent_dir(path)
        else:
            dir_resolved = FileManager._resolve_dir(dir)
            path = os.path.join(dir_resolved, file_name)

        logger.info(f"[save_my_df], Saving DataFrame '{df_name}' to path: {path}")
        df_utils.save_df_to_csv(
            df=df,
            file_path=path,
            mode=mode ,
            drop_dupplicates=drop_duplicates,
            unique_columns=unique_subset if unique_subset else [],
            tabular=save_tabular,
            keep=keep
        )
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
        name: str = None,
        dir: Optional[str] = None, # if you set dir, then file_name must be set too
        file_name: Optional[str] = None,
        min_interval_sec: Optional[int] = None,
    ) -> Optional[str]:
        """
        Save JSON data to disk.

        - min_interval_sec=None → always save
        - min_interval_sec=N    → save at most once every N seconds
        """

        if min_interval_sec is not None:
            key = name if name is not None else file_name
            now = time.time()
            last = FileManager._last_save_times.get(key)
            if last and (now - last) < min_interval_sec:
                return None

        if dir is None: # is not set, read it ....
            path = FileManager._resolve_path(name)
            FileManager._ensure_parent_dir(path)
        else:
            dir_resolved = FileManager._resolve_dir(dir)
            path = os.path.join(dir_resolved, file_name )

        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, default=str)

        os.replace(tmp, path)
        logger.info(f"[save_named_json], Saving JSON '{name}' to path: {path}")

        FileManager._last_save_times[name] = time.time()
        return path

    @staticmethod
    def load_named_json(name: str= None,
                        file_name: Optional[str] = None,
                        dir: Optional[str] = None,
                        full_path: Optional[str] = None
                        ) -> Any:
        if full_path is not None:
            # This is full explicit path
            path = full_path
        elif dir is not None and file_name is not None:
            dir_resolved = FileManager._resolve_dir(dir)
            path = os.path.join(dir_resolved, file_name )
        else:
            path = FileManager._resolve_path(name)

        if not os.path.exists(path):
            return {}

        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[save_named_json] Malformed JSON in {path}: {e}")
            return {}

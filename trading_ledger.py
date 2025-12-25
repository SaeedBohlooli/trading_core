import pandas as pd
from typing import Dict, List, Any, Iterable
from collections import defaultdict


class TradingLedger:
    """
    TradingLedger – Version 2.1

    Central, process-wide ledger for trading lifecycle data.

    Features:
    - Global (class-level) storage
    - Lazy creation of dataframes and lists
    - add_to_dataframe supports dict or list[dict]
    - Optional per-call buffering
    - Explicit buffer flushing
    - Backward compatible with Version 1
    """

    # =====================================================
    # CLASS-LEVEL STORAGE
    # =====================================================
    dataframes: Dict[str, pd.DataFrame] = {}
    lists: Dict[str, List[Any]] = {}

    # Internal buffers for dataframe writes
    _buffers: Dict[str, List[dict]] = defaultdict(list)

    # =====================================================
    # DATAFRAME API
    # =====================================================

    @classmethod
    def add_to_dataframe(
        cls,
        dataframe_name: str,
        rows: dict | List[dict],
        *,
        extra: dict | None = None,
        ensure_columns: bool = True,
        buffer: bool = False,
    ) -> None:
        """
        Add one or many rows to a dataframe.

        rows:
            - dict        -> single row
            - list[dict]  -> multiple rows
        """

        # ----------------------------
        # Normalize input to list[dict]
        # ----------------------------
        if isinstance(rows, dict):
            rows_iter: Iterable[dict] = [rows]
        elif isinstance(rows, list):
            rows_iter = rows
        else:
            raise TypeError(
                f"rows must be dict or list[dict], got {type(rows)}"
            )

        # ----------------------------
        # Prepare payloads (safe copy)
        # ----------------------------
        payloads: List[dict] = []
        for row in rows_iter:
            payload = dict(row)
            if extra:
                payload.update(extra)
            payloads.append(payload)

        # ----------------------------
        # BUFFER MODE
        # ----------------------------
        if buffer:
            cls._buffers[dataframe_name].extend(payloads)
            return

        # ----------------------------
        # DIRECT MODE
        # ----------------------------
        cls._append_many(
            dataframe_name,
            payloads,
            ensure_columns=ensure_columns,
        )

    # =====================================================
    # INTERNAL APPEND HELPERS
    # =====================================================

    @classmethod
    def _append_many(
        cls,
        dataframe_name: str,
        payloads: List[dict],
        *,
        ensure_columns: bool,
    ) -> None:
        new_df = pd.DataFrame(payloads)

        # Create dataframe if missing
        if dataframe_name not in cls.dataframes:
            cls.dataframes[dataframe_name] = new_df
            return

        df = cls.dataframes[dataframe_name]

        if ensure_columns:
            # Align columns safely
            for col in df.columns:
                if col not in new_df.columns:
                    new_df[col] = pd.NA

            for col in new_df.columns:
                if col not in df.columns:
                    df[col] = pd.NA

            new_df = new_df[df.columns]

        cls.dataframes[dataframe_name] = pd.concat(
            [df, new_df],
            ignore_index=True,
        )

    # =====================================================
    # BUFFER FLUSHING
    # =====================================================

    @classmethod
    def flush_buffers(cls) -> None:
        """
        Flush ALL buffered dataframe rows.
        Call explicitly (e.g. once per engine loop).
        """
        for dataframe_name, rows in cls._buffers.items():
            if not rows:
                continue

            cls._append_many(
                dataframe_name,
                rows,
                ensure_columns=True,
            )
            rows.clear()

    @classmethod
    def flush_dataframe_buffer(cls, dataframe_name: str) -> None:
        """
        Flush buffer for a single dataframe.
        """
        rows = cls._buffers.get(dataframe_name)
        if not rows:
            return

        cls._append_many(
            dataframe_name,
            rows,
            ensure_columns=True,
        )
        rows.clear()

    # =====================================================
    # DATAFRAME READ / HOUSEKEEPING
    # =====================================================

    @classmethod
    def get_dataframe(cls, dataframe_name: str) -> pd.DataFrame:
        return cls.dataframes.get(dataframe_name, pd.DataFrame())

    @classmethod
    def has_dataframe(cls, dataframe_name: str) -> bool:
        return dataframe_name in cls.dataframes

    @classmethod
    def clear_dataframe(cls, dataframe_name: str) -> None:
        cls.dataframes.pop(dataframe_name, None)
        cls._buffers.pop(dataframe_name, None)

    # =====================================================
    # LIST API
    # =====================================================

    @classmethod
    def add_to_list(
        cls,
        list_name: str,
        item: Any | List[Any],
    ) -> None:
        """
        Append one or many items to a named list.
        """
        if list_name not in cls.lists:
            cls.lists[list_name] = []

        if isinstance(item, list):
            cls.lists[list_name].extend(item)
        else:
            cls.lists[list_name].append(item)

    @classmethod
    def get_list(cls, list_name: str) -> List[Any]:
        return cls.lists.get(list_name, [])

    @classmethod
    def has_list(cls, list_name: str) -> bool:
        return list_name in cls.lists

    @classmethod
    def clear_list(cls, list_name: str) -> None:
        cls.lists.pop(list_name, None)

    # =====================================================
    # GLOBAL HOUSEKEEPING
    # =====================================================

    @classmethod
    def clear_all(cls) -> None:
        cls.dataframes.clear()
        cls.lists.clear()
        cls._buffers.clear()

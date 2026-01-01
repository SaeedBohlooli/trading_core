import pandas as pd
from typing import Dict, List, Any, Iterable
from collections import defaultdict


class TradingLedger:
    """
    TradingLedger – Version 1.4

    Central, process-wide ledger for trading lifecycle data.

    Responsibilities:
    - Own in-memory dataframes and lists
    - Support direct + buffered writes
    - Enforce dataframe column order (schema)
    - Accept externally-loaded dataframes (from FileManager, DB, etc.)

    Non-responsibilities:
    - File I/O
    - Persistence
    """

    # =====================================================
    # CLASS-LEVEL STORAGE
    # =====================================================
    dataframes: Dict[str, pd.DataFrame] = {}
    lists: Dict[str, List[Any]] = {}

    # Internal buffers for dataframe writes
    _buffers: Dict[str, List[dict]] = defaultdict(list)

    # Optional registered schemas (column order)
    _schemas: Dict[str, List[str]] = {}

    # =====================================================
    # DATAFRAME WRITE API
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
        drop_duplicates: bool = False,
        subset_for_duplicate: list[str] | None = None,
    ) -> None:
        """
        Add one or many rows to a dataframe.

        rows:
            - dict        -> single row
            - list[dict]  -> multiple rows
        """

        # Normalize input
        if isinstance(rows, dict):
            rows_iter: Iterable[dict] = [rows]
        elif isinstance(rows, list):
            rows_iter = rows
        else:
            raise TypeError(
                f"rows must be dict or list[dict], got {type(rows)}"
            )

        # Prepare payloads
        payloads: List[dict] = []
        for row in rows_iter:
            payload = dict(row)  # copy to avoid side effects
            if extra:
                payload.update(extra)
            payloads.append(payload)

        # BUFFER MODE
        if buffer:
            cls._buffers[dataframe_name].extend(payloads)
            return

        # DIRECT MODE
        cls._append_many(
            dataframe_name,
            payloads,
            ensure_columns=ensure_columns,
        )
        if drop_duplicates:
            cls.dataframes[dataframe_name] = cls.dataframes[dataframe_name].drop_duplicates(keep='last', subset=subset_for_duplicate if subset_for_duplicate else None)

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
            cls._apply_schema_if_any(dataframe_name)
            return

        df = cls.dataframes[dataframe_name]

        if ensure_columns:
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

        cls._apply_schema_if_any(dataframe_name)

    # =====================================================
    # BUFFER FLUSHING
    # =====================================================

    @classmethod
    def flush_buffers(cls) -> None:
        """
        Flush ALL buffered dataframe rows.
        Call explicitly (e.g., once per engine loop).
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
    # DATAFRAME SCHEMA (v1.3)
    # =====================================================

    @classmethod
    def set_dataframe_columns(
        cls,
        dataframe_name: str,
        columns: List[str],
    ) -> None:
        """
        Register and enforce column order for a dataframe.
        """
        cls._schemas[dataframe_name] = list(columns)

        if dataframe_name not in cls.dataframes:
            cls.dataframes[dataframe_name] = pd.DataFrame(columns=columns)
            return

        cls._apply_schema_if_any(dataframe_name)

    @classmethod
    def _apply_schema_if_any(cls, dataframe_name: str) -> None:
        if dataframe_name not in cls._schemas:
            return

        df = cls.dataframes[dataframe_name]
        schema_cols = cls._schemas[dataframe_name]

        # Add missing columns
        for col in schema_cols:
            if col not in df.columns:
                df[col] = pd.NA

        # Preserve extra columns
        extra_cols = [c for c in df.columns if c not in schema_cols]

        cls.dataframes[dataframe_name] = df[schema_cols + extra_cols]

    # =====================================================
    # DATAFRAME LOAD / REPLACE (v1.4)
    # =====================================================

    @classmethod
    def set_dataframe(
        cls,
        dataframe_name: str,
        df: pd.DataFrame,
        *,
        copy: bool = True,
        apply_schema: bool = False,
    ) -> None:
        """
        Set / replace a dataframe in the ledger.

        Intended for loading data from previous runs
        (read externally via FileManager).
        """
        if copy:
            df = df.copy()

        cls.dataframes[dataframe_name] = df

        if apply_schema:
            cls._apply_schema_if_any(dataframe_name)

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
        cls._schemas.pop(dataframe_name, None)

    # =====================================================
    # LIST API
    # =====================================================

    @classmethod
    def add_to_list(
        cls,
        list_name: str,
        item: Any | List[Any],
    ) -> None:
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
        cls._schemas.clear()


    # =====================================================
    # STATS / INTROSPECTION API (v1.5)
    # =====================================================

    @classmethod
    def get_stats(cls) -> dict:
        """
        Return global ledger statistics.
        """
        return {
            "dataframes": {
                "count": len(cls.dataframes),
                "names": list(cls.dataframes.keys()),
            },
            "lists": {
                "count": len(cls.lists),
                "names": list(cls.lists.keys()),
            },
            "buffers": {
                "dataframes_with_buffers": [
                    name for name, rows in cls._buffers.items() if rows
                ],
                "total_buffered_rows": sum(
                    len(rows) for rows in cls._buffers.values()
                ),
            },
        }

    @classmethod
    def get_dataframe_stats(cls, dataframe_name: str) -> dict:
        """
        Return statistics for a specific dataframe.
        """
        df = cls.dataframes.get(dataframe_name)
        buffered_rows = len(cls._buffers.get(dataframe_name, []))

        if df is None:
            return {
                "exists": False,
                "name": dataframe_name,
            }

        return {
            "exists": True,
            "name": dataframe_name,
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "buffered_rows": buffered_rows,
            "has_schema": dataframe_name in cls._schemas,
            "schema_columns": cls._schemas.get(dataframe_name),
            "memory_bytes": int(df.memory_usage(deep=True).sum()),
        }

    @classmethod
    def get_list_stats(cls, list_name: str) -> dict:
        """
        Return statistics for a specific list.
        """
        lst = cls.lists.get(list_name)

        if lst is None:
            return {
                "exists": False,
                "name": list_name,
            }

        return {
            "exists": True,
            "name": list_name,
            "items": len(lst),
        }

    @classmethod
    def get_all_dataframe_stats(cls) -> List[dict]:
        """
        Return stats for ALL registered dataframes.
        """
        return [
            cls.get_dataframe_stats(name)
            for name in sorted(cls.dataframes.keys())
        ]

    @classmethod
    def get_all_list_stats(cls) -> List[dict]:
        """
        Return stats for ALL registered lists.
        """
        return [
            cls.get_list_stats(name)
            for name in sorted(cls.lists.keys())
        ]

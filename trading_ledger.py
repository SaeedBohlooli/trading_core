import pandas as pd
from typing import Dict, List, Any


class TradingLedger:
    """
    Central, process-wide ledger for trading lifecycle data.

    - DataFrames: tabular, analytical data
    - Lists: ordered event streams, refs, counters, logs

    Callable from anywhere without passing instances.
    """

    # =====================================================
    # CLASS-LEVEL STORAGE
    # =====================================================
    dataframes: Dict[str, pd.DataFrame] = {}
    lists: Dict[str, List[Any]] = {}

    # =====================================================
    # DATAFRAME API
    # =====================================================

    @classmethod
    def add_to_dataframe(
        cls,
        dataframe_name: str,
        row: dict,
        *,
        extra: dict | None = None,
        ensure_columns: bool = True,
    ) -> None:
        payload = dict(row)
        if extra:
            payload.update(extra)

        new_row_df = pd.DataFrame([payload])

        # Create dataframe if missing
        if dataframe_name not in cls.dataframes:
            cls.dataframes[dataframe_name] = new_row_df
            return

        df = cls.dataframes[dataframe_name]

        if ensure_columns:
            for col in df.columns:
                if col not in new_row_df.columns:
                    new_row_df[col] = pd.NA

            for col in new_row_df.columns:
                if col not in df.columns:
                    df[col] = pd.NA

            new_row_df = new_row_df[df.columns]

        cls.dataframes[dataframe_name] = pd.concat(
            [df, new_row_df],
            ignore_index=True,
        )

    @classmethod
    def get_dataframe(cls, dataframe_name: str) -> pd.DataFrame:
        return cls.dataframes.get(dataframe_name, pd.DataFrame())

    @classmethod
    def has_dataframe(cls, dataframe_name: str) -> bool:
        return dataframe_name in cls.dataframes

    # =====================================================
    # LIST API
    # =====================================================

    @classmethod
    def add_to_list(
        cls,
        list_name: str,
        item: Any,
    ) -> None:
        """
        Append an item to a named list.
        """
        if list_name not in cls.lists:
            cls.lists[list_name] = []

        cls.lists[list_name].append(item)

    @classmethod
    def extend_list(
        cls,
        list_name: str,
        items: List[Any],
    ) -> None:
        if list_name not in cls.lists:
            cls.lists[list_name] = []

        cls.lists[list_name].extend(items)

    @classmethod
    def get_list(cls, list_name: str) -> List[Any]:
        return cls.lists.get(list_name, [])

    @classmethod
    def has_list(cls, list_name: str) -> bool:
        return list_name in cls.lists

    # =====================================================
    # OPTIONAL HOUSEKEEPING
    # =====================================================

    @classmethod
    def clear_dataframe(cls, dataframe_name: str) -> None:
        cls.dataframes.pop(dataframe_name, None)

    @classmethod
    def clear_list(cls, list_name: str) -> None:
        cls.lists.pop(list_name, None)

    @classmethod
    def clear_all(cls) -> None:
        cls.dataframes.clear()
        cls.lists.clear()

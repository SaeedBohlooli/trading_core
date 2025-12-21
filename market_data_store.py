# trading_core/market_data_store.py

class MarketDataStore:
    """
    Server-side cache for heavy market data (dfs, indicators).
    Never streamed to UI.
    """
    def __init__(self):
        self.dfs_map = {}
        self.dfs_w_indicators = {}  # { symbol: {'1d': df, '1h': df, ...} }
        self.dfs_with_indicators = {}
        self.last_updated = None

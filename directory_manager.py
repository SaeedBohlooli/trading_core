# trading_core/directory_manager.py

import os
import datetime

class DirectoryPaths:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class DirectoryManager:

    def __init__(self, portfolio_id: str, mode: str):
        self.portfolio_id = portfolio_id
        self.mode = mode

        alias = '' if mode == 'live' else '-backtest'

        now = datetime.datetime.now().strftime("%Y-%m-%d")

        self.portfolio_dir = f'../../portfolios/{portfolio_id}/results-{alias}'
        self.ib_dir = f'../../portfolios/{portfolio_id}/ib{alias}'
        self.reports_dir = f'../../portfolios/{portfolio_id}/reports{alias}'
        self.log_dir = f'../../portfolios/{portfolio_id}/logs{alias}/{now}'
        self.intermediate_dir = f'../../portfolios/{portfolio_id}/intermediate{alias}'
        self.ohlc_dir = f'../../portfolios/{portfolio_id}/backtest-ohlc{alias}'
        self.ohlc_archive_dir = f'../../portfolios/{portfolio_id}/ohlc-archive/{portfolio_id}'
        self.ohlc_w_indicators_dir = f'../../portfolios/{portfolio_id}/ohlc-w-indicators/{portfolio_id}'
        self.charts_dir = f'../../portfolios/{portfolio_id}/charts{alias}'

        for d in [
            self.portfolio_dir, self.ib_dir, self.reports_dir, self.log_dir,
            self.intermediate_dir, self.ohlc_dir,
            self.charts_dir, self.ohlc_archive_dir, self.ohlc_w_indicators_dir
        ]:
            os.makedirs(d, exist_ok=True)

        self.paths = DirectoryPaths(
            portfolio=self.portfolio_dir,
            ib=self.ib_dir,
            reports=self.reports_dir,
            log_dir=self.log_dir,
            intermediate=self.intermediate_dir,
            ohlc=self.ohlc_dir,
            ohlc_archive=self.ohlc_archive_dir,
            ohlc_w_indicators=self.ohlc_w_indicators_dir,
            charts=self.charts_dir
        )

    def __getattr__(self, item):
        return getattr(self.paths, item)

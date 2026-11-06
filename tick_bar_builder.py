import logging
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

_NY = ZoneInfo('America/New_York')

logger = logging.getLogger(__name__)

OHLCV_COLS = ['date', 'open', 'high', 'low', 'close', 'volume']
TICK_COLS  = ['date', 'open', 'high', 'low', 'close', 'volume', 'tick_count']


class TickBarBuilder:
    """
    Builds 1-minute OHLCV bars from live ticks.

    Usage:
      1. TickBarBuilder.seed(symbol, historical_df)   -- called once per symbol
      2. TickBarBuilder.on_tick(symbol, last, bid, ask, timestamp_str)  -- called on every tick
      3. TickBarBuilder.save_all()                    -- called every hour to persist to disk
    """

    _bars: dict = {}         # symbol -> list of completed bar dicts
    _current_bar: dict = {}  # symbol -> current open bar dict (or None)
    _seeded: set = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def seed(cls, symbol: str, df: pd.DataFrame) -> None:
        """Seed from historical DataFrame. No-op if already seeded for this symbol."""
        if symbol in cls._seeded:
            return
        rows = df[OHLCV_COLS][:-1].to_dict('records')  # skip last bar — it's still open/incomplete at seed time
        cls._bars[symbol] = rows
        cls._current_bar[symbol] = None
        cls._seeded.add(symbol)
        logger.info(f"[TickBarBuilder] seeded {symbol} with {len(rows)} historical bars")

    @classmethod
    def on_tick(cls, symbol: str, last, bid, ask, timestamp_str: str, last_size=1) -> None:
        """Process an incoming tick. Updates current 1-min bar or starts a new one."""

        # Determine the price for this tick.
        # Prefer 'last' (actual trade price). Fall back to mid = (bid+ask)/2 if last is missing.
        price = cls._resolve_price(last, bid, ask)
        if price is None:
            return  # tick carries no usable price — skip it

        # Round the tick's timestamp down to the minute it belongs to.
        # e.g. "2026-11-03 14:32:47" -> datetime(2026, 11, 03, 14, 32, 00)
        bar_minute = cls._floor_to_minute(timestamp_str)
        if bar_minute is None:
            return  # unparseable timestamp — skip

        # First tick ever for this symbol — initialize empty state
        if symbol not in cls._bars:
            cls._bars[symbol] = []
            cls._current_bar[symbol] = None

        # Grab whatever bar is currently open for this symbol (may be None)
        current = cls._current_bar.get(symbol)

        # --- New bar? ---
        # This happens when: (a) no bar is open yet, or (b) the tick belongs to a later minute
        if current is None or current['date'] != bar_minute:
            # Finalize the previous bar and push it to the completed list
            if current is not None:
                cls._bars[symbol].append(current)
                logger.info(
                    f"[tick_bar] {symbol} BAR_CLOSED  date={current['date']} "
                    f"o={current['open']} h={current['high']} l={current['low']} c={current['close']} "
                    f"vol={current['volume']:.1f} ticks={current['tick_count']}"
                )

            # Open a fresh bar. All four OHLC values start at this tick's price.
            # volume = real shares traded (lastSize), tick_count = number of trades
            cls._current_bar[symbol] = {
                'date': bar_minute,
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': float(last_size),
                'tick_count': 1,
            }
            logger.info(
                f"[tick_bar] {symbol} BAR_OPENED  date={bar_minute} "
                f"first_price={price} last_size={last_size} timestamp_src={timestamp_str}"
            )
        else:
            # --- Same bar — just update it ---
            current['high'] = max(current['high'], price)
            current['low'] = min(current['low'], price)
            current['close'] = price
            current['volume'] += float(last_size)
            current['tick_count'] += 1

    @classmethod
    def get_df(cls, symbol: str) -> pd.DataFrame:
        """Return all completed bars + current live bar as a DataFrame."""
        bars = list(cls._bars.get(symbol, []))
        current = cls._current_bar.get(symbol)
        if current is not None:
            bars = bars + [current]
        if not bars:
            return pd.DataFrame(columns=TICK_COLS)
        df = pd.DataFrame(bars)
        if 'tick_count' not in df.columns:
            df['tick_count'] = 0  # seeded historical bars have no tick_count
        return df[TICK_COLS]

    @classmethod
    def save_all(cls) -> None:
        """Save each seeded symbol's tick-built DataFrame to charts/ dir."""
        from trading_core.file_manager import FileManager
        for symbol in cls._seeded:
            df = cls.get_df(symbol)
            if df.empty:
                continue
            file_name = f"{symbol}-1min-tick.csv"
            FileManager.save_my_df(df, dir="charts", file_name=file_name, mode='w')
            logger.info(f"[TickBarBuilder] saved {symbol}: {len(df)} bars -> {file_name}")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_price(last, bid, ask):
        try:
            if last is not None and not pd.isna(last):
                return float(last)
            if bid is not None and ask is not None and not pd.isna(bid) and not pd.isna(ask):
                return (float(bid) + float(ask)) / 2
        except (TypeError, ValueError):
            pass
        return None

    @staticmethod
    def _floor_to_minute(timestamp_str: str):
        try:
            ts = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            return ts.replace(second=0, microsecond=0, tzinfo=_NY)
        except (ValueError, TypeError):
            logger.warning(f"[TickBarBuilder] unparseable timestamp: {timestamp_str}")
            return None

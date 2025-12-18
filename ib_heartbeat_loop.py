import logging
logger = logging.getLogger(__name__)

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from ib_async import IB
from trading_core.file_manager import FileManager
import os
from trading_core import engine_cycle

async def ib_heartbeat_loop(
    ib: IB,
    application_state = None,
    heartbeat_file: str = None,
    interval_seconds: int = 30,
):
    """
    Periodically verifies the existing IB connection is alive
    and writes a heartbeat timestamp to a file.

    - Does NOT reconnect
    - Does NOT create a new IB client
    - Safe to run continuously
    """
    if heartbeat_file is None:
        heartbeat_file = os.path.join(FileManager.dirs.ib, "heartbeat.log")

    path = Path(heartbeat_file)

    while True:
        try:
            if engine_cycle.should_exit(application_state=application_state):
                logger.info("[market_session_guard_loop] Exiting as requested.")
                break
            # 1) Basic connection check
            if not ib.isConnected():
                # IB is not connected → do NOT write heartbeat
                await asyncio.sleep(interval_seconds)
                continue

            # 2) Lightweight API responsiveness check
            await ib.reqCurrentTimeAsync()

            # 3) Write heartbeat (UTC ISO timestamp)
            ts = datetime.now(timezone.utc).isoformat()
            path.write_text(ts)

        except Exception:
            # Any exception → skip heartbeat this round
            # Engine can decide how to react elsewhere
            pass

        await asyncio.sleep(interval_seconds)

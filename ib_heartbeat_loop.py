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
    ib_heartbeat_file: str = None,
    interval_seconds: int = 30,
):
    """
    Periodically verifies the existing IB connection is alive
    and writes a heartbeat timestamp to a file.

    - Does NOT reconnect
    - Does NOT create a new IB client
    - Safe to run continuously
    """
    if ib_heartbeat_file is None:
        ib_heartbeat_file = os.path.join(FileManager.dirs.heartbeat, "ib_heartbeat.log")
    app_heartbeat_file = os.path.join(FileManager.dirs.heartbeat, "app_heartbeat.log")

    ib_hb_path = Path(ib_heartbeat_file)
    app_hb_path = Path(app_heartbeat_file)

    while True:
        try:
            if engine_cycle.should_exit(application_state=application_state):
                logger.info("[market_session_guard_loop] Exiting as requested.")
                break
            # 1) Basic connection check

            logger.info(f"IB Heartbeat Loop: Checking IB connection...")
            ts = datetime.now(timezone.utc).isoformat()
            app_hb_path.write_text(ts)  # write app heartbeat

            if not ib.isConnected():
                # IB is not connected → do NOT write heartbeat
                logger.warning(f"@@@@@  IB Heartbeat Loop: IB not connected, skipping heartbeat write.")
                await asyncio.sleep(interval_seconds)
                continue

            # 2) Lightweight API responsiveness check
            await ib.reqCurrentTimeAsync()

            # 3) Write heartbeat (UTC ISO timestamp)

            ib_hb_path.write_text(ts)
            logger.info(f"IB Heartbeat Loop: Wrote heartbeat to {ib_heartbeat_file}")
            logger.info

        except Exception:
            # Any exception → skip heartbeat this round
            # Engine can decide how to react elsewhere
            pass

        await asyncio.sleep(interval_seconds)

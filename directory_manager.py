import os
import datetime
import logging
logger = logging.getLogger(__name__)


class DirectoryPaths:
    """
    {
  "intermediate": "...",
  "log_dir": "...",
}
paths.intermediate
paths.log_dir

    """
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class DirectoryManager:

    def __init__(self, portfolio_id: str, app_config: dict, mode: str= 'live',alias: str | None = None):
        logger.info(f"Initializing DirectoryManager")


        resolved_alias = (
            "" if mode == "live"
            else alias if alias is not None
            else "-backtest"
        )

        runtime_ctx = {
            "portfolio_id": portfolio_id,
            "alias": resolved_alias,
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        }

        dirs_cfg = app_config.get("dirs", {})
        if not dirs_cfg:
            logger.warning(f"@@@ [DirectoryManager] No 'dirs' section found in app_config")
            raise ValueError("Missing 'dirs' section in app_config")

        paths = {}
        for key, template in dirs_cfg.items():
            resolved = template.format(**runtime_ctx)
            os.makedirs(resolved, exist_ok=True)
            paths[key] = resolved
            print(f"[DirectoryManager] Created directory for '{key}': {resolved}")
        tmp = DirectoryPaths(**paths)
        from pprint import pprint
        print("[DirectoryManager] Final resolved paths:")
        pprint(vars(tmp))

        self.paths = tmp

    def __getattr__(self, item):
        return getattr(self.paths, item)

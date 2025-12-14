import os
import datetime



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

    def __init__(self, portfolio_id: str, mode: str, app_config: dict, alias: str | None = None):
        self.portfolio_id = portfolio_id
        self.mode = mode

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
            raise ValueError("Missing 'dirs' section in app_config")

        paths = {}
        for key, template in dirs_cfg.items():
            resolved = template.format(**runtime_ctx)
            os.makedirs(resolved, exist_ok=True)
            paths[key] = resolved

        self.paths = DirectoryPaths(**paths)

    def __getattr__(self, item):
        return getattr(self.paths, item)

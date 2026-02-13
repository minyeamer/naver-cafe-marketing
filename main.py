from __future__ import annotations

from task.farm import Farmer, MaxRetries, QuiteHours
from core.action import Wpm
from extensions.gsheets import WorksheetConnection
from extensions.vpn import VpnConfig
from utils.common import Delay

from typing import TypedDict, TYPE_CHECKING
import os
import yaml

if TYPE_CHECKING:
    from typing import Literal
    from pathlib import Path
    import datetime as dt


CONFIGS = [
    ".secrets/config.yaml",
    ".secrets/설정.yaml",
    "config.yaml",
    "설정.yaml",
]

class BrowserConfig(TypedDict, total=False):
    device: str
    mobile: bool
    headless: bool
    action_delay: Delay
    goto_delay: Delay
    reload_delay: Delay
    upload_delay: Delay

class ReadConfig(TypedDict):
    configs: WorksheetConnection
    openai_key: str | Path
    quiet_hours: QuiteHours
    comment_threshold: float
    like_threshold: float
    write_threshold: float
    dst_wpm: Wpm
    src_wpm: Wpm

class RunConfig(TypedDict, total=False):
    max_retries: MaxRetries
    num_my_articles: int
    max_read_length: int
    max_reply_length: int
    reload_start_step: int
    reply_cutoff_date: dt.date | str | Literal["today"]
    task_delay: float
    vpn_delay: float
    with_state: bool
    verbose: int | str | Path
    dry_run: bool
    save_log: bool


def read_configs(config_path: str | Path | None = None) -> dict:
    files = [str(config_path)] + CONFIGS if config_path else CONFIGS
    for file_path in files:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding="utf-8") as file:
                return yaml.safe_load(file.read())


def main(
        browser: BrowserConfig,
        read: ReadConfig,
        run: RunConfig,
        vpn: VpnConfig,
        write: WorksheetConnection,
    ) -> Farmer:
    farmer = Farmer(**browser, **read, vpn_config=vpn, write_config=write)
    farmer.start(**run)
    return farmer


if __name__ == "__main__":
    main(**read_configs())

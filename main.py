from __future__ import annotations
import sys
import os

if getattr(sys, "frozen", False):
    _base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
        _base, "playwright", "driver", "package", ".local-browsers"
    )

from task.farm import Farmer, MaxRetries, QuiteHours
from task.profile import ProfileManager

from core.action import Wpm
from core.browser import MOBILE_DEVICE
from extensions.gsheets import WorksheetConnection
# from extensions.vpn import VpnConfig
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
    profiles_path: str | Path
    device: str
    headless: bool
    action_delay: Delay
    goto_delay: Delay
    reload_delay: Delay
    upload_delay: Delay

class ReadConfig(TypedDict):
    configs: WorksheetConnection
    openai_key: str | Path
    mobile: bool
    quiet_hours: QuiteHours
    comment_threshold: float
    like_threshold: float
    write_threshold: float
    dst_wpm: Wpm
    src_wpm: Wpm

class FarmConfig(TypedDict, total=False):
    max_retries: MaxRetries
    num_my_articles: int
    max_read_length: int
    max_reply_length: int
    reload_start_step: int
    reply_cutoff_date: dt.date | str | Literal["today"]
    task_delay: float
    # vpn_delay: float
    verbose: int | str | Path
    dry_run: bool
    save_log: bool

class ProfileConfig(TypedDict, total=False):
    prompt_close: bool
    skip_if_logged_in: bool
    wait_interval: float


def read_configs(config_path: str | Path | None = None) -> dict:
    files = [str(config_path)] + CONFIGS if config_path else CONFIGS
    for file_path in files:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding="utf-8") as file:
                return yaml.safe_load(file.read())


def run_farm(
        browser: BrowserConfig,
        read: ReadConfig,
        farm: FarmConfig,
        # vpn: VpnConfig,
        write: WorksheetConnection,
        **kwargs
    ) -> Farmer:
    farmer = Farmer(**browser, **read, write_config=write)
    farmer.start(**farm)
    return farmer


def run_profile(
        accounts: WorksheetConnection,
        browser: BrowserConfig,
        profile: ProfileConfig,
        **kwargs
    ) -> ProfileManager:
    manager = ProfileManager(
        accounts = accounts,
        profiles_path = browser.get("profiles_path"),
        device = browser.get("device", MOBILE_DEVICE),
        headless = browser.get("headless", False),
    )
    manager.start(**profile)
    return manager


if __name__ == "__main__":
    configs = read_configs()
    mode = configs.pop("mode", "farm")
    if mode == "profile":
        run_profile(**configs)
    else:
        run_farm(**configs)

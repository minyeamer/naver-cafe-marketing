from __future__ import annotations
import functools

from playwright.sync_api import Playwright, sync_playwright
from playwright.sync_api import BrowserContext, Page

from core.login import NaverLoginError

from utils.common import AttrDict, Delay

from pathlib import Path


class ProfileNotFoundError(FileNotFoundError):
    ...


DEFAULT_DIR = "Default"
MOBILE_DEVICE = "Galaxy S24"

# Injected before every page load to normalise browser fingerprint.
STEALTH_SCRIPT = """\
(() => {
    // 1. Suppress the CDP automation marker.
    if (navigator.webdriver !== undefined) {
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true,
        });
    }
    // 2. Hardware profile — Galaxy S24 (Snapdragon 8 Gen 3)
    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
    Object.defineProperty(navigator, 'deviceMemory',        { get: () => 8 });
    Object.defineProperty(navigator, 'platform',            { get: () => 'Linux armv8l' });
    // 3. Chrome runtime object probe.
    if (!window.chrome) { window.chrome = { runtime: {} }; }
    // 4. Canvas: minimal noise on getImageData copy.
    (function () {
        const orig = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function (sx, sy, sw, sh) {
            const d = orig.call(this, sx, sy, sw, sh);
            d.data[0] ^= 0x01;
            return d;
        };
    })();
    // 5. WebGL: Qualcomm / Adreno 750 (Galaxy S24 Snapdragon).
    (function () {
        const patch = function (proto) {
            const orig = proto.getParameter;
            proto.getParameter = function (param) {
                if (param === 37445) return 'Qualcomm';
                if (param === 37446) return 'Adreno (TM) 750';
                return orig.call(this, param);
            };
        };
        patch(WebGLRenderingContext.prototype);
        if (typeof WebGL2RenderingContext !== 'undefined') {
            patch(WebGL2RenderingContext.prototype);
        }
    })();
})();
"""


def build_launch_kwargs(
        headless: bool = True,
        profile_dir: str = "Default",
        device_opts: dict | None = None,
        proxy: str | None = None,
    ) -> dict:
    kwargs = {
        "channel": "chrome",
        "headless": headless,
        "ignore_default_args": ["--enable-automation"],
        "args": [
            f"--profile-directory={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
            "--lang=ko-KR",
            "--no-restore-state",
            "--hide-crash-restore-bubble",
        ],
        "locale": "ko-KR",
        "timezone_id": "Asia/Seoul",
    }
    if device_opts:
        keys = {"device_scale_factor", "has_touch", "is_mobile", "screen", "user_agent", "viewport"}
        kwargs.update({key: value for key, value in device_opts.items() if key in keys})
    if proxy:
        kwargs["proxy"] = {"server": proxy}
    return kwargs


class BrowserSession:
    """Holds the active Playwright context and page for one profile run."""

    def __init__(self):
        ...

    def set(self, context: BrowserContext, page: Page):
        self.context: BrowserContext = context
        self.page: Page = page

    def reset(self):
        try: self.context.close()
        except: pass
        self.context: BrowserContext = None
        self.page: Page = None


class BrowserDelay(AttrDict):

    def __init__(
            self,
            action: Delay = (0.3, 0.6),
            goto: Delay = (1, 3),
            reload: Delay = (3, 5),
            upload: Delay = (2, 4),
        ):
        super().__init__()
        self.action = action
        self.goto = goto
        self.reload = reload
        self.upload = upload

    def get_delays(self, keys: list[str]) -> dict[str, Delay]:
        return {f"{key}_delay": getattr(self, key) for key in keys}


class BrowserController(AttrDict):

    def __init__(
            self,
            profile_path: str | Path,
            profile_dir: str = "Default",
            device: str | None = None,
            headless: bool = True,
            action_delay: Delay = (0.3, 0.6),
            goto_delay: Delay = (1, 3),
            reload_delay: Delay = (3, 5),
            upload_delay: Delay = (2, 4),
        ):
        super().__init__()
        self.__session = BrowserSession()
        self.__profile_path = Path(profile_path) if profile_path else Path()
        self.__profile_dir = profile_dir
        self.device: str = device
        self.headless: bool = headless
        self.delays: BrowserDelay = BrowserDelay(action_delay, goto_delay, reload_delay, upload_delay)

    @property
    def context(self) -> BrowserContext | None:
        if self.__session.context is None:
            raise RuntimeError("Browser context is not initialized.")
        return self.__session.context

    @property
    def page(self) -> Page | None:
        if self.__session.page is None:
            raise RuntimeError("Page not created.")
        return self.__session.page

    @property
    def profile(self) -> dict:
        return {"path": self.__profile_path, "dir": self.__profile_dir}

    def with_chrome_profile(func):
        @functools.wraps(func)
        def wrapper(self: BrowserController, *args, proxy: str | None = None, **kwargs):
            with sync_playwright() as playwright:
                context = self.launch_persistent_context(playwright, proxy)
                page = context.new_page()

                try:
                    self.__session.set(context, page)
                    self.authorize()
                    return func(self, *args, **kwargs)
                finally:
                    if self.__session:
                        self.__session.reset()
        return wrapper

    def launch_persistent_context(self, playwright: Playwright, proxy: str | None = None) -> BrowserContext:
        profile_path: Path = self.profile["path"]
        if not profile_path.exists():
            raise ProfileNotFoundError(f"Chrome 프로필이 없습니다: {profile_path}")

        kwargs = build_launch_kwargs(
            headless = self.headless,
            profile_dir = (self.profile["dir"] or "Default"),
            device_opts = (playwright.devices[self.device] if self.device else dict()),
            proxy = proxy,
        )
        context = playwright.chromium.launch_persistent_context(str(profile_path), **kwargs)
        context.add_init_script(STEALTH_SCRIPT)
        return context

    def authorize(self):
        naver_cookies = self.context.cookies("https://www.naver.com")
        if not any(cookie["name"] == "NID_SES" for cookie in naver_cookies):
            raise NaverLoginError("프로필에 네이버 로그인이 되어 있지 않습니다.")

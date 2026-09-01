from urllib.error import URLError
from urllib.request import Request, urlopen

import socket
import subprocess
import time

from pathlib import Path
import json
import sys
import traceback

MOBILE_IP_TOKEN = "<mobile>"


class AdbRuntimeError(RuntimeError):
    ...

class IpAddrRequestError(RuntimeError):
    ...

class IpAddrNotChangedError(RuntimeError):
    ...


def ensure_adb_server_ready(adb_path: str | Path):
    if not is_adb_server_running():
        run_adb_command(adb_path, "start-server", check=True, timeout=20.0)
    run_adb_command(adb_path, "devices", check=True, timeout=20.0)


def is_adb_server_running(host: str = "127.0.0.1", port: int = 5037) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def run_adb_command(
        adb_path: str | Path,
        *args: str,
        check: bool = True,
        timeout: float = 30.0,
    ) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(
            [str(adb_path), *args],
            check=False, text=True, capture_output=True, timeout=timeout)
    except Exception:
        exc_info = '\n'.join(traceback.format_exception(*sys.exc_info()))
        raise AdbRuntimeError(f"adb 명령 실행 실패: {' '.join(args)}\n{exc_info}")

    if check and proc.returncode != 0:
        stderr = (proc.stderr or proc.stdout or str()).strip()
        raise AdbRuntimeError(f"adb 명령 실행 실패: {' '.join(args)}\n{stderr}")
    return proc


def rotate_mobile_ip_addr(adb_path: str | Path) -> tuple[str, str]:
    original_ip = get_public_ip_addr(timeout=10.0)
    toggle_airplane_mode(adb_path)
    new_ip = wait_until_ip_addr_changed(original_ip, timeout_sec=60.0, poll_sec=3.0)
    return original_ip, new_ip


def get_public_ip_addr(timeout: float = 10.0) -> str:
    request = Request("https://api.ipify.org/?format=json")
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            ip_addr = payload.get("ip") if isinstance(payload, dict) else None
            if not ip_addr:
                raise IpAddrRequestError(f"ipify 응답이 올바르지 않습니다: {payload}")
            return str(ip_addr)
    except (TimeoutError, URLError, OSError, json.JSONDecodeError) as error:
        raise IpAddrRequestError(f"공인 IP 조회 실패: {error}") from error


def toggle_airplane_mode(adb_path: str | Path):
    run_adb_command(adb_path, "shell", "cmd", "connectivity", "airplane-mode", "enable", timeout=20.0)
    time.sleep(2.0)
    run_adb_command(adb_path, "shell", "cmd", "connectivity", "airplane-mode", "disable", timeout=20.0)


def wait_until_ip_addr_changed(
        previous_ip: str,
        timeout_sec: float = 60.0,
        poll_sec: float = 3.0,
    ) -> str:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        time.sleep(max(0.5, poll_sec))
        try:
            current_ip = get_public_ip_addr(timeout=10.0)
        except IpAddrRequestError:
            continue
        if current_ip != previous_ip:
            return current_ip
    raise IpAddrNotChangedError(f"IP 주소가 변경되지 않았습니다: {current_ip}")

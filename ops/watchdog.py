#!/usr/bin/env python3
"""
Heartbeat supervisor for the Future Transport museum kiosk.

Responsibilities
----------------
1. Launch `streamlit run museum_app/app.py` as a child process.
2. Every CHECK_INTERVAL seconds, probe the Streamlit health endpoint
   (/_stcore/health) -- this is the "heartbeat".
3. If the process dies, restart it immediately.
4. If the heartbeat fails MAX_FAILURES times in a row (app frozen/hung),
   kill and restart Streamlit.
5. Append every heartbeat to logs/heartbeat.log for monitoring.

Internet loss does NOT trigger a restart -- restarting cannot fix the network,
and the app already degrades to its offline gallery on its own. Connectivity is
still logged (ONLINE / OFFLINE) so staff can see the cause in the heartbeat log.

Run it directly for a quick test:

    .venv/bin/python ops/watchdog.py

In production it is meant to run under systemd (Restart=always) so the
supervisor itself is resurrected on crash or reboot -- see museum-kiosk.service.
"""

import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
HEARTBEAT_LOG = LOG_DIR / "heartbeat.log"

HOST = os.getenv("KIOSK_HOST", "localhost")
PORT = os.getenv("KIOSK_PORT", "8501")
BIND_ADDRESS = os.getenv("KIOSK_BIND", "0.0.0.0")
HEALTH_URL = f"http://{HOST}:{PORT}/_stcore/health"

CHECK_INTERVAL = int(os.getenv("KIOSK_CHECK_INTERVAL", "15"))  # seconds between beats
MAX_FAILURES = int(os.getenv("KIOSK_MAX_FAILURES", "4"))       # beats before restart
START_GRACE = int(os.getenv("KIOSK_START_GRACE", "20"))        # boot time before probing

_running = True


def log(msg: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    line = f"{datetime.now().isoformat(timespec='seconds')}  {msg}"
    print(line, flush=True)
    with HEARTBEAT_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def start_streamlit() -> subprocess.Popen:
    log("Starting Streamlit…")
    return subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            str(PROJECT_ROOT / "museum_app" / "app.py"),
            "--server.port", PORT,
            "--server.address", BIND_ADDRESS,
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ],
        cwd=str(PROJECT_ROOT),
    )


def streamlit_healthy() -> bool:
    """True if the Streamlit health endpoint returns HTTP 200."""
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def internet_up(timeout: float = 1.5) -> bool:
    """Informational only -- reachability of a public DNS resolver."""
    for target in (("1.1.1.1", 53), ("8.8.8.8", 53)):
        try:
            with socket.create_connection(target, timeout=timeout):
                return True
        except OSError:
            continue
    return False


def stop_streamlit(proc: subprocess.Popen) -> None:
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def _handle_signal(_signum, _frame) -> None:
    global _running
    _running = False


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    proc = start_streamlit()
    time.sleep(START_GRACE)
    failures = 0

    while _running:
        # 1. Process-level: did Streamlit exit on its own?
        if proc.poll() is not None:
            log(f"Streamlit exited (code {proc.returncode}); restarting.")
            proc = start_streamlit()
            time.sleep(START_GRACE)
            failures = 0
            continue

        # 2. Heartbeat: is the app actually responding?
        net = "ONLINE" if internet_up() else "OFFLINE"
        if streamlit_healthy():
            failures = 0
            log(f"OK    heartbeat healthy | internet={net}")
        else:
            failures += 1
            log(f"WARN  heartbeat failed ({failures}/{MAX_FAILURES}) | internet={net}")
            if failures >= MAX_FAILURES:
                log("Restarting Streamlit after repeated failed heartbeats.")
                stop_streamlit(proc)
                proc = start_streamlit()
                time.sleep(START_GRACE)
                failures = 0
                continue

        time.sleep(CHECK_INTERVAL)

    log("Supervisor shutting down; stopping Streamlit.")
    stop_streamlit(proc)


if __name__ == "__main__":
    main()

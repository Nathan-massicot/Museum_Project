# Kiosk operations — heartbeat, auto-restart & offline mode

Three layers of resilience keep the museum kiosk running unattended.

| Layer | What it does | Where |
|-------|--------------|-------|
| **systemd** (`museum-kiosk.service`) | Starts the kiosk on boot; restarts the supervisor if it ever crashes (`Restart=always`). | OS level |
| **Heartbeat supervisor** (`watchdog.py`) | Launches Streamlit, probes `/_stcore/health` every 15 s, and restarts Streamlit if it dies or freezes. Logs every beat. | Process level |
| **Offline gallery** (in `museum_app/app.py`) | When the internet is down, the app switches itself to a view-only gallery of the last 10 generated images and auto-resumes when connectivity returns. | App level |

**Why the split?** A restart fixes a frozen/crashed *app*. It cannot fix a dead
*network* — so internet loss never triggers a restart; the app degrades to the
offline gallery on its own, and the supervisor just logs `internet=OFFLINE`.

## Test it locally (macOS or Linux)

```bash
# From the project root
.venv/bin/python ops/watchdog.py        # or: uv run python ops/watchdog.py
```

Open <http://localhost:8501>. Watch the heartbeat in another terminal:

```bash
tail -f logs/heartbeat.log
```

- **Simulate a freeze/crash:** `kill` the `streamlit` child process → the
  supervisor detects it and relaunches within a few seconds.
- **Simulate internet loss:** turn off Wi-Fi → within ~12 s the app shows the
  offline gallery; the log shows `internet=OFFLINE` but Streamlit is *not*
  restarted. Turn Wi-Fi back on → the kiosk returns to the home screen
  automatically.

Stop with `Ctrl-C` (the supervisor stops Streamlit cleanly).

## Deploy on the Linux kiosk

1. Copy the project to the kiosk (e.g. `/opt/Museum_Project`) and create the
   virtualenv + install deps (`uv sync`, or `pip install -e .`).
2. Edit the three marked lines in `ops/museum-kiosk.service` (`User`,
   `WorkingDirectory`, `ExecStart`) to match your paths.
3. Install and enable the service:

   ```bash
   sudo cp ops/museum-kiosk.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now museum-kiosk.service
   ```

4. Check status / logs:

   ```bash
   systemctl status museum-kiosk.service
   journalctl -u museum-kiosk.service -f     # supervisor + Streamlit output
   tail -f logs/heartbeat.log                # heartbeat history
   ```

## Tuning (environment variables)

| Variable | Default | Meaning |
|----------|---------|---------|
| `KIOSK_PORT` | `8501` | Streamlit port |
| `KIOSK_BIND` | `0.0.0.0` | Streamlit bind address |
| `KIOSK_CHECK_INTERVAL` | `15` | Seconds between heartbeats |
| `KIOSK_MAX_FAILURES` | `4` | Consecutive failed beats before a restart |
| `KIOSK_START_GRACE` | `20` | Seconds to let Streamlit boot before probing |

> **Windows kiosk instead of Linux?** Run `watchdog.py` the same way, but wrap it
> with [NSSM](https://nssm.cc/) or Task Scheduler (set to restart on failure)
> instead of systemd. The supervisor and offline gallery are unchanged.

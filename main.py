#!/usr/bin/env python3
"""
AngKer Mini App launcher
- Builds / starts Next.js app on port 15541
- Starts Cloudflare Tunnel via tunnel.sh
"""

import os
import sys
import time
import signal
import subprocess
import shutil
from pathlib import Path

# ============================================================
# CONFIG — edit if needed
# ============================================================
PORT = 15541
HOST = "127.0.0.1"

# Cloudflare Tunnel Token
CLOUDFLARE_TUNNEL_TOKEN = os.environ.get(
    "CLOUDFLARE_TUNNEL_TOKEN",
    "eyJhIjoiMjYxOGY4MzY3Y2M3M2ExYWMxZDZlNmY2ZGM5NWIyNWUiLCJ0IjoiYjA4YWM1OWYtYTQxNy00ODA1LWE2ODEtMzM1MjEzNDI1YmU2IiwicyI6Ik5UazVZalpoTTJJdE5EVmhZUzAwWlRoa0xUaG1OVGd0WVRNMU1HUXdNVEU1TmpjeiJ9",
)

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "angker-ready"
TUNNEL_SCRIPT = ROOT / "tunnel.sh"
ZIP_MARKER = APP_DIR / ".zip-applied"

# Processes we start
procs = []


def log(msg: str):
    print(f"[main] {msg}", flush=True)


def cleanup(signum=None, frame=None):
    log("Shutting down...")
    for p in reversed(procs):
        try:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()
        except Exception as e:
            log(f"cleanup error: {e}")
    sys.exit(0)


def ensure_app_dir():
    """Make sure angker-ready exists (user should upload it or use previous unpack)."""
    if not APP_DIR.is_dir():
        log(f"ERROR: {APP_DIR} not found.")
        log("Upload the angker-ready folder next to main.py, then run again.")
        sys.exit(1)
    log(f"App directory: {APP_DIR}")


def run_npm(cmd: list, cwd: Path, env: dict | None = None):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    log(f"Running: {' '.join(cmd)} (cwd={cwd})")
    r = subprocess.run(cmd, cwd=str(cwd), env=full_env)
    if r.returncode != 0:
        log(f"Command failed with code {r.returncode}")
        sys.exit(r.returncode)


def build_if_needed():
    """Install deps + build if .next is missing or forced."""
    node_modules = APP_DIR / "node_modules"
    next_dir = APP_DIR / ".next"

    if not node_modules.is_dir():
        log("node_modules missing → npm install")
        run_npm(["npm", "install"], APP_DIR)

    # Force rebuild if marker removed or .next missing
    force = not ZIP_MARKER.exists() or not next_dir.is_dir()
    if force:
        log("Building app (npm run build)...")
        run_npm(["npm", "run", "build"], APP_DIR)
        ZIP_MARKER.touch()
        log("Build finished.")
    else:
        log("Using existing build (.next found).")


def start_next():
    """Start Next.js on PORT."""
    env = os.environ.copy()
    env["PORT"] = str(PORT)
    env["HOSTNAME"] = HOST
    # Next.js respects PORT
    cmd = ["npm", "run", "start", "--", "-p", str(PORT), "-H", HOST]
    log(f"Starting Next.js → http://{HOST}:{PORT}")
    p = subprocess.Popen(
        cmd,
        cwd=str(APP_DIR),
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    procs.append(p)
    return p


def start_tunnel():
    """Start Cloudflare Tunnel by calling tunnel.sh"""
    if not TUNNEL_SCRIPT.is_file():
        log(f"WARNING: {TUNNEL_SCRIPT} not found — skipping tunnel")
        return None

    # Make executable
    TUNNEL_SCRIPT.chmod(TUNNEL_SCRIPT.stat().st_mode | 0o111)

    env = os.environ.copy()
    if CLOUDFLARE_TUNNEL_TOKEN:
        env["CLOUDFLARE_TUNNEL_TOKEN"] = CLOUDFLARE_TUNNEL_TOKEN

    log(f"Starting tunnel via {TUNNEL_SCRIPT.name}")
    p = subprocess.Popen(
        ["bash", str(TUNNEL_SCRIPT)],
        cwd=str(ROOT),
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    procs.append(p)
    return p


def wait_for_port(port: int, timeout: int = 60):
    """Wait until local port is listening."""
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((HOST, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    log("=== AngKer Mini App launcher ===")
    log(f"Target: http://{HOST}:{PORT}")

    ensure_app_dir()
    build_if_needed()

    # Start Next.js first
    next_proc = start_next()

    log("Waiting for app to listen...")
    if wait_for_port(PORT, timeout=90):
        log(f"App is up on http://{HOST}:{PORT}")
    else:
        log("WARNING: port not ready in time — continuing anyway")

    # Then start tunnel (so it can reach local port)
    tunnel_proc = start_tunnel()

    if not CLOUDFLARE_TUNNEL_TOKEN and not os.environ.get("CLOUDFLARE_TUNNEL_TOKEN"):
        log("")
        log("*** CLOUDFLARE_TUNNEL_TOKEN is empty ***")
        log("Edit main.py or tunnel.sh and paste your token,")
        log("or run:  export CLOUDFLARE_TUNNEL_TOKEN='your_token_here'")
        log("Then restart:  python3 main.py")
        log("")

    log("Both processes running. Press Ctrl+C to stop.")

    # Keep alive and watch children
    while True:
        time.sleep(2)
        if next_proc.poll() is not None:
            log(f"Next.js exited with code {next_proc.returncode}")
            cleanup()
        if tunnel_proc and tunnel_proc.poll() is not None:
            code = tunnel_proc.returncode
            log(f"Tunnel exited with code {code}")
            # If token missing, tunnel exits early — keep app running
            if code == 2:
                log("Tunnel stopped (token missing?). App continues on local port.")
                tunnel_proc = None
            else:
                log("Restarting tunnel in 5s...")
                time.sleep(5)
                tunnel_proc = start_tunnel()


if __name__ == "__main__":
    main()

"""Start the Resume Studio web app: API + built UI on one local port, then open the browser.

    python -m resume_builder.webapp            # first free port from 8001, opens browser
    python -m resume_builder.webapp --no-browser --port 8001

Requires the web extra:  pip install ".[web]"   and a built UI (cd web && npm run build).
The server only listens on 127.0.0.1, so nothing is exposed to your network.
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path


def find_free_port(start: int = 8001, attempts: int = 20) -> int:
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port between {start} and {start + attempts - 1}")


def _open_when_ready(url: str, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url + "api/studio/config", timeout=2):
                webbrowser.open(url)
                return
        except Exception:
            time.sleep(0.5)


def ui_is_current(web_dir: Path) -> bool:
    """True if web/dist exists and is newer than every file in web/src + package.json."""
    index = web_dir / "dist" / "index.html"
    if not index.is_file():
        return False
    built = index.stat().st_mtime
    sources = [p for p in (web_dir / "src").rglob("*") if p.is_file()]
    sources += [web_dir / n for n in ("package.json", "index.html", "vite.config.ts") if (web_dir / n).is_file()]
    return all(p.stat().st_mtime <= built for p in sources)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="resume-studio", description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=0, help="port (default: first free from 8001)")
    ap.add_argument("--no-browser", action="store_true", help="don't open a browser window")
    ap.add_argument("--web-dist", help="path to the built UI (default: <repo>/web/dist)")
    ap.add_argument("--check-ui", metavar="WEB_DIR",
                    help="exit 0 if WEB_DIR/dist is built and up to date, else 1 (used by run_resume.bat)")
    args = ap.parse_args(argv)

    if args.check_ui:
        return 0 if ui_is_current(Path(args.check_ui)) else 1

    try:
        import uvicorn  # noqa: F401
        import fastapi  # noqa: F401
        import multipart  # noqa: F401
    except ImportError as e:
        print(f"Missing web dependency ({e.name}). Install with:  pip install \".[web]\"")
        return 2

    dist = Path(args.web_dist) if args.web_dist else Path(
        os.environ.get("RESUME_WEB_DIST") or Path(__file__).resolve().parents[2] / "web" / "dist")
    if not (dist / "index.html").is_file():
        print(f"The web UI is not built yet ({dist / 'index.html'} missing).\n"
              "Build it with:  cd web  &&  npm install  &&  npm run build")
        return 2
    os.environ["RESUME_WEB_DIST"] = str(dist)

    port = args.port or find_free_port()
    url = f"http://127.0.0.1:{port}/"
    backend = os.environ.get("RESUME_BACKEND") or "none (format only)"
    print("=" * 68, flush=True)
    print(f" Resume Studio is running at {url}")
    print(f" AI backend: {backend}")
    print(" Keep this window open while you use the app. Close it to stop.")
    print("=" * 68, flush=True)
    if not args.no_browser and not os.environ.get("RESUME_NO_BROWSER"):
        threading.Thread(target=_open_when_ready, args=(url,), daemon=True).start()

    import uvicorn
    from .api.main import app
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())

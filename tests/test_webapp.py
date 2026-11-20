import os
import socket
import time
from pathlib import Path

from resume_builder import webapp


def test_find_free_port_skips_busy_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen()
        busy = s.getsockname()[1]
        assert webapp.find_free_port(busy, attempts=5) != busy


def _make_web(tmp_path: Path, build_first: bool) -> Path:
    web = tmp_path / "web"
    (web / "src").mkdir(parents=True)
    (web / "dist").mkdir()
    src = web / "src" / "App.tsx"
    idx = web / "dist" / "index.html"
    first, second = (idx, src) if build_first else (src, idx)
    first.write_text("x")
    old = time.time() - 100
    os.utime(first, (old, old))
    second.write_text("y")
    return web


def test_check_ui_detects_missing_stale_and_current(tmp_path):
    assert webapp.main(["--check-ui", str(tmp_path / "nope")]) == 1
    assert webapp.main(["--check-ui", str(_make_web(tmp_path / "a", build_first=True))]) == 1
    assert webapp.main(["--check-ui", str(_make_web(tmp_path / "b", build_first=False))]) == 0


def test_launcher_refuses_without_built_ui(tmp_path, capsys):
    assert webapp.main(["--no-browser", "--web-dist", str(tmp_path)]) == 2
    assert "npm run build" in capsys.readouterr().out

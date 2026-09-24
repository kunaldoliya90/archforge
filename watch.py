#!/usr/bin/env python3
"""ArchForge live-reload dev loop.

    python watch.py                 # re-render diagrams on save
    python watch.py --serve         # + build the site, serve it, auto-refresh the browser
    python watch.py --once          # render every diagram once and exit (CI / pre-commit)

* Saving architecture/<name>.py re-renders docs/assets/<name>.png.
  Files starting with "_" (e.g. _style.py) are shared helpers: saving one re-renders all.
* With --serve, any change in docs/ or theme/ (including a freshly rendered PNG)
  rebuilds the site via build.py and refreshes open browser tabs.

If the Python packages or Graphviz aren't installed locally, it re-runs itself
inside Docker (docker compose) automatically; pass --local to disable that.
Set WATCH_POLLING=1 inside Docker on Windows/macOS, where bind mounts don't emit
native filesystem events.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARCH_DIR = ROOT / "architecture"
DOCS_DIR = ROOT / "docs"
THEME_DIR = ROOT / "theme"
OUT_DIR = ROOT / "public"
DEBOUNCE_SECONDS = 0.25  # editors often emit several events per save
RENDER_TIMEOUT_SECONDS = 60

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"

# Windows consoles default to cp1252, which can't print ✔ / ✘ / 👀.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
if os.name == "nt":
    os.system("")  # enables ANSI colour codes in the classic Windows console


# ── Diagrams ─────────────────────────────────────────────────────────────────

def diagram_files() -> list[Path]:
    return sorted(p for p in ARCH_DIR.glob("*.py") if not p.name.startswith("_"))


def render(path: Path) -> bool:
    started = time.perf_counter()
    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=RENDER_TIMEOUT_SECONDS,
    )
    elapsed = time.perf_counter() - started
    rel = path.relative_to(ROOT).as_posix()
    if result.returncode == 0:
        print(f"{GREEN}✔{RESET} {rel} {DIM}({elapsed:.2f}s){RESET}", flush=True)
        return True
    print(f"{RED}✘ {rel} failed ({elapsed:.2f}s){RESET}", flush=True)
    print(result.stderr.strip() or result.stdout.strip(), flush=True)
    return False


def render_all() -> bool:
    # Evaluate every file (no short-circuit) so all errors are reported at once.
    return all([render(p) for p in diagram_files()])


# ── Site ─────────────────────────────────────────────────────────────────────

# Held while public/ is being rewritten; the dev server takes it before reading a
# file, so a request that lands mid-rebuild waits instead of getting half a page.
SITE_LOCK = threading.Lock()


def build_site() -> bool:
    """Rebuild public/. Returns True only if something changed (i.e. browsers should reload)."""
    started = time.perf_counter()
    try:
        import build
        importlib.reload(build)  # pick up edits to build.py without restarting
        with SITE_LOCK:
            _, changed = build.build(dev=True)
    except Exception as exc:  # keep the watcher alive on any build error
        is_build_error = type(exc).__name__ == "BuildError"
        print(f"{RED}✘ site build failed{RESET}\n{exc if is_build_error else traceback.format_exc()}", flush=True)
        return False
    if changed:
        print(f"{GREEN}✔{RESET} site {DIM}({changed} files updated, {time.perf_counter() - started:.2f}s){RESET}", flush=True)
    return changed > 0


class Reloader:
    """Tells connected browsers (via Server-Sent Events) to refresh."""

    def __init__(self) -> None:
        self.version = 0
        self.cond = threading.Condition()

    def notify(self) -> None:
        with self.cond:
            self.version += 1
            self.cond.notify_all()


def start_server(host: str, reloader: Reloader) -> ThreadingHTTPServer:
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(OUT_DIR), **kwargs)

        def log_message(self, *args) -> None:
            pass

        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def do_GET(self) -> None:
            if self.path == "/__reload":
                return self._events()
            path, _, query = self.path.partition("?")
            target = Path(self.translate_path(path))
            if target.is_dir() and not path.endswith("/"):
                self.send_response(301)
                self.send_header("Location", path + "/" + (f"?{query}" if query else ""))
                self.end_headers()
                return
            if target.is_dir():
                target = target / "index.html"
            with SITE_LOCK:
                found = target.is_file()
                if found:
                    body = target.read_bytes()
                else:
                    missing = OUT_DIR / "404.html"
                    body = missing.read_bytes() if missing.exists() else b"Not found"
            if found:
                self._send(200, self.guess_type(str(target)), body)
            else:
                self._send(404, "text/html; charset=utf-8", body)

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _events(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            seen = reloader.version
            try:
                while True:
                    with reloader.cond:
                        if reloader.version == seen:
                            reloader.cond.wait(timeout=20)
                    if reloader.version != seen:
                        seen = reloader.version
                        self.wfile.write(b"data: reload\n\n")
                    else:
                        self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    address, _, port = host.rpartition(":")
    server = ThreadingHTTPServer((address or "127.0.0.1", int(port)), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    shown = "localhost" if address in ("0.0.0.0", "") else address
    print(f"🌐 Serving http://{shown}:{port}", flush=True)
    return server


# ── Watching ─────────────────────────────────────────────────────────────────

class Debouncer:
    """Collects changed paths and acts once the burst of events settles."""

    def __init__(self, reloader: Reloader | None) -> None:
        self._pending: set[Path] = set()
        self._lock = threading.Lock()
        # Serialises flushes: diagrams writes a temp file next to the PNG, so two
        # overlapping renders of the same diagram would delete each other's file.
        self._flush_lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._reloader = reloader

    def add(self, path: Path) -> None:
        with self._lock:
            self._pending.add(path)
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(DEBOUNCE_SECONDS, self._flush)
            self._timer.start()

    def _flush(self) -> None:
        with self._flush_lock:
            with self._lock:
                paths, self._pending = self._pending, set()
            if paths:
                self._process(paths)

    def _process(self, paths: set[Path]) -> None:
        diagrams = sorted(p for p in paths if p.parent == ARCH_DIR)
        site_changed = any(p.is_relative_to(DOCS_DIR) or p.is_relative_to(THEME_DIR) for p in paths)

        if any(p.name.startswith("_") for p in diagrams):
            print(f"{DIM}shared helper changed → re-rendering all{RESET}", flush=True)
            render_all()
        else:
            for path in diagrams:
                if path.exists():
                    render(path)
        # Rebuild right after a render instead of waiting to notice the new PNG; the
        # PNG event that follows then finds nothing changed and doesn't reload again.
        if (site_changed or diagrams) and self._reloader and build_site():
            self._reloader.notify()


def watch(polling: bool, reloader: Reloader | None) -> None:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler

    if polling:
        from watchdog.observers.polling import PollingObserver as Observer
    else:
        from watchdog.observers import Observer

    debouncer = Debouncer(reloader)

    class Handler(FileSystemEventHandler):
        def on_any_event(self, event: FileSystemEvent) -> None:
            if event.is_directory or event.event_type not in ("modified", "created", "moved", "deleted"):
                return
            raw = getattr(event, "dest_path", "") or event.src_path
            path = Path(os.fsdecode(raw)).resolve()
            if path.parent == ARCH_DIR:
                if path.suffix == ".py" and event.event_type != "deleted":
                    debouncer.add(path)
            elif reloader and not path.name.startswith("."):
                debouncer.add(path)

    # Polling at 0.3s keeps save→PNG well under the 2s budget inside Docker.
    observer = Observer(timeout=0.3) if polling else Observer()
    observer.schedule(Handler(), str(ARCH_DIR), recursive=False)
    watched = ["architecture/*.py"]
    if reloader:
        observer.schedule(Handler(), str(DOCS_DIR), recursive=True)
        observer.schedule(Handler(), str(THEME_DIR), recursive=True)
        watched += ["docs/", "theme/"]
    observer.start()
    mode = "polling" if polling else "native events"
    print(f"👀 Watching {', '.join(watched)} ({mode}). Ctrl+C to stop.", flush=True)
    try:
        while observer.is_alive():
            observer.join(1)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()


# ── Entry point ──────────────────────────────────────────────────────────────

def missing_prerequisites(serve: bool) -> list[str]:
    modules = {"diagrams": "diagrams", "watchdog": "watchdog"}
    if serve:
        modules.update({"markdown": "markdown", "pygments": "pygments"})
    missing = [f"Python package '{pkg}'" for mod, pkg in modules.items() if importlib.util.find_spec(mod) is None]
    if shutil.which("dot") is None:
        missing.append("Graphviz (the 'dot' command)")
    return missing


def run_in_docker(once: bool) -> int:
    """Delegate to the Docker toolchain, which has Python deps + Graphviz baked in."""
    if once:
        cmd = ["docker", "compose", "run", "--rm", "--build", "docs", "watch.py", "--once"]
    else:
        print(f"{DIM}Site preview will be at http://localhost:8000{RESET}", flush=True)
        cmd = ["docker", "compose", "up", "--build"]
    try:
        return subprocess.call(cmd, cwd=ROOT)
    except KeyboardInterrupt:
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--once", action="store_true", help="render all diagrams once and exit")
    parser.add_argument("--serve", action="store_true", help="also build + serve the site with live reload")
    parser.add_argument("--host", default="127.0.0.1:8000", help="address for --serve (default: %(default)s)")
    parser.add_argument("--polling", action="store_true", default=os.environ.get("WATCH_POLLING") == "1",
                        help="use polling instead of native FS events (auto-on when WATCH_POLLING=1)")
    parser.add_argument("--local", action="store_true", help="never fall back to Docker")
    args = parser.parse_args()

    missing = missing_prerequisites(args.serve)
    if missing:
        print(f"{RED}Missing locally:{RESET} " + ", ".join(missing), flush=True)
        if not args.local and shutil.which("docker"):
            print("→ Running inside Docker instead (use --local to disable).", flush=True)
            return run_in_docker(args.once)
        print("Fix: pip install -r requirements.txt, and install Graphviz "
              "(winget install Graphviz.Graphviz · brew install graphviz · apt install graphviz), "
              "or install Docker and run: docker compose up", flush=True)
        return 1

    ok = render_all()
    if args.once:
        return 0 if ok else 1

    reloader = server = None
    if args.serve:
        reloader = Reloader()
        build_site()
        server = start_server(args.host, reloader)
    try:
        watch(args.polling, reloader)
    finally:
        if server:
            server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())

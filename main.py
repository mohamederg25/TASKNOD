"""TaskNudge entry point."""

from __future__ import annotations

import argparse
import getpass
import hashlib
import logging
import logging.handlers
import re
import sys
from typing import Optional

from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QMessageBox

from tasknudge import APP_NAME, __version__
from tasknudge import autostart
from tasknudge.application import ApplicationController
from tasknudge.avatar import make_app_icon
from tasknudge.config import Config
from tasknudge.paths import data_dir, log_path
from tasknudge.storage import TaskStore
from tasknudge.ui.style import GLOBAL_STYLE

log = logging.getLogger(__name__)


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s  %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        handler = logging.handlers.RotatingFileHandler(
            log_path(), maxBytes=1_000_000, backupCount=2, encoding="utf-8"
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)
    except OSError:
        pass
    if sys.stderr is not None:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)


def _instance_name() -> str:
    digest = hashlib.sha1(str(data_dir()).encode("utf-8")).hexdigest()[:10]
    user = re.sub(r"[^A-Za-z0-9_.-]", "_", getpass.getuser() or "user")
    return f"TaskNudge-{user}-{digest}"


def _notify_existing_instance(name: str) -> bool:
    socket = QLocalSocket()
    socket.connectToServer(name)
    if not socket.waitForConnected(250):
        return False
    socket.write(b"show\n")
    socket.flush()
    socket.waitForBytesWritten(250)
    socket.disconnectFromServer()
    return True


def _start_server(name: str) -> Optional[QLocalServer]:
    QLocalServer.removeServer(name)
    server = QLocalServer()
    if not server.listen(name):
        log.warning("Could not listen for the single-instance socket: %s", server.errorString())
        return None
    return server


def _wire_show_requests(server: QLocalServer, controller: ApplicationController) -> None:
    def handle_connection() -> None:
        while server.hasPendingConnections():
            socket = server.nextPendingConnection()
            if socket is None:
                continue

            def read_request(current=socket) -> None:
                payload = bytes(current.readAll()).decode("utf-8", errors="ignore").strip()
                if payload == "show":
                    controller.show_task_list()
                current.disconnectFromServer()

            socket.readyRead.connect(read_request)
            if socket.bytesAvailable():
                read_request()
            socket.disconnected.connect(socket.deleteLater)

    server.newConnection.connect(handle_connection)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument(
        "--minimized",
        action="store_true",
        help="start only in the system tray (used by auto-start)",
    )
    parser.add_argument(
        "--install-autostart",
        action="store_true",
        help="add TaskNudge to this Windows user's login items and exit",
    )
    parser.add_argument(
        "--remove-autostart",
        action="store_true",
        help="remove TaskNudge from this Windows user's login items and exit",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.install_autostart or args.remove_autostart:
        try:
            autostart.set_enabled(args.install_autostart)
        except OSError as exc:
            print(f"Could not update auto-start: {exc}", file=sys.stderr)
            return 1
        action = "installed" if args.install_autostart else "removed"
        print(f"TaskNudge auto-start {action}.")
        print(f"Command: {autostart.command_preview()}")
        return 0

    setup_logging()
    log.info("Starting %s %s", APP_NAME, __version__)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("TaskNudge")
    app.setStyle("Fusion")
    app.setWindowIcon(make_app_icon())
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(GLOBAL_STYLE)

    name = _instance_name()
    if _notify_existing_instance(name):
        log.info("Another TaskNudge instance is already running; asked it to show.")
        return 0

    server = _start_server(name)
    if server is not None:
        app.aboutToQuit.connect(lambda: QLocalServer.removeServer(name))

    try:
        config = Config.load()
        store = TaskStore()
    except Exception as exc:
        log.exception("TaskNudge could not start")
        QMessageBox.critical(
            None,
            "TaskNudge could not start",
            f"TaskNudge could not open its local data:\n\n{exc}",
        )
        return 1

    controller = ApplicationController(app, config, store)
    if server is not None:
        _wire_show_requests(server, controller)

    controller.start(show_window=not args.minimized)
    log.info("TaskNudge is running")
    exit_code = app.exec()

    if server is not None:
        server.close()
        QLocalServer.removeServer(name)
    log.info("TaskNudge stopped")
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())

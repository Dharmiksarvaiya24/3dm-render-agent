# ===== controller/watcher.py =====

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from shared.logger import get_logger

logger = get_logger("watcher")

POLL_INTERVAL = 5  # seconds between folder scans


class RenderFileHandler(FileSystemEventHandler):
    def __init__(self, queue):
        self.queue = queue
        self.processed = set()

    def on_created(self, event):
        if event.is_directory:
            return
        self._handle_file(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return
        self._handle_file(event.dest_path)

    def _handle_file(self, path):
        path = Path(path)

        if not path.exists():
            return

        if path.suffix.lower() != ".3dm":
            return

        if str(path) in self.processed:
            logger.info(f"Already processed: {path.name}")
            return

        self.processed.add(str(path))
        logger.info(f"Creating job for: {path.name}")
        try:
            self.queue.create_job(str(path), path.name)
            logger.info(f"✅ New job created for: {path.name}")
        except Exception as e:
            logger.error(f"Failed to create job for {path.name}: {e}")


def scan_folder(folder: Path, handler: RenderFileHandler):
    if not folder.exists():
        return
    try:
        for entry in folder.iterdir():
            if entry.is_file() and entry.suffix.lower() == ".3dm":
                handler._handle_file(str(entry))
    except Exception as e:
        logger.error(f"Folder scan error: {e}")


def start_watcher(queue, input_folder):
    input_folder = Path(input_folder)
    input_folder.mkdir(parents=True, exist_ok=True)
    logger.info(f"👁 Watching folder: {input_folder}")

    handler = RenderFileHandler(queue)

    # Scan existing files on startup
    logger.info("Scanning for existing .3dm files...")
    scan_folder(input_folder, handler)

    # Start watchdog for real-time events
    observer = Observer()
    observer.schedule(handler, str(input_folder), recursive=False)
    observer.start()
    logger.info("✅ Watcher started")

    # Keep thread alive and periodically scan for missed files
    try:
        while True:
            time.sleep(POLL_INTERVAL)
            scan_folder(input_folder, handler)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()

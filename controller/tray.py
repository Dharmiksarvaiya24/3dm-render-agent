# ===== controller/tray.py =====

import os
import sys
import webbrowser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.logger import get_logger

logger = get_logger("tray")

_queue_paused = False


def is_queue_paused() -> bool:
    return _queue_paused


def start_tray() -> None:
    global _queue_paused
    try:
        import pystray
    except ImportError:
        logger.warning("pystray not installed — tray icon skipped")
        return

    try:
        from PIL import Image, ImageDraw
        import threading

        def create_icon_image():
            img = Image.new("RGB", (64, 64), color=(59, 130, 246))
            draw = ImageDraw.Draw(img)
            draw.rectangle([16, 20, 48, 44], fill="white")
            draw.rectangle([24, 28, 28, 36], fill=(59, 130, 246))
            return img

        def open_dashboard(icon, item):
            webbrowser.open("http://localhost:8765")

        def toggle_pause(icon, item):
            global _queue_paused
            _queue_paused = not _queue_paused
            logger.info(f"Queue {'paused' if _queue_paused else 'resumed'}")
            icon.update_menu()

        def quit_app(icon, item):
            logger.info("Quit from tray menu")
            icon.stop()
            os._exit(0)

        def setup(icon):
            icon.visible = True

        def build_menu():
            from pystray import Menu, MenuItem

            pause_text = "Resume Queue" if _queue_paused else "Pause Queue"
            return Menu(
                MenuItem("Open Dashboard", open_dashboard, default=True),
                MenuItem(pause_text, toggle_pause),
                Menu.SEPARATOR,
                MenuItem("Quit", quit_app),
            )

        icon = pystray.Icon(
            "RenderAgent",
            create_icon_image(),
            "RenderAgent Controller",
            menu=build_menu,
        )

        logger.info("System tray icon started")
        icon.run(setup)

    except Exception:
        import traceback

        logger.warning(f"Tray icon failed: {traceback.format_exc()}")
# ===== controller/main.py =====

import os
import socket
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.config import Config
from shared.logger import get_logger

logger = get_logger("controller")


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def start_udp_listener(port: int) -> None:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
        sock.settimeout(5)
        logger.info(f"UDP discovery listener started on port {port}")

        while True:
            try:
                data, addr = sock.recvfrom(1024)
                if b"RENDERAGENT_DISCOVER" in data:
                    local_ip = get_local_ip()
                    response = f"RENDERAGENT_CONTROLLER http://{local_ip}:8765".encode()
                    sock.sendto(response, addr)
                    logger.debug(f"Discovery response sent to {addr[0]}")
            except socket.timeout:
                continue
            except Exception:
                import traceback

                logger.error(f"UDP listener error: {traceback.format_exc()}")
    except Exception:
        import traceback

        logger.error(f"Failed to start UDP listener: {traceback.format_exc()}")


def start_stuck_job_recovery(interval_seconds: int = 300) -> None:
    def _loop():
        while True:
            try:
                from controller.job_queue import reset_stuck_jobs

                reset_stuck_jobs(timeout_minutes=30)
            except Exception:
                import traceback

                logger.error(f"Stuck job recovery error: {traceback.format_exc()}")
            time.sleep(interval_seconds)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    logger.info(f"Stuck job recovery started (every {interval_seconds}s)")


def main() -> None:
    try:
        logger.info("=== RenderAgent Controller Starting ===")

        config = Config()

        if not config.is_complete():
            logger.info("Config incomplete — launching setup wizard...")
            from controller.setup_wizard import run_wizard

            wizard_data = run_wizard()
            for key, value in wizard_data.items():
                if value:
                    config.set(key, str(value))
            logger.info("Setup complete")

        from controller.job_queue import init_db, reset_stuck_jobs

        init_db()

        reset_stuck_jobs(timeout_minutes=2)
        logger.info("✅ Stuck jobs reset")

        input_folder = config.get("input_folder") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "input"
        )
        if not os.path.exists(input_folder):
            os.makedirs(input_folder, exist_ok=True)
            logger.info(f"Created input folder: {input_folder}")

        threading.Thread(
            target=lambda: start_watcher_safe(input_folder), daemon=True
        ).start()
        logger.info("Folder watcher thread started")

        udp_port = 8766
        try:
            udp_port = int(config.get("udp_port") or 8766)
        except Exception:
            pass
        threading.Thread(
            target=lambda: start_udp_listener(udp_port), daemon=True
        ).start()

        try:
            import platform

            if platform.system() == "Windows":
                threading.Thread(target=start_tray_safe, daemon=True).start()
            else:
                logger.info("System tray skipped (non-Windows platform)")
        except Exception:
            pass

        from controller.updater import start_background_check

        start_background_check(interval_seconds=3600)

        start_stuck_job_recovery(interval_seconds=300)

        import uvicorn

        port = 8765
        try:
            port = int(config.get("port") or 8765)
        except Exception:
            pass

        logger.info(f"Starting FastAPI server on 0.0.0.0:{port}")
        logger.info(f"Dashboard: http://localhost:{port}")
        uvicorn.run(
            "controller.api:app",
            host="0.0.0.0",
            port=port,
            log_level="warning",
            access_log=False,
        )

    except KeyboardInterrupt:
        logger.info("Controller shutting down...")
    except Exception:
        import traceback

        logger.error(f"Fatal error: {traceback.format_exc()}")
        sys.exit(1)


def start_watcher_safe(input_folder: str) -> None:
    try:
        from controller.watcher import start_watcher
        from controller import job_queue

        observer = start_watcher(job_queue, input_folder)
    except Exception:
        import traceback

        logger.error(f"Watcher thread failed: {traceback.format_exc()}")


def start_tray_safe() -> None:
    try:
        from controller.tray import start_tray

        start_tray()
    except Exception:
        pass


if __name__ == "__main__":
    main()
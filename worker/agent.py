# ===== worker/agent.py =====

import os
import socket
import subprocess
import sys
import threading
import time
import asyncio
from typing import Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.config import Config
from shared.logger import get_logger

logger = get_logger("worker")

_jobs_completed = 0
_current_job_id = None


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def discover_controller(udp_port: int = 8766, timeout_s: int = 10) -> str:
    logger.info("Discovering controller via UDP broadcast...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout_s)
        sock.sendto(b"RENDERAGENT_DISCOVER", ("255.255.255.255", udp_port))
        data, addr = sock.recvfrom(1024)
        response = data.decode()
        if response.startswith("RENDERAGENT_CONTROLLER "):
            url = response.split(" ", 1)[1].strip()
            logger.info(f"Controller discovered: {url}")
            return url
        raise TimeoutError("Invalid discovery response")
    except socket.timeout:
        raise TimeoutError(
            f"No controller responded after {timeout_s} seconds on UDP port {udp_port}"
        )


def get_system_metrics() -> dict:
    metrics = {"utilization": None, "temperature": None, "fan_speed": None}
    if not HAS_PSUTIL:
        return metrics
    try:
        metrics["utilization"] = round(psutil.cpu_percent(interval=0.5), 1)
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                if entries:
                    metrics["temperature"] = round(entries[0].current, 1)
                    break
        fans = psutil.sensors_fans()
        if fans:
            for name, entries in fans.items():
                if entries:
                    metrics["fan_speed"] = round(entries[0].current, 1)
                    break
    except Exception:
        pass
    return metrics


def send_heartbeat(
    controller_url: str,
    worker_id: str,
    jobs_completed: int,
    current_job_id: Optional[str] = None,
) -> None:
    try:
        import requests

        payload = {
            "worker_id": worker_id,
            "ip": get_local_ip(),
            "jobs_completed": jobs_completed,
            "current_job_id": current_job_id,
        }
        payload.update(get_system_metrics())
        requests.post(
            f"{controller_url}/api/workers/heartbeat",
            json=payload,
            timeout=5,
        )
    except Exception:
        import traceback

        logger.debug(f"Heartbeat failed: {traceback.format_exc()}")


async def process_job(job: dict, config: dict) -> str:
    global _jobs_completed, _current_job_id

    file_path = job["file_path"]
    output_folder = config.get("output_folder") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output"
    )
    email = config.get("ijewel_email")
    password = config.get("ijewel_password")

    _current_job_id = job["id"]

    try:
        from worker.ijewel_automation import run

        success = await run(
            file_path=file_path,
            output_folder=output_folder,
            email=email,
            password=password,
        )
        if success:
            _jobs_completed += 1
            _current_job_id = None
            output_filename = os.path.splitext(os.path.basename(file_path))[0] + ".mp4"
            return os.path.join(output_folder, output_filename)
        raise Exception("Automation returned False")
    except Exception:
        _current_job_id = None
        raise


async def get_next_job(worker_id: str, controller_url: str) -> Optional[dict]:
    import requests

    try:
        response = requests.get(
            f"{controller_url}/api/jobs/next?worker_id={worker_id}",
            timeout=30,
        )
        if response.status_code == 204:
            return None
        return response.json()
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to controller at {controller_url}")
        raise
    except Exception as e:
        logger.error(f"Error polling for job: {e}")
        raise


async def poll_loop(controller_url: str, worker_id: str, config: dict) -> None:
    import traceback as tb_module
    import requests

    running = True
    while running:
        try:
            logger.info("Polling for jobs...")
            job = await get_next_job(worker_id, controller_url)
            if job:
                logger.info(f"✅ Got job: {job['file_name']}")
                logger.info(
                    f"Claimed job: {job['file_name']} (ID: {job['id']})"
                )

                requests.post(
                    f"{controller_url}/api/jobs/{job['id']}/status",
                    json={"status": "PROCESSING"},
                    timeout=10,
                )

                output_path = await process_job(job, config)

                requests.post(
                    f"{controller_url}/api/jobs/{job['id']}/status",
                    json={
                        "status": "COMPLETED",
                        "output_path": output_path,
                    },
                    timeout=10,
                )

                logger.info(f"Job {job['id']} completed successfully")
                logger.info("Job done, polling immediately for next job")
                continue
            else:
                logger.info("No jobs available, waiting 3s...")
                await asyncio.sleep(3)
        except requests.exceptions.ConnectionError:
            logger.error("Connection error, retrying in 3s...")
            await asyncio.sleep(3)
        except Exception as e:
            tb = tb_module.format_exc()
            logger.error(f"Job failed: {tb}")
            try:
                if "job" in dir():
                    requests.post(
                        f"{controller_url}/api/jobs/{job['id']}/status",
                        json={
                            "status": "FAILED",
                            "error_message": tb,
                        },
                        timeout=10,
                    )
            except Exception:
                pass
            logger.info("Polling for next job after failure...")
            await asyncio.sleep(3)


def main() -> None:
    global _jobs_completed, _current_job_id

    logger.info("=== RenderAgent Worker Starting ===")

    python_cmd = "python" if sys.platform == "win32" else "python3"

    try:
        result = subprocess.run(
            [python_cmd, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Playwright Chromium installed/verified")
    except subprocess.CalledProcessError:
        logger.warning("Could not install Playwright Chromium (may already be installed)")
    except FileNotFoundError:
        logger.warning("Playwright not found in PATH")

    config = Config()

    if not config.is_complete():
        logger.info("Config incomplete — launching setup wizard...")
        from worker.setup_wizard import run_wizard

        wizard_data = run_wizard()
        for key, value in wizard_data.items():
            if value:
                config.set(key, str(value))
        logger.info("Setup complete")

    worker_id = socket.gethostname()

    controller_url = config.get("controller_url")
    if not controller_url:
        try:
            udp_port_val = config.get("udp_port")
            udp_port = int(udp_port_val) if udp_port_val else 8766
            controller_url = discover_controller(udp_port=udp_port, timeout_s=10)
            config.set("controller_url", controller_url)
            logger.info(f"Controller URL saved to config: {controller_url}")
        except TimeoutError:
            logger.error("Could not discover controller on local network")
            sys.exit(1)

    heartbeat_interval = 10
    try:
        heartbeat_interval = int(config.get("heartbeat_interval") or 10)
    except Exception:
        pass

    def heartbeat_loop():
        while True:
            send_heartbeat(
                controller_url=controller_url,
                worker_id=worker_id,
                jobs_completed=_jobs_completed,
                current_job_id=_current_job_id,
            )
            time.sleep(heartbeat_interval)

    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    hb_thread.start()
    logger.info("Heartbeat thread started")

    logger.info(f"Worker {worker_id} started. Polling {controller_url}")

    asyncio.run(poll_loop(controller_url, worker_id, config.get_all()))


if __name__ == "__main__":
    main()

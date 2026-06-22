# ===== worker/service.py =====

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.logger import get_logger

logger = get_logger("worker_service")

WINDOWS_SERVICE_AVAILABLE = False

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager

    WINDOWS_SERVICE_AVAILABLE = True
except ImportError:
    pass


if WINDOWS_SERVICE_AVAILABLE:

    class RenderAgentWorkerService(win32serviceutil.ServiceFramework):
        _svc_name_ = "RenderAgentWorker"
        _svc_display_name_ = "RenderAgent Worker"
        _svc_description_ = "Distributed rendering automation worker"

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            try:
                from worker.agent import main

                main()
            except Exception:
                import traceback

                logger.error(f"Service error: {traceback.format_exc()}")
                raise

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.hWaitStop)
            logger.info("Service stop requested")


if __name__ == "__main__":
    if not WINDOWS_SERVICE_AVAILABLE:
        print("Windows Service is not available on this platform.")
        print("Run 'python worker/agent.py' directly instead.")
        sys.exit(0)
    win32serviceutil.HandleCommandLine(RenderAgentWorkerService)
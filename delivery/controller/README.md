# Controller Module

The controller is the central hub of RenderAgent. It watches a folder for incoming `.3dm` files, manages a SQLite job queue, exposes a REST API for workers, serves a React dashboard, and handles auto-discovery + auto-updates.

---

## Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point — orchestrates all controller services |
| `api.py` | FastAPI REST API — endpoints for workers and dashboard |
| `queue.py` | SQLite job queue with SQLAlchemy ORM |
| `watcher.py` | Watchdog folder watcher for `.3dm` files |
| `tray.py` | System tray icon (Windows only, skip on Mac) |
| `updater.py` | Auto-updater via GitHub Releases API |
| `setup_wizard.py` | First-run Tkinter configuration wizard |
| `service.py` | Windows Service wrapper using pywin32 |

---

## main.py — Entry Point

### Purpose

Single entry point that starts all controller subsystems. Designed to run as both a standalone script and as a Windows Service.

### Startup Sequence

1. Initialize shared logger: `logger = get_logger("controller")`
2. Load config via `shared.config`. If config is incomplete → launch `setup_wizard.py` and block until user completes it.
3. Initialize the SQLite database via `queue.init_db()`
4. Start the **folder watcher** in a background thread (`watcher.start()`)
5. Start the **UDP discovery listener** in a background thread (listen on port `8766`)
6. Start the **system tray** in a background thread (wrapped in try/except — skip silently on Mac or if pystray is not installed)
7. Start the **auto-updater** in a background thread (`updater.start_background_check()`)
8. Start the **stuck job recovery** loop in a background thread (runs every 5 minutes)
9. Start **uvicorn** on `0.0.0.0:8765` (this blocks the main thread)

### Function Signatures

```
def main() -> None
    """Entry point. Starts all services and runs uvicorn."""

def start_udp_listener(port: int) -> None
    """Listen for UDP discovery broadcasts on the given port.
    When a packet containing 'RENDERAGENT_DISCOVER' is received,
    respond with 'RENDERAGENT_CONTROLLER http://<local_ip>:8765'."""

def get_local_ip() -> str
    """Return the local network IP address of this machine."""

def start_stuck_job_recovery(interval_seconds: int = 300) -> None
    """Periodically reset stuck jobs (CLAIMED > 30 min) back to PENDING."""
```

### UDP Discovery Protocol

```
Worker sends:    b"RENDERAGENT_DISCOVER"  →  broadcast 255.255.255.255:8766
Controller:      Receives packet, responds with:
                 b"RENDERAGENT_CONTROLLER http://<controller_ip>:8765"
                 Sent back to the worker's source IP/port
```

---

## api.py — FastAPI REST API

### Purpose

FastAPI application that serves as the communication layer between the controller, workers, and dashboard. All endpoints return JSON. The React dashboard static files are served from `dashboard/dist/` at the root path `/`.

### FastAPI App Setup

```
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="RenderAgent Controller", version="1.0.0")

# Mount React dashboard static files (must be LAST, after all API routes)
app.mount("/", StaticFiles(directory="controller/dashboard/dist", html=True), name="dashboard")
```

### Endpoints

#### `GET /jobs/next?worker_id={worker_id}` — Claim Next Job

- Calls `queue.claim_next_job(worker_id)`
- Returns the claimed job as JSON, or `204 No Content` if queue is empty
- Atomic operation — two workers cannot claim the same job
- Response body:
  ```json
  {
    "id": "uuid-string",
    "file_path": "/absolute/path/to/file.3dm",
    "file_name": "file.3dm",
    "status": "CLAIMED",
    "priority": "NORMAL",
    "worker_id": "DESKTOP-PC01",
    "created_at": "2024-01-01T12:00:00",
    "retry_count": 0
  }
  ```

#### `POST /jobs/{id}/status` — Update Job Status

- Request body:
  ```json
  {
    "status": "COMPLETED",
    "output_path": "/path/to/output.mp4",
    "error_message": null
  }
  ```
- Calls `queue.update_job_status(id, status, output_path, error_message)`
- If status is `FAILED` and `retry_count < 3` → auto-reset to `PENDING` with incremented retry count
- Returns updated job JSON

#### `POST /workers/heartbeat` — Worker Heartbeat

- Request body:
  ```json
  {
    "worker_id": "DESKTOP-PC01",
    "ip": "192.168.1.50",
    "jobs_completed": 42,
    "current_job_id": "uuid-or-null"
  }
  ```
- Stores heartbeat in an in-memory dictionary with timestamp
- Returns `{"status": "ok"}`

#### `GET /workers` — List Active Workers

- Returns workers whose last heartbeat was within the last 30 seconds
- Response body:
  ```json
  [
    {
      "worker_id": "DESKTOP-PC01",
      "ip": "192.168.1.50",
      "last_seen": "2024-01-01T12:00:00",
      "jobs_completed": 42,
      "current_job_id": "uuid-or-null"
    }
  ]
  ```

#### `GET /stats` — Dashboard Statistics

- Returns aggregate statistics for the dashboard
- Response body:
  ```json
  {
    "queue_depth": 15,
    "done_today": 87,
    "failed_today": 2,
    "active_workers": 3
  }
  ```
- `queue_depth` = count of PENDING + CLAIMED + PROCESSING jobs
- `done_today` = count of COMPLETED jobs where `updated_at` is today
- `failed_today` = count of FAILED jobs where `updated_at` is today (with retry_count >= 3)
- `active_workers` = count of workers with heartbeat < 30 seconds ago

#### `GET /logs` — Recent Log Lines

- Reads the last 100 lines from `logs/render-agent.log`
- Returns:
  ```json
  {
    "lines": ["2024-01-01 12:00:00 [INFO] controller: Started", "..."]
  }
  ```

#### `GET /jobs?status={status}` — List All Jobs

- Optional query param `status` to filter (e.g., `?status=PENDING`)
- Returns list of all jobs sorted by `created_at` descending
- Response body:
  ```json
  [
    {
      "id": "uuid",
      "file_path": "/path/to/file.3dm",
      "file_name": "file.3dm",
      "status": "COMPLETED",
      "priority": "NORMAL",
      "worker_id": "DESKTOP-PC01",
      "created_at": "2024-01-01T12:00:00",
      "updated_at": "2024-01-01T12:05:00",
      "retry_count": 0,
      "error_message": null,
      "output_path": "/path/to/output.mp4"
    }
  ]
  ```

---

## queue.py — SQLite Job Queue

### Purpose

Manages the job queue using SQLite (via SQLAlchemy). Provides atomic job claiming to prevent race conditions when multiple workers poll simultaneously.

### Database Setup

- SQLite database file: `render_agent.db` (project root)
- Uses SQLAlchemy ORM with the `Job` model from `shared.models`
- Creates tables on first run via `Base.metadata.create_all()`

### Job Table Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (string) | Primary key, auto-generated `uuid4()` |
| `file_path` | String | Absolute path to the `.3dm` file |
| `file_name` | String | Base filename (e.g., `ring.3dm`) |
| `status` | Enum | `PENDING`, `CLAIMED`, `PROCESSING`, `COMPLETED`, `FAILED` |
| `priority` | Enum | `LOW`, `NORMAL`, `HIGH`, `URGENT` |
| `worker_id` | String (nullable) | ID of the worker that claimed this job |
| `created_at` | DateTime | Timestamp when job was created |
| `updated_at` | DateTime | Timestamp of last status change |
| `retry_count` | Integer | Number of retry attempts (starts at 0) |
| `error_message` | Text (nullable) | Full error traceback if job failed |
| `output_path` | String (nullable) | Path to output file after completion |

### Function Signatures

```
def init_db() -> None
    """Create SQLite database and tables if they don't exist."""

def create_job(file_path: str) -> Job
    """Create a new job from a detected .3dm file.
    Sets status=PENDING, priority=NORMAL, retry_count=0.
    file_name is extracted from file_path using os.path.basename()."""

def claim_next_job(worker_id: str) -> Optional[Job]
    """Atomically claim the next available job.
    SELECT the oldest PENDING job (ordered by priority DESC, created_at ASC),
    then UPDATE its status to CLAIMED and set worker_id.
    Both operations happen in a SINGLE TRANSACTION to prevent race conditions.
    Returns the claimed Job, or None if no jobs are available."""

def update_job_status(job_id: str, status: str, output_path: str = None, error_message: str = None) -> Job
    """Update a job's status.
    If status is FAILED:
      - If retry_count < 3: set status=PENDING, increment retry_count, clear worker_id
      - If retry_count >= 3: keep status=FAILED, store error_message
    Always updates updated_at timestamp."""

def get_all_jobs(status_filter: str = None) -> List[Job]
    """Return all jobs, optionally filtered by status.
    Ordered by created_at descending."""

def get_stats() -> dict
    """Return dictionary with:
    - queue_depth: count of PENDING + CLAIMED + PROCESSING
    - done_today: count of COMPLETED with updated_at = today
    - failed_today: count of FAILED (retry_count >= 3) with updated_at = today"""

def reset_stuck_jobs(timeout_minutes: int = 30) -> int
    """Find all jobs with status=CLAIMED where updated_at is older than
    timeout_minutes ago. Reset them to PENDING and clear worker_id.
    Returns count of reset jobs."""
```

### Atomic Job Claim — Implementation Notes

The `claim_next_job()` method MUST use `with_for_update()` (SQLite row-level locking) within a single session transaction:

```
# Pseudocode — NOT actual implementation
with Session() as session:
    job = session.query(Job)\
        .filter(Job.status == "PENDING")\
        .order_by(Job.priority.desc(), Job.created_at.asc())\
        .with_for_update()\
        .first()
    if job:
        job.status = "CLAIMED"
        job.worker_id = worker_id
        job.updated_at = datetime.utcnow()
        session.commit()
    return job
```

---

## watcher.py — Folder Watcher

### Purpose

Uses the `watchdog` library to monitor the `input_folder` (from config) for new `.3dm` files. When a new file is detected, it creates a job in the queue.

### Function Signatures

```
def start(input_folder: str) -> None
    """Start the watchdog observer on the given folder.
    Runs in the current thread (call from a background thread).
    Creates a RenderFileHandler instance and observes the folder."""

class RenderFileHandler(FileSystemEventHandler):
    def on_created(self, event) -> None
        """Called when a new file is created in the watched folder.
        - Ignore directories
        - Ignore files that don't end with .3dm (case-insensitive)
        - Wait 1 second for file to finish writing (avoid partial files)
        - Call queue.create_job(event.src_path)
        - Log: 'New file detected: {filename}'"""
```

### Behavior Details

- Only processes files with `.3dm` extension (case-insensitive: `.3DM`, `.3Dm` also match)
- Ignores all other file types silently
- Ignores directory creation events
- Waits 1 second after file detection to ensure the file has finished being written/copied
- Logs every file detection event at INFO level
- Does NOT process files that already exist when the watcher starts (only new files)

---

## tray.py — System Tray Icon

### Purpose

Adds a system tray icon on Windows for quick access to the dashboard and process control. Entirely optional — the controller runs fine without it.

### Critical Implementation Rule

**ALL code must be wrapped in try/except.** This module must NEVER crash the controller, even if pystray is not installed or the system doesn't support tray icons (e.g., headless Linux, macOS).

### Function Signatures

```
def start_tray() -> None
    """Start the system tray icon.
    Import pystray INSIDE this function within a try/except.
    If import fails → log warning and return silently.
    
    Menu items:
    - 'Open Dashboard' → opens http://localhost:8765 in default browser
    - 'Pause Queue' / 'Resume Queue' → toggle (sets a global flag)
    - 'Quit' → graceful shutdown of entire controller
    
    Icon: Use a simple colored square created with Pillow (no external icon file)."""
```

### Menu Structure

```
RenderAgent (tray icon)
├── Open Dashboard     → webbrowser.open("http://localhost:8765")
├── ──────────────
├── Pause Queue        → Toggle. Changes to "Resume Queue" when paused.
├── ──────────────
└── Quit               → Calls os._exit(0) for clean shutdown
```

---

## updater.py — Auto-Updater

### Purpose

Periodically checks GitHub Releases for a newer version. If found, downloads the new executable, replaces the current one, and restarts the process.

### Function Signatures

```
def start_background_check(interval_seconds: int = 3600) -> None
    """Start a background thread that calls check_for_update() every interval_seconds."""

def check_for_update() -> bool
    """Check GitHub Releases API for a newer version.
    1. Read current version from build/version.json
    2. GET https://api.github.com/repos/{owner}/{repo}/releases/latest
    3. Compare version strings (semver)
    4. If remote version > local version:
       a. Download new .exe from the release assets
       b. Replace current executable
       c. Log: 'Updated from v{old} to v{new}. Restarting...'
       d. Restart the process using os.execv()
    5. Return True if updated, False otherwise."""

def get_current_version() -> str
    """Read version string from build/version.json."""
```

### version.json Location

The updater reads `build/version.json` to determine the current version:

```json
{
  "version": "1.0.0",
  "controller_url": "https://github.com/yourrepo/releases/download/v1.0.0/controller.exe",
  "worker_url": "https://github.com/yourrepo/releases/download/v1.0.0/worker.exe"
}
```

---

## setup_wizard.py — First-Run Configuration

### Purpose

A Tkinter GUI wizard that runs on first launch (when `config.json` is missing or incomplete). Collects essential configuration from the user and saves it.

### Function Signatures

```
def run_wizard() -> dict
    """Display the Tkinter setup wizard window.
    Block until user fills in all fields and clicks Submit.
    Return the config dictionary.
    
    Fields:
    - ijewel Email:    Text input
    - ijewel Password: Password input (masked)
    - Input Folder:    Text input + 'Browse' button (opens folder dialog)
    - Output Folder:   Text input + 'Browse' button (opens folder dialog)
    
    Validation:
    - All fields required
    - Email must contain '@'
    - Folders must exist or be creatable
    
    On Submit:
    - Save all values to config.json via shared.config
    - Close the window
    - Return config dict"""

def is_config_complete() -> bool
    """Check if config.json exists and has all required fields filled.
    Required fields: ijewel_email, ijewel_password, input_folder, output_folder."""
```

### UI Layout

```
┌─────────────────────────────────────────┐
│         RenderAgent Setup               │
│                                         │
│  ijewel Email:    [___________________] │
│  ijewel Password: [___________________] │
│                                         │
│  Input Folder:    [_______________] [📁]│
│  Output Folder:   [_______________] [📁]│
│                                         │
│              [ Save & Start ]           │
└─────────────────────────────────────────┘
```

---

## service.py — Windows Service Wrapper

### Purpose

Wraps the controller as a Windows Service so it can start automatically on boot and run in the background without a console window.

### Critical Implementation Rule

**ALL `win32` imports must be inside try/except.** This file must be importable on Mac/Linux without crashing.

### Function Signatures

```
class RenderAgentControllerService:
    """Windows Service class.
    
    Service Name: 'RenderAgentController'
    Display Name: 'RenderAgent Controller'
    Description: 'Distributed rendering job queue controller'
    
    Methods:
    - SvcDoRun():  Called when service starts. Calls main.main()
    - SvcStop():   Called when service stops. Sets stop event.
    
    Usage:
    - python service.py install    → Install the service
    - python service.py start      → Start the service
    - python service.py stop       → Stop the service
    - python service.py remove     → Uninstall the service
    """
```

### Platform Guard

```
# At the top of service.py:
try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    WINDOWS_SERVICE_AVAILABLE = True
except ImportError:
    WINDOWS_SERVICE_AVAILABLE = False

# In __main__:
if __name__ == '__main__':
    if not WINDOWS_SERVICE_AVAILABLE:
        print("Windows Service is not available on this platform.")
        print("Run 'python controller/main.py' directly instead.")
        sys.exit(0)
    win32serviceutil.HandleCommandLine(RenderAgentControllerService)
```

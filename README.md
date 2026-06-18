# RenderAgent — Distributed 3D Rendering Automation System

RenderAgent is a distributed rendering automation system that watches a folder for `.3dm` (Rhino 3D) files, queues them for processing, and dispatches jobs to worker machines that use Playwright to automate [ijewel.design](https://ijewel.design) — uploading each file, triggering a render, and downloading the resulting MP4/JPG output. It consists of a **Controller PC** (job queue manager + web dashboard) and one or more **Worker PCs** (headless browser automation agents), communicating over REST API with automatic UDP-based discovery. The entire system is delivered as simple Python scripts that run on both Mac and Windows.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CONTROLLER PC                               │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────────────────┐ │
│  │  watcher.py  │   │   queue.py   │   │       api.py            │ │
│  │  (watchdog)  │──▶│  (SQLite +   │◀──│  (FastAPI + Uvicorn)    │ │
│  │              │   │  SQLAlchemy) │   │  Port 8765              │ │
│  │ Watch input/ │   │              │   │                         │ │
│  │ for .3dm     │   │  Job Queue   │   │  REST endpoints for     │ │
│  └──────────────┘   └──────────────┘   │  workers & dashboard    │ │
│                                         └────────┬────────────────┘ │
│  ┌──────────────┐   ┌──────────────┐             │                  │
│  │  tray.py     │   │ updater.py   │             │  Serves React    │
│  │  (pystray)   │   │ (GitHub API) │             │  dashboard at /  │
│  │  System tray │   │ Auto-update  │             │                  │
│  └──────────────┘   └──────────────┘   ┌─────────▼────────────────┐ │
│                                         │  dashboard/ (React SPA) │ │
│  ┌──────────────┐   ┌──────────────┐   │  Vite + Tailwind        │ │
│  │ service.py   │   │setup_wizard  │   │  Queue & Workers pages  │ │
│  │ (Win Svc)    │   │  (Tkinter)   │   └─────────────────────────┘ │
│  └──────────────┘   └──────────────┘                                │
│                                                                     │
│  UDP Discovery Listener ◀─── port 8766 ───────────────┐            │
└─────────────────────────────────────────────────────────┼────────────┘
                                                          │
                    ┌─────────────────────────────────────┘
                    │  UDP Broadcast "RENDERAGENT_DISCOVER"
                    │
         ┌──────────▼──────────────────────────────────────────────┐
         │                     WORKER PC(s)                        │
         │                                                         │
         │  ┌──────────────┐   ┌──────────────────────────────┐   │
         │  │  agent.py    │   │  ijewel_automation.py         │   │
         │  │              │   │                                │   │
         │  │ Poll GET     │──▶│  Playwright (Chromium)         │   │
         │  │ /jobs/next   │   │                                │   │
         │  │              │   │  1. Check login                │   │
         │  │ Heartbeat    │   │  2. Login if needed            │   │
         │  │ every 10s    │   │  3. Open upload modal          │   │
         │  │              │   │  4. Upload .3dm file           │   │
         │  └──────────────┘   │  5. Trigger render             │   │
         │                      │  6. Download MP4/JPG           │   │
         │  ┌──────────────┐   └──────────────────────────────┘   │
         │  │ service.py   │                                       │
         │  │ (Win Svc)    │   ┌──────────────┐                   │
         │  └──────────────┘   │setup_wizard  │                   │
         │                      │ (Tkinter)    │                   │
         │                      └──────────────┘                   │
         └─────────────────────────────────────────────────────────┘

         ┌─────────────────────────────────────────────────────────┐
         │                    SHARED MODULE                        │
         │                                                         │
         │  config.py   — Fernet-encrypted config management       │
         │  models.py   — SQLAlchemy + Pydantic models             │
         │  logger.py   — Rotating file + colored console logging  │
         └─────────────────────────────────────────────────────────┘
```

---

## Communication Model

### REST API (Primary)

All controller–worker communication happens over HTTP REST API on port **8765**.

| Direction | Method | Endpoint | Purpose |
|-----------|--------|----------|---------|
| Worker → Controller | `GET` | `/jobs/next?worker_id=X` | Claim the next pending job atomically |
| Worker → Controller | `POST` | `/jobs/{id}/status` | Update job status (PROCESSING, COMPLETED, FAILED) |
| Worker → Controller | `POST` | `/workers/heartbeat` | Send heartbeat with worker metadata |
| Dashboard → Controller | `GET` | `/workers` | List active workers (last seen < 30s) |
| Dashboard → Controller | `GET` | `/stats` | Queue depth, done today, failed today, active workers |
| Dashboard → Controller | `GET` | `/logs` | Last 100 log lines |
| Dashboard → Controller | `GET` | `/jobs` | All jobs with optional `?status=` filter |
| Dashboard → Controller | `GET` | `/` | Serve React dashboard static files |

### UDP Discovery (Automatic Setup)

Workers that don't have a `controller_url` in their config will broadcast a UDP packet on port **8766** to discover the controller automatically.

1. Worker sends UDP broadcast: `RENDERAGENT_DISCOVER` → `255.255.255.255:8766`
2. Controller listens on port `8766`, responds with: `RENDERAGENT_CONTROLLER http://<ip>:8765`
3. Worker parses the response and saves `controller_url` to config

This eliminates the need for manual IP configuration on a local network.

---

## Complete Folder Structure

```
render-agent/
├── README.md                              # This file — project overview and architecture
├── config.json                            # (Generated) Encrypted configuration file
├── .key                                   # (Generated) Fernet encryption key — NEVER commit
│
├── controller/
│   ├── README.md                          # Controller module documentation
│   ├── main.py                            # Entry point — starts all controller services
│   ├── api.py                             # FastAPI REST API with all endpoints
│   ├── queue.py                           # SQLite job queue with SQLAlchemy ORM
│   ├── watcher.py                         # Watchdog folder watcher for .3dm files
│   ├── tray.py                            # System tray icon (pystray, Windows only)
│   ├── updater.py                         # Auto-updater via GitHub Releases API
│   ├── setup_wizard.py                    # First-run Tkinter config wizard
│   ├── service.py                         # Windows Service wrapper (pywin32)
│   └── dashboard/
│       ├── README.md                      # Dashboard module documentation
│       ├── package.json                   # Node dependencies (React, Vite, Tailwind)
│       ├── vite.config.js                 # Vite build configuration
│       ├── tailwind.config.js             # Tailwind CSS configuration
│       ├── index.html                     # SPA entry HTML
│       ├── dist/                          # (Generated) Production build served by FastAPI
│       └── src/
│           ├── main.jsx                   # React app entry point
│           ├── App.jsx                    # Router — Queue and Workers pages
│           ├── index.css                  # Tailwind base imports
│           └── components/
│               ├── README.md              # Component documentation
│               ├── StatsBar.jsx           # 4-card stats display (queue, done, failed, workers)
│               ├── JobCard.jsx            # Single job display with status badge
│               ├── QueuePage.jsx          # Full queue view with filters
│               ├── WorkersPage.jsx        # Active workers list
│               └── LogDrawer.jsx          # Slide-in log viewer
│
├── worker/
│   ├── README.md                          # Worker module documentation
│   ├── agent.py                           # Worker main loop — poll, process, heartbeat
│   ├── ijewel_automation.py               # Playwright automation for ijewel.design
│   ├── setup_wizard.py                    # First-run Tkinter config wizard
│   └── service.py                         # Windows Service wrapper (pywin32)
│
├── shared/
│   ├── README.md                          # Shared module documentation
│   ├── config.py                          # Fernet-encrypted config management
│   ├── models.py                          # SQLAlchemy + Pydantic models
│   └── logger.py                          # Rotating file + colored console logging
│
├── build/
│   ├── README.md                          # Build system documentation
│   ├── build_windows.bat                  # Windows build script
│   ├── version.json                       # Version info for auto-updater
│   ├── requirements-controller.txt        # Controller Python dependencies
│   └── requirements-worker.txt            # Worker Python dependencies
│
└── logs/                                  # (Generated) Log files directory
    └── render-agent.log                   # Rotating log file (10MB max, 5 backups)
```

---

## How to Run — Mac

### Prerequisites

```bash
# Install Python 3.10+
brew install python@3.10

# Install Node.js 18+
brew install node@18

# Verify versions
python3 --version    # Must be 3.10+
node --version       # Must be 18+
npm --version
```

### Run Controller (Mac)

```bash
# Clone the project
git clone https://github.com/yourrepo/render-agent.git
cd render-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install controller dependencies
pip install -r build/requirements-controller.txt

# Build the dashboard
cd controller/dashboard
npm install
npm run build
cd ../..

# Run the controller (first run will open setup wizard)
python3 controller/main.py
```

### Run Worker (Mac)

```bash
cd render-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install worker dependencies
pip install -r build/requirements-worker.txt

# Install Playwright Chromium
python3 -m playwright install chromium

# Run the worker (first run will open setup wizard)
python3 worker/agent.py
```

---

## How to Run — Windows

### Prerequisites

```cmd
REM Download and install Python 3.10+ from https://www.python.org/downloads/
REM Download and install Node.js 18+ from https://nodejs.org/
REM Ensure both are added to PATH during installation

python --version    & REM Must be 3.10+
node --version      & REM Must be 18+
npm --version
```

### Run Controller (Windows)

```cmd
REM Clone the project
git clone https://github.com/yourrepo/render-agent.git
cd render-agent

REM Create virtual environment
python -m venv venv
venv\Scripts\activate

REM Install controller dependencies
pip install -r build\requirements-controller.txt

REM Build the dashboard
cd controller\dashboard
npm install
npm run build
cd ..\..

REM Run the controller (first run will open setup wizard)
python controller\main.py

REM OR install as Windows Service:
python controller\service.py install
python controller\service.py start
```

### Run Worker (Windows)

```cmd
cd render-agent

REM Create virtual environment
python -m venv venv
venv\Scripts\activate

REM Install worker dependencies
pip install -r build\requirements-worker.txt

REM Install Playwright Chromium
python -m playwright install chromium

REM Run the worker (first run will open setup wizard)
python worker\agent.py

REM OR install as Windows Service:
python worker\service.py install
python worker\service.py start
```

---

## Full Job Flow

This is the complete lifecycle of a single render job, from dropping a `.3dm` file to downloading the final MP4:

```
 USER DROPS FILE                    CONTROLLER                           WORKER
 ══════════════                     ══════════                           ══════

 1. User places                 2. watcher.py detects
    "ring.3dm"                     new .3dm file via
    into input_folder/             watchdog inotify
                                        │
                                        ▼
                                3. queue.create_job()
                                   inserts row into SQLite:
                                   status=PENDING
                                   priority=NORMAL
                                   retry_count=0
                                        │
                                        ▼
                                4. Job sits in queue
                                   waiting to be claimed
                                                                   5. agent.py polls
                                                                      GET /jobs/next?worker_id=PC-01
                                                                           │
                                                                           ▼
                                6. api.py calls                    ◀── HTTP Request
                                   queue.claim_next_job()
                                   Atomic: SELECT + UPDATE
                                   status → CLAIMED
                                   worker_id → PC-01
                                        │
                                        ▼
                                7. Returns job JSON ──────────────▶ 8. Worker receives job
                                   {id, file_path, file_name}            │
                                                                          ▼
                                                                   9. Worker POSTs
                                                                      status=PROCESSING
                                                                           │
                                                                           ▼
                                                                  10. ijewel_automation.run()
                                                                      │
                                                                      ├─ Check login status
                                                                      ├─ Login if needed
                                                                      ├─ Open upload modal
                                                                      ├─ Upload ring.3dm
                                                                      ├─ Fill title "ring"
                                                                      ├─ Click UPLOAD
                                                                      ├─ Wait for render
                                                                      │  (up to 20 minutes)
                                                                      └─ Download MP4/JPG
                                                                           │
                                                                           ▼
                                                                  11. Save to output_folder/
                                                                      ring.mp4
                                                                           │
                                                                           ▼
                               12. Worker POSTs               ◀── 13. POST /jobs/{id}/status
                                   status=COMPLETED                    {status: COMPLETED,
                                   output_path saved                    output_path: ring.mp4}

                               ── ON FAILURE ──
                               14. Worker POSTs                ◀── POST /jobs/{id}/status
                                   status=FAILED                    {status: FAILED,
                                   error_message saved                error: "full traceback"}
                                        │
                                        ▼
                               15. queue checks retry_count
                                   If retry_count < 3:
                                     status → PENDING
                                     retry_count += 1
                                   If retry_count >= 3:
                                     status stays FAILED

                               ── STUCK JOB RECOVERY ──
                               16. Periodic check:
                                   Jobs with status=CLAIMED
                                   and updated_at > 30 min ago
                                   → Reset to PENDING
```

---

## Config File Structure — `config.json`

The config file is stored at the project root. All sensitive values are encrypted with Fernet symmetric encryption. The `.key` file (auto-generated on first run) must be kept alongside `config.json`.

```json
{
  "controller_url": "http://192.168.1.100:8765",
  "input_folder": "/path/to/watch/folder",
  "output_folder": "/path/to/output/folder",
  "ijewel_email": "user@example.com",
  "ijewel_password": "encrypted_value_here",
  "worker_id": "DESKTOP-PC01",
  "port": 8765,
  "udp_port": 8766,
  "heartbeat_interval": 10,
  "poll_interval": 5,
  "max_retries": 3,
  "stuck_job_timeout_minutes": 30,
  "auto_update": true,
  "log_level": "INFO"
}
```

| Field | Type | Used By | Description |
|-------|------|---------|-------------|
| `controller_url` | string | Worker | Full URL of the controller API (e.g. `http://192.168.1.100:8765`). If empty, worker uses UDP discovery. |
| `input_folder` | string | Controller | Absolute path to the folder watched for incoming `.3dm` files. |
| `output_folder` | string | Worker | Absolute path where rendered MP4/JPG files are saved. |
| `ijewel_email` | string | Worker | Login email for ijewel.design. Stored encrypted. |
| `ijewel_password` | string | Worker | Login password for ijewel.design. Stored encrypted. |
| `worker_id` | string | Worker | Unique identifier for this worker (defaults to `socket.gethostname()`). |
| `port` | int | Controller | HTTP port for the FastAPI server. Default: `8765`. |
| `udp_port` | int | Both | UDP port for auto-discovery broadcasts. Default: `8766`. |
| `heartbeat_interval` | int | Worker | Seconds between heartbeat pings to controller. Default: `10`. |
| `poll_interval` | int | Worker | Seconds between polling for new jobs. Default: `5`. |
| `max_retries` | int | Controller | Maximum retry attempts for failed jobs before permanent failure. Default: `3`. |
| `stuck_job_timeout_minutes` | int | Controller | Minutes after which a CLAIMED job is reset to PENDING. Default: `30`. |
| `auto_update` | bool | Both | Whether to check GitHub Releases for updates. Default: `true`. |
| `log_level` | string | Both | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`. Default: `INFO`. |

---

## Environment Requirements

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.10+ | Core runtime for controller and worker scripts |
| Node.js | 18+ | Build the React dashboard |
| npm | 9+ | Install dashboard dependencies |
| Playwright | Latest | Browser automation on worker PCs |
| Chromium | (via Playwright) | Headless browser used by workers |

### Python Packages — Controller

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy>=2.0.0
watchdog>=3.0.0
pystray>=0.19.0       # Windows only — wrapped in try/except
Pillow>=10.0.0        # Required by pystray for icon
pywin32>=306           # Windows only — wrapped in try/except
cryptography>=41.0.0  # Fernet encryption
requests>=2.31.0      # Auto-updater HTTP calls
pydantic>=2.5.0
```

### Python Packages — Worker

```
playwright>=1.40.0
cryptography>=41.0.0
requests>=2.31.0
pywin32>=306           # Windows only — wrapped in try/except
pydantic>=2.5.0
```

### Node Packages — Dashboard

```
react ^18
react-dom ^18
react-router-dom ^6
vite ^5
@vitejs/plugin-react ^4
tailwindcss ^3
autoprefixer ^10
postcss ^8
```

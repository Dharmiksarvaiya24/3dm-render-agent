# Worker Module

The worker is a headless automation agent that polls the controller for render jobs, uses Playwright to automate [ijewel.design](https://ijewel.design), and downloads the rendered output (MP4/JPG). Multiple workers can run in parallel across different machines.

---

## Files

| File | Purpose |
|------|---------|
| `agent.py` | Main worker loop — polling, heartbeat, job dispatch |
| `ijewel_automation.py` | Playwright browser automation for ijewel.design |
| `setup_wizard.py` | First-run Tkinter configuration wizard |
| `service.py` | Windows Service wrapper using pywin32 |

---

## agent.py — Worker Main Loop

### Purpose

The main entry point for worker machines. Handles controller discovery, job polling, heartbeat sending, and error recovery.

### Startup Sequence

1. Initialize logger: `logger = get_logger("worker")`
2. Check if Playwright Chromium is installed — if not, install it:
   ```
   subprocess.run(["python3", "-m", "playwright", "install", "chromium"], check=True)
   ```
   On Windows, use `"python"` instead of `"python3"`.
3. Load config via `shared.config`
4. If config is incomplete → launch `setup_wizard.run_wizard()` and block until complete
5. Set `worker_id = socket.gethostname()`
6. If `controller_url` not in config → run UDP discovery to find the controller
7. Start **heartbeat thread** (sends heartbeat every 10 seconds)
8. Enter **main polling loop**

### Main Polling Loop

```
while True:
    try:
        response = requests.get(f"{controller_url}/jobs/next?worker_id={worker_id}")
        
        if response.status_code == 204:
            # No jobs available
            time.sleep(poll_interval)  # Default: 5 seconds
            continue
        
        job = response.json()
        logger.info(f"Claimed job: {job['file_name']} (ID: {job['id']})")
        
        # Update status to PROCESSING
        requests.post(f"{controller_url}/jobs/{job['id']}/status", json={
            "status": "PROCESSING"
        })
        
        # Run Playwright automation
        success = await ijewel_automation.run(
            file_path=job['file_path'],
            output_folder=config.get('output_folder'),
            email=config.get('ijewel_email'),
            password=config.get('ijewel_password')
        )
        
        # Report success
        requests.post(f"{controller_url}/jobs/{job['id']}/status", json={
            "status": "COMPLETED",
            "output_path": output_path
        })
        
    except Exception as e:
        # ALWAYS print full traceback — NEVER hide errors
        logger.error(f"Job failed: {traceback.format_exc()}")
        requests.post(f"{controller_url}/jobs/{job['id']}/status", json={
            "status": "FAILED",
            "error_message": traceback.format_exc()
        })
        time.sleep(min(backoff, 10))  # Max backoff = 10 seconds
```

### Function Signatures

```
def main() -> None
    """Entry point. Runs startup sequence then enters polling loop."""

async def process_job(job: dict, config: dict) -> str
    """Process a single job. Calls ijewel_automation.run().
    Returns the output file path on success.
    Raises Exception with full traceback on failure."""

def send_heartbeat(controller_url: str, worker_id: str, jobs_completed: int, current_job_id: str = None) -> None
    """Send heartbeat to controller. Called every 10 seconds from a background thread.
    POST /workers/heartbeat with:
    {
        'worker_id': worker_id,
        'ip': get_local_ip(),
        'jobs_completed': jobs_completed,
        'current_job_id': current_job_id
    }
    Silently catch and log any connection errors."""

def discover_controller(udp_port: int = 8766, timeout: int = 10) -> str
    """Broadcast UDP discovery packet and wait for controller response.
    Send b'RENDERAGENT_DISCOVER' to 255.255.255.255:8766.
    Wait up to timeout seconds for response.
    Parse response: 'RENDERAGENT_CONTROLLER http://<ip>:<port>'
    Return the controller URL string.
    Raise TimeoutError if no response received."""

def get_local_ip() -> str
    """Return the local network IP address of this machine."""
```

### Windows Compatibility

- Wrap `import msvcrt` and any Windows-specific imports in try/except
- Use `sys.platform == 'win32'` checks where behavior differs
- On Windows, use `"python"` for subprocess calls; on Mac, use `"python3"`

---

## ijewel_automation.py — Playwright Automation

### Purpose

Automates the entire ijewel.design workflow: login → upload → render → download. Uses a persistent browser context to maintain login sessions across jobs.

### Public Interface

```
async def run(file_path: str, output_folder: str, email: str, password: str) -> bool
    """Execute the full ijewel.design automation flow.
    
    Args:
        file_path:     Absolute path to the .3dm file to upload
        output_folder: Absolute path to save downloaded MP4/JPG
        email:         ijewel.design login email
        password:      ijewel.design login password
    
    Returns:
        True on success
    
    Raises:
        Exception with descriptive message on any failure
    """
```

### Browser Context Setup

Use a **persistent browser context** to keep the login session alive across multiple jobs. NEVER relaunch the browser for each job.

```
# ONE-TIME setup (module level or singleton)
playwright = await async_playwright().start()
browser_context = await playwright.chromium.launch_persistent_context(
    user_data_dir="./browser_session",
    headless=True,
    viewport={"width": 1920, "height": 1080},
    accept_downloads=True
)
page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()
```

The `./browser_session` directory stores cookies and session data so the user stays logged in between runs.

---

### EXACT PLAYWRIGHT FLOW

Each step must be implemented exactly as specified below. These selectors are specific to the ijewel.design website and must not be changed.

---

#### Step 1 — CHECK LOGIN STATUS

Check if the user is already logged in by looking for the upload button on the homepage.

```python
logger.info("Checking login status...")

await page.goto('https://ijewel.design')
await page.wait_for_load_state('networkidle')
await page.wait_for_timeout(2000)

# Look for the upload button in the header
btn = await page.query_selector(
    '#__next > div > div:nth-of-type(2) > header > div:nth-of-type(2) > div:nth-of-type(2) > button:nth-of-type(1)'
)

if btn:
    logger.info("Already logged in")
    # Skip to Step 3
else:
    logger.info("Not logged in — proceeding to login")
    # Continue to Step 2
```

---

#### Step 2 — LOGIN (only if not logged in)

Navigate to the login page, fill in credentials, and submit.

```python
logger.info("Logging in...")

await page.goto('https://ijewel.design/login?redirect=/')
await page.wait_for_load_state('networkidle')
await page.wait_for_timeout(2000)

# Fill email
await page.get_by_placeholder('Enter your email').fill(email)
await page.wait_for_timeout(500)

# Fill password
await page.get_by_placeholder('Enter your password').fill(password)
await page.wait_for_timeout(500)

# Click login button
await page.get_by_role('button', name='Log in').click()
await page.wait_for_load_state('networkidle')
await page.wait_for_timeout(3000)

# Verify login succeeded
if '/login' in page.url:
    raise Exception('Login failed — check credentials in config.json')

logger.info("Login successful")
```

---

#### Step 3 — OPEN UPLOAD MODAL

Navigate to the homepage and open the upload dialog.

```python
logger.info("Opening upload modal...")

await page.goto('https://ijewel.design')
await page.wait_for_load_state('networkidle')
await page.wait_for_timeout(2000)

# Click the upload button SVG icon in the header
await page.locator(
    '#__next > div > div:nth-of-type(2) > header > div:nth-of-type(2) > div:nth-of-type(2) > button:nth-of-type(1) > svg'
).click()

# Wait for upload modal to appear
await page.wait_for_selector('section[role="dialog"]', timeout=15000)

logger.info("Upload modal opened")
```

---

#### Step 4 — UPLOAD FILE

Upload the `.3dm` file via the modal dialog.

```python
logger.info(f"Uploading file: {file_path}")

# Extract filename without extension for the title
filename_without_extension = os.path.splitext(os.path.basename(file_path))[0]

# Click the file input area to prepare for upload
await page.locator(
    '#:R3996H2: > div > div:nth-of-type(2) > div:nth-of-type(1) > label > div > p'
).click()

# Set the file input to the .3dm file
await page.locator('#file').set_input_files(file_path)

# Fill in the title field
await page.get_by_placeholder('Title (required)').fill(filename_without_extension)

# Wait for the UPLOAD button to become enabled
await page.wait_for_selector(
    'button:not([disabled])[class*="bg-primary"]',
    timeout=15000
)

# Click UPLOAD
await page.get_by_role('button', name='UPLOAD').click()

# Wait for modal to close (indicates upload is complete)
await page.wait_for_selector(
    'section[role="dialog"]',
    state='hidden',
    timeout=60000
)

logger.info("Upload complete")
```

---

#### Step 5 — RENDER & DOWNLOAD

Wait for the render to complete (can take up to 20 minutes) and download the output.

```python
logger.info("Waiting for render... (up to 20 min)")

await page.wait_for_load_state('networkidle')
await page.wait_for_timeout(3000)

# Click the export/render tab
await page.locator(
    '#react-aria9249711144-:r1p:-tab-export > div > div > div > svg > path'
).click()

# Wait for the download button to appear (up to 20 minutes = 1,200,000 ms)
await page.wait_for_selector(
    '[name="Download .mp4"]',
    timeout=1200000
)

# Set up download handler BEFORE clicking download
async with page.expect_download() as download_info:
    await page.locator('[name="Download .mp4"]').click()

download = await download_info.value

# Save the downloaded file to the output folder
output_filename = filename_without_extension + ".mp4"
output_path = os.path.join(output_folder, output_filename)
await download.save_as(output_path)

logger.info(f"Download complete. Saved to: {output_path}")
```

---

### Required Logging

The following log messages MUST appear at the corresponding steps:

| Step | Log Message |
|------|-------------|
| 1 | `logger.info("Checking login status...")` |
| 1 (logged in) | `logger.info("Already logged in")` |
| 2 (start) | `logger.info("Logging in...")` |
| 2 (success) | `logger.info("Login successful")` |
| 3 | `logger.info("Opening upload modal...")` |
| 4 (start) | `logger.info(f"Uploading file: {file_path}")` |
| 4 (done) | `logger.info("Upload complete")` |
| 5 (start) | `logger.info("Waiting for render... (up to 20 min)")` |
| 5 (done) | `logger.info(f"Download complete. Saved to: {output_path}")` |

### Error Handling

- Every step must be wrapped in try/except
- On ANY exception: log the FULL traceback using `traceback.format_exc()`
- Take a screenshot on failure for debugging:
  ```python
  await page.screenshot(path=f"error_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
  ```
- Re-raise the exception so `agent.py` can report it to the controller

---

## setup_wizard.py — Worker Configuration

### Purpose

A Tkinter GUI wizard that runs on first launch to configure the worker.

### Function Signatures

```
def run_wizard() -> dict
    """Display the Tkinter setup wizard.
    
    Fields:
    - Controller URL:    Text input (or leave blank for auto-discover)
    - Auto-Discover:     Checkbox — if checked, use UDP discovery
    - Output Folder:     Text input + 'Browse' button (folder dialog)
    
    On Submit:
    - Save to config.json via shared.config
    - Return config dict"""
```

### UI Layout

```
┌─────────────────────────────────────────┐
│       RenderAgent Worker Setup          │
│                                         │
│  Controller URL: [___________________]  │
│  ☑ Auto-discover on local network       │
│                                         │
│  Output Folder:  [_______________] [📁] │
│                                         │
│              [ Save & Start ]           │
└─────────────────────────────────────────┘
```

- When "Auto-discover" is checked, the Controller URL field is disabled/grayed out
- Output Folder browse button opens a native folder picker dialog

---

## service.py — Windows Service Wrapper

### Purpose

Wraps the worker as a Windows Service for automatic startup and background operation.

### Critical Implementation Rule

**ALL `win32` imports must be inside try/except.**

### Function Signatures

```
class RenderAgentWorkerService:
    """Windows Service class.
    
    Service Name: 'RenderAgentWorker'
    Display Name: 'RenderAgent Worker'
    Description: 'Distributed rendering automation worker'
    
    Methods:
    - SvcDoRun():  Called when service starts. Calls agent.main()
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
try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    WINDOWS_SERVICE_AVAILABLE = True
except ImportError:
    WINDOWS_SERVICE_AVAILABLE = False

if __name__ == '__main__':
    if not WINDOWS_SERVICE_AVAILABLE:
        print("Windows Service is not available on this platform.")
        print("Run 'python worker/agent.py' directly instead.")
        sys.exit(0)
    win32serviceutil.HandleCommandLine(RenderAgentWorkerService)
```

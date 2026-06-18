# Shared Module

Common utilities used by both the controller and worker. This module provides encrypted configuration management, data models, and logging infrastructure.

---

## Files

| File | Purpose |
|------|---------|
| `config.py` | Fernet-encrypted configuration management |
| `models.py` | SQLAlchemy ORM + Pydantic data models |
| `logger.py` | Rotating file + colored console logging |

---

## config.py — Encrypted Configuration

### Purpose

Manages application configuration stored in an encrypted JSON file. Uses **Fernet symmetric encryption** from the `cryptography` library to protect sensitive values (passwords, API keys) at rest.

### File Layout

```
render-agent/
├── config.json     ← Encrypted configuration values
├── .key            ← Fernet encryption key (NEVER commit to git)
└── .gitignore      ← Must include: .key, config.json, *.db, browser_session/
```

### Encryption Details

- **Algorithm**: Fernet (AES-128-CBC with HMAC-SHA256)
- **Key file**: `.key` at project root — contains a single Fernet key string
- **Config file**: `config.json` at project root — values are Fernet-encrypted strings
- The `.key` file is generated automatically on first run if it doesn't exist
- The key MUST NOT be stored inside `config.json` — it's always in a separate `.key` file

### Config Fields

| Field | Type | Used By | Sensitive | Description |
|-------|------|---------|-----------|-------------|
| `controller_url` | string | Worker | No | Controller API URL (e.g., `http://192.168.1.100:8765`) |
| `input_folder` | string | Controller | No | Folder path watched for .3dm files |
| `output_folder` | string | Worker | No | Folder path for downloaded renders |
| `ijewel_email` | string | Worker | **Yes** | Login email for ijewel.design |
| `ijewel_password` | string | Worker | **Yes** | Login password for ijewel.design |
| `worker_id` | string | Worker | No | Unique worker identifier |

### Function Signatures

```
class Config:
    def __init__(self, config_path: str = "config.json", key_path: str = ".key"):
        """Initialize config manager.
        If key_path doesn't exist → generate new Fernet key and save it.
        If config_path doesn't exist → create empty config.json."""

    def get(self, key: str) -> str | None:
        """Get a decrypted config value by key.
        Read config.json, find the key, decrypt the value with Fernet.
        Return None if key doesn't exist."""

    def set(self, key: str, value: str) -> None:
        """Set an encrypted config value.
        Encrypt the value with Fernet, save to config.json.
        Create config.json if it doesn't exist."""

    def get_all(self) -> dict:
        """Return all config values as a decrypted dictionary.
        Read config.json, decrypt every value, return as dict."""

    def is_complete(self) -> bool:
        """Check if all required fields have non-empty values.
        Required fields depend on role:
        - Controller: input_folder
        - Worker: output_folder, ijewel_email, ijewel_password
        Return True only if ALL required fields are present and non-empty."""

    def _load_key(self) -> bytes:
        """Load the Fernet key from the .key file."""

    def _generate_key(self) -> bytes:
        """Generate a new Fernet key, save to .key file, return it."""

    def _encrypt(self, value: str) -> str:
        """Encrypt a string value using Fernet. Return base64-encoded string."""

    def _decrypt(self, token: str) -> str:
        """Decrypt a Fernet token back to the original string."""
```

### First Run Behavior

```
1. Config.__init__() called
2. Check if .key exists
   ├─ No  → Generate Fernet key, write to .key file
   └─ Yes → Load existing key
3. Check if config.json exists
   ├─ No  → Create empty {} config.json
   └─ Yes → Load existing config
4. is_complete() returns False → setup_wizard is triggered by main.py
```

### Security Notes

- Add `.key` to `.gitignore` — it MUST NOT be committed to version control
- Add `config.json` to `.gitignore` — it contains encrypted secrets
- If `.key` is lost, config.json values cannot be recovered — user must re-run setup wizard
- Fernet encryption is time-stamped — tokens include creation time

---

## models.py — Data Models

### Purpose

Defines data models used across the system. SQLAlchemy models for the database (controller) and Pydantic models for API request/response validation.

### Enums

```
class JobStatus(str, Enum):
    PENDING = "PENDING"
    CLAIMED = "CLAIMED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Priority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"
```

### SQLAlchemy Model — Job (Database)

```
class Job(Base):
    """SQLAlchemy ORM model for the jobs table.
    
    __tablename__ = 'jobs'
    
    Columns:
        id:            String(36), primary_key, default=lambda: str(uuid4())
        file_path:     String, nullable=False
        file_name:     String, nullable=False
        status:        String, nullable=False, default=JobStatus.PENDING
        priority:      String, nullable=False, default=Priority.NORMAL
        worker_id:     String, nullable=True
        created_at:    DateTime, default=datetime.utcnow
        updated_at:    DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
        retry_count:   Integer, default=0
        error_message: Text, nullable=True
        output_path:   String, nullable=True
    
    Indexes:
        - Index on status (for fast job claiming queries)
        - Index on created_at (for ordering)
        - Composite index on (status, priority, created_at) for claim_next_job()
    """
```

### Pydantic Models — API Request/Response

```
class JobResponse(BaseModel):
    """Pydantic model for job data in API responses.
    
    Fields:
        id:            str
        file_path:     str
        file_name:     str
        status:        JobStatus
        priority:      Priority
        worker_id:     Optional[str]
        created_at:    datetime
        updated_at:    datetime
        retry_count:   int
        error_message: Optional[str]
        output_path:   Optional[str]
    
    Config:
        from_attributes = True  (allows creating from SQLAlchemy objects)
    """

class JobStatusUpdate(BaseModel):
    """Pydantic model for POST /jobs/{id}/status request body.
    
    Fields:
        status:        JobStatus
        output_path:   Optional[str] = None
        error_message: Optional[str] = None
    """

class WorkerHeartbeat(BaseModel):
    """Pydantic model for POST /workers/heartbeat request body.
    
    Fields:
        worker_id:      str
        ip:             str
        jobs_completed: int = 0
        current_job_id: Optional[str] = None
    """

class StatsResponse(BaseModel):
    """Pydantic model for GET /stats response.
    
    Fields:
        queue_depth:    int
        done_today:     int
        failed_today:   int
        active_workers: int
    """
```

---

## logger.py — Logging Infrastructure

### Purpose

Provides a consistent logging setup used by all modules. Outputs to both a rotating file and the console with colored output.

### Function Signatures

```
def get_logger(name: str) -> logging.Logger:
    """Create and return a configured logger.
    
    Args:
        name: Logger name (e.g., 'controller', 'worker', 'watcher')
    
    Returns:
        Configured Logger instance with two handlers:
        
        1. Rotating File Handler:
           - Path: logs/render-agent.log
           - Max size: 10 MB per file
           - Backup count: 5 (keeps render-agent.log.1 through .5)
           - Level: DEBUG (captures everything)
        
        2. Console Handler (StreamHandler to stdout):
           - Colored output using ANSI codes
           - Level: INFO (hides DEBUG in console)
    
    Log Format:
        '2024-01-01 12:00:00 [INFO] controller: Server started on port 8765'
        '{timestamp} [{level}] {name}: {message}'
    
    Console Colors (ANSI):
        DEBUG    → Gray    (\\033[90m)
        INFO     → White   (\\033[97m)
        WARNING  → Yellow  (\\033[93m)
        ERROR    → Red     (\\033[91m)
        CRITICAL → Bold Red (\\033[1;91m)
    
    Creates logs/ directory if it doesn't exist (using os.makedirs)."""
```

### Log File Rotation

```
logs/
├── render-agent.log       ← Current log file (max 10 MB)
├── render-agent.log.1     ← Previous log file
├── render-agent.log.2     ← ...
├── render-agent.log.3
├── render-agent.log.4
└── render-agent.log.5     ← Oldest backup (auto-deleted when 6th is created)
```

### Usage Pattern

```python
# In any module:
from shared.logger import get_logger

logger = get_logger("controller")
logger.info("Server started on port 8765")
logger.warning("Worker DESKTOP-PC01 missed heartbeat")
logger.error(f"Job failed: {traceback.format_exc()}")
```

### Implementation Notes

- Use `logging.handlers.RotatingFileHandler` for file rotation
- Use a custom `logging.Formatter` subclass for console colors
- Each call to `get_logger()` with the same name returns the SAME logger instance (Python logging's built-in behavior)
- Always create the `logs/` directory with `os.makedirs("logs", exist_ok=True)` before adding the file handler
- The console color formatter should reset colors after each message with `\033[0m`

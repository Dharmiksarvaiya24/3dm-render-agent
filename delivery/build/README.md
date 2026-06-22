# Build Module

Contains build scripts, version metadata, and dependency manifests for packaging RenderAgent into distributable executables.

---

## Files

| File | Purpose |
|------|---------|
| `build_windows.bat` | Windows batch script to build controller.exe and worker.exe |
| `version.json` | Version metadata for the auto-updater |
| `requirements-controller.txt` | Python dependencies for the controller |
| `requirements-worker.txt` | Python dependencies for the worker |

---

## build_windows.bat — Windows Build Script

### Purpose

Automates the full build pipeline on Windows: install dependencies, build the React dashboard, and package both controller and worker as standalone `.exe` files using PyInstaller.

### Exact Script Contents

```batch
@echo off
echo ==========================================
echo  RenderAgent Build Script
echo ==========================================
echo.

REM Step 1: Install Python dependencies for controller
echo [1/6] Installing controller Python dependencies...
pip install -r requirements-controller.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install controller dependencies
    exit /b 1
)

REM Step 2: Install Python dependencies for worker
echo [2/6] Installing worker Python dependencies...
pip install -r requirements-worker.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install worker dependencies
    exit /b 1
)

REM Step 3: Install Playwright Chromium
echo [3/6] Installing Playwright Chromium browser...
python -m playwright install chromium
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install Playwright Chromium
    exit /b 1
)

REM Step 4: Build React dashboard
echo [4/6] Building React dashboard...
cd ..\controller\dashboard
npm install
npm run build
cd ..\..\build
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build dashboard
    exit /b 1
)

REM Step 5: Package controller with PyInstaller
echo [5/6] Packaging controller.exe...
pyinstaller --onefile --name controller --add-data "..\controller\dashboard\dist;dashboard\dist" ..\controller\main.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build controller.exe
    exit /b 1
)

REM Step 6: Package worker with PyInstaller
echo [6/6] Packaging worker.exe...
pyinstaller --onefile --name worker ..\worker\agent.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build worker.exe
    exit /b 1
)

REM Copy executables to dist folder
echo.
echo Copying executables to dist/...
mkdir dist 2>nul
copy dist\controller\controller.exe dist\controller.exe
copy dist\worker\worker.exe dist\worker.exe

echo.
echo ==========================================
echo  Build complete!
echo  Output:
echo    dist\controller.exe
echo    dist\worker.exe
echo ==========================================
```

### PyInstaller Flags

| Flag | Purpose |
|------|---------|
| `--onefile` | Bundle everything into a single `.exe` |
| `--name controller` | Output filename: `controller.exe` |
| `--add-data "..;dashboard\dist"` | Include built React dashboard in the bundle |

### Build Output

```
build/
├── dist/
│   ├── controller.exe    ← Standalone controller executable
│   └── worker.exe         ← Standalone worker executable
├── build/                 ← PyInstaller intermediate files (can be deleted)
├── controller.spec        ← PyInstaller spec file (auto-generated)
└── worker.spec            ← PyInstaller spec file (auto-generated)
```

---

## version.json — Version Metadata

### Purpose

Stores the current version number and download URLs for the auto-updater (`controller/updater.py`). The auto-updater compares the local version against the latest GitHub Release.

### Structure

```json
{
  "version": "1.0.0",
  "controller_url": "https://github.com/yourrepo/releases/download/v1.0.0/controller.exe",
  "worker_url": "https://github.com/yourrepo/releases/download/v1.0.0/worker.exe"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Semantic version of the current build (e.g., `"1.0.0"`, `"1.2.3"`) |
| `controller_url` | string | Direct download URL for the controller executable from GitHub Releases |
| `worker_url` | string | Direct download URL for the worker executable from GitHub Releases |

### Versioning Rules

- Use **semantic versioning**: `MAJOR.MINOR.PATCH`
  - `MAJOR`: Breaking changes (API changes, config format changes)
  - `MINOR`: New features (new endpoints, new dashboard pages)
  - `PATCH`: Bug fixes and minor improvements
- The auto-updater compares version strings using `packaging.version.Version` or a simple tuple comparison:
  ```
  tuple(map(int, remote.split('.'))) > tuple(map(int, local.split('.')))
  ```

### Auto-Update Flow

```
1. updater.py reads build/version.json → local version "1.0.0"
2. updater.py calls GitHub API:
   GET https://api.github.com/repos/{owner}/{repo}/releases/latest
3. Parse response → remote version "1.1.0"
4. Compare: "1.1.0" > "1.0.0" → update available
5. Download new .exe from release assets
6. Replace current executable
7. Update version.json with new version
8. Restart the process
```

---

## requirements-controller.txt — Controller Dependencies

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy>=2.0.0
watchdog>=3.0.0
pystray>=0.19.0
Pillow>=10.0.0
pywin32>=306
cryptography>=41.0.0
requests>=2.31.0
pydantic>=2.5.0
pyinstaller>=6.0.0
```

> **Note**: `pystray` and `pywin32` are Windows-only. They will fail to install on Mac/Linux but this is handled at runtime with try/except guards. For Mac development, install with `--ignore-installed` or comment out those lines.

---

## requirements-worker.txt — Worker Dependencies

```
playwright>=1.40.0
cryptography>=41.0.0
requests>=2.31.0
pywin32>=306
pydantic>=2.5.0
pyinstaller>=6.0.0
```

> **Note**: `pywin32` is Windows-only. Same runtime guard as above.

---

## Release Checklist

When creating a new release:

1. Update `version.json` with the new version number
2. Run `build_windows.bat` on a Windows machine
3. Test both `controller.exe` and `worker.exe` on a clean Windows machine
4. Create a GitHub Release with tag `v{version}` (e.g., `v1.1.0`)
5. Upload `controller.exe` and `worker.exe` as release assets
6. Update `controller_url` and `worker_url` in `version.json` with the new release URLs
7. Commit and push the updated `version.json`

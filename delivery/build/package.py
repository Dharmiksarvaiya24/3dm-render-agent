#!/usr/bin/env python3
"""
 build/package.py — Cross-platform packager for RenderAgent client delivery.
 Run on macOS/Linux/Windows to populate the delivery/ folder.
"""
import os
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DELIVERY_DIR = os.path.join(PROJECT_ROOT, "delivery")

EXCLUDES = {
    ".git", ".DS_Store", "venv", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", "*.log", "*.db", "config.json", ".key",
    "delivery", "render_agent.db", ".key"
}


def should_exclude(name: str) -> bool:
    return name in EXCLUDES or name.endswith(('.log', '.db'))


def copy_tree(src: str, dst: str) -> None:
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(os.path.dirname(dst) if not dst.endswith(os.sep) else os.path.dirname(dst.rstrip(os.sep)), exist_ok=True)
    shutil.copytree(src, dst, ignore=lambda d, names: [n for n in names if should_exclude(n)])


def main():
    print("=" * 50)
    print(" RenderAgent — Packaging for Client Delivery")
    print("=" * 50)
    print()

    # Clean / create delivery dir
    if os.path.exists(DELIVERY_DIR):
        print("Cleaning old delivery folder...")
        shutil.rmtree(DELIVERY_DIR)
    os.makedirs(DELIVERY_DIR, exist_ok=True)

    dirs_to_copy = ["controller", "worker", "shared", "build"]
    for d in dirs_to_copy:
        src = os.path.join(PROJECT_ROOT, d)
        dst = os.path.join(DELIVERY_DIR, d)
        print(f"Copying {d}/ ...")
        copy_tree(src, dst)

    # Copy start scripts
    for bat in ["start_controller.bat", "start_worker.bat"]:
        src = os.path.join(PROJECT_ROOT, bat)
        if os.path.exists(src):
            shutil.copy2(src, DELIVERY_DIR)
            print(f"Copied {bat}")

    # Create Install_Controller.bat (user-facing, capitalized)
    install_controller = os.path.join(DELIVERY_DIR, "Install_Controller.bat")
    with open(install_controller, "w") as f:
        f.write('@echo off\n')
        f.write('chcp 65001 >nul\n')
        f.write('echo.\n')
        f.write('echo   ================================================\n')
        f.write('echo    RenderAgent Controller - Installation\n')
        f.write('echo   ================================================\n')
        f.write('echo.\n')
        f.write('echo  Installing... Please wait.\n')
        f.write('echo.\n')
        f.write('call ".\\build\\install_controller.bat"\n')
        f.write('pause\n')

    # Create Install_Worker.bat
    install_worker = os.path.join(DELIVERY_DIR, "Install_Worker.bat")
    with open(install_worker, "w") as f:
        f.write('@echo off\n')
        f.write('chcp 65001 >nul\n')
        f.write('echo.\n')
        f.write('echo   ================================================\n')
        f.write('echo    RenderAgent Worker - Installation\n')
        f.write('echo   ================================================\n')
        f.write('echo.\n')
        f.write('echo  Installing... Please wait.\n')
        f.write('echo.\n')
        f.write('call ".\\build\\install_worker.bat"\n')
        f.write('pause\n')

    # Create HOW_TO_USE.txt
    how_to = os.path.join(DELIVERY_DIR, "HOW_TO_USE.txt")
    with open(how_to, "w") as f:
        f.write("RenderAgent — How to Use\n")
        f.write("=======================================\n\n")
        f.write("1.  PLUG IN THE USB DRIVE\n")
        f.write("    Open this folder on the USB drive.\n\n")
        f.write("2.  RUN THE INSTALLER\n")
        f.write("    Double-click one of these files:\n")
        f.write("      - Install_Controller.bat   (for the main computer)\n")
        f.write("      - Install_Worker.bat       (for helper computers)\n")
        f.write("    Wait for it to finish. It will install everything automatically.\n\n")
        f.write("3.  FIRST RUN SETUP\n")
        f.write("    The first time you run the Controller or Worker,\n")
        f.write("    a beautiful setup wizard will appear.\n")
        f.write("    Fill in your details and click SAVE.\n\n")
        f.write("4.  DAILY USE\n")
        f.write("    After setup, just double-click the desktop shortcut every day.\n")
        f.write("    That's it! RenderAgent will do the rest.\n\n")
        f.write("=======================================\n")
        f.write("Need help? Contact support.\n")

    # Summary
    entries = os.listdir(DELIVERY_DIR)
    print()
    print("=" * 50)
    print(" Packaging Complete!")
    print("=" * 50)
    print()
    print(f"Delivery folder: {DELIVERY_DIR}")
    print()
    print("Contents:")
    for e in sorted(entries):
        print(f"  - {e}")
    print()
    print("Give the 'delivery' folder to your client on USB.")
    print()


if __name__ == "__main__":
    main()

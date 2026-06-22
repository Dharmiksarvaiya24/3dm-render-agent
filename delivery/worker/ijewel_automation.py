# ===== worker/ijewel_automation.py =====

import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.logger import get_logger

logger = get_logger("ijewel_automation")

_playwright = None
_browser_context = None
_page = None


async def _ensure_browser():
    global _playwright, _browser_context, _page

    if _browser_context is not None:
        return _page

    try:
        from playwright.async_api import async_playwright

        logger.info("🌐 Opening browser window...")
        _playwright = await async_playwright().start()

        session_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "browser_session",
        )
        os.makedirs(session_dir, exist_ok=True)

        _browser_context = await _playwright.chromium.launch_persistent_context(
            user_data_dir=session_dir,
            headless=False,
            slow_mo=500,
            viewport={"width": 1920, "height": 1080},
            accept_downloads=True,
        )
        _page = _browser_context.pages[0] if _browser_context.pages else await _browser_context.new_page()
        logger.info("Browser launched successfully")
        return _page
    except Exception:
        import traceback

        logger.error(f"Browser launch failed: {traceback.format_exc()}")
        raise


async def run(file_path: str, output_folder: str, email: str, password: str) -> bool:
    try:
        page = await _ensure_browser()
        filename_without_extension = os.path.splitext(os.path.basename(file_path))[0]
        job_id = os.path.basename(file_path)

        logger.info("🔐 Checking login status...")

        await page.goto("https://ijewel.design")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        btn = await page.query_selector(
            "#__next > div > div:nth-of-type(2) > header > div:nth-of-type(2) > div:nth-of-type(2) > button:nth-of-type(1)"
        )

        if btn:
            logger.info("✅ Already logged in")
        else:
            logger.info("Not logged in — proceeding to login")
            logger.info("🔑 Logging in...")

            await page.goto("https://ijewel.design/login?redirect=/")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)

            await page.get_by_placeholder("Enter your email").fill(email)
            await page.wait_for_timeout(500)

            await page.get_by_placeholder("Enter your password").fill(password)
            await page.wait_for_timeout(500)

            await page.get_by_role("button", name="Log in").click()
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)

            if "/login" in page.url:
                raise Exception("Login failed — check credentials in config.json")

            logger.info("✅ Login successful")

        logger.info("📂 Opening upload modal...")

        await page.goto("https://ijewel.design")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        await page.locator(
            "#__next > div > div:nth-of-type(2) > header > div:nth-of-type(2) > div:nth-of-type(2) > button:nth-of-type(1) > svg"
        ).click()

        await page.wait_for_selector('section[role="dialog"]', timeout=15000)
        logger.info("Upload modal opened")

        dialog = page.locator('section[role="dialog"]')

        logger.info("📁 Setting file for upload...")

        file_input = dialog.locator('input[type="file"]')
        await file_input.wait_for(timeout=10000)
        await file_input.set_input_files(str(file_path))
        logger.info(f"File set: {file_path}")

        # Wait for file to be processed by the site
        await page.wait_for_timeout(2000)

        # Fill title first (required before UPLOAD enables)
        # Use first() to target only the first visible Title input in dialog
        title_input = page.locator('section[role="dialog"] input[placeholder="Title (required)"]').first
        await title_input.wait_for(timeout=10000)
        await title_input.fill(filename_without_extension)
        logger.info(f"Title filled: {filename_without_extension}")

        # Fill description field inside dialog (second input)
        description_input = page.locator('section[role="dialog"] input[placeholder="Description"]').first
        await description_input.wait_for(timeout=5000)
        await description_input.fill(f"Auto-rendered by RenderAgent on {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        logger.info("Description filled")

        # Wait until UPLOAD button is NOT disabled
        # It has class "bg-primary" and is in the dialog footer
        logger.info("Waiting for UPLOAD button to enable...")
        await page.wait_for_function("""
            () => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const uploadBtn = buttons.find(b => b.textContent.trim() === 'UPLOAD');
                return uploadBtn && !uploadBtn.disabled && !uploadBtn.hasAttribute('data-disabled');
            }
        """, timeout=15000)

        # Click the enabled UPLOAD button
        logger.info("Clicking UPLOAD button...")
        buttons = await page.query_selector_all('button')
        for btn in buttons:
            text = await btn.inner_text()
            if text.strip() == 'UPLOAD':
                is_disabled = await btn.get_attribute('disabled')
                if is_disabled is None:
                    await btn.click()
                    logger.info("✅ UPLOAD button clicked")
                    break

        # Wait for dialog to close after upload
        logger.info("Waiting for upload to complete...")
        await page.wait_for_selector('section[role="dialog"]', state='hidden', timeout=60000)
        logger.info("✅ Upload complete, dialog closed")

        logger.info("🎬 Waiting for render to complete (up to 20 min)...")

        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(3000)

        logger.info("🎬 Looking for Export tab...")

        try:
            export_tab = page.get_by_role("tab", name="Export")
            await export_tab.wait_for(timeout=5000)
            await export_tab.click()
            logger.info("Clicked Export tab by role")
        except Exception:
            try:
                await page.locator('[id*="-tab-export"]').click()
                logger.info("Clicked Export tab by id")
            except Exception:
                try:
                    await page.get_by_text("Export").first.click()
                    logger.info("Clicked Export tab by text")
                except Exception:
                    await page.locator('[aria-label*="export" i]').first.click()
                    logger.info("Clicked Export tab by aria-label")

        await page.wait_for_timeout(2000)
        logger.info("Export panel opened")

        logger.info("⬇️ Looking for Export as MP4 button...")

        async with page.expect_download() as download_info:
            try:
                mp4_btn = page.locator('[name="Download .mp4"]')
                await mp4_btn.wait_for(timeout=10000)
                await mp4_btn.click()
                logger.info("Clicked Download .mp4 by name")
            except Exception:
                try:
                    mp4_btn = page.get_by_role("button", name="Export as MP4")
                    await mp4_btn.wait_for(timeout=5000)
                    await mp4_btn.click()
                    logger.info("Clicked Export as MP4 by role")
                except Exception:
                    try:
                        mp4_btn = page.get_by_text("Export as MP4").first
                        await mp4_btn.wait_for(timeout=5000)
                        await mp4_btn.click()
                        logger.info("Clicked Export as MP4 by text")
                    except Exception:
                        mp4_btn = page.get_by_text("Download").first
                        await mp4_btn.wait_for(timeout=5000)
                        await mp4_btn.click()
                        logger.info("Clicked Download by text")

        logger.info("⬇️  Downloading MP4...")

        download = await download_info.value

        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_filename = filename_without_extension + ".mp4"
        output_path = output_dir / output_filename
        await download.save_as(str(output_path))

        logger.info(f"Download complete. Saved to: {output_path}")
        logger.info("✅ Job complete!")
        return True

    except Exception:
        import traceback

        tb = traceback.format_exc()
        logger.error(f"Automation failed: {tb}")
        try:
            if _page is not None:
                screenshot_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "logs",
                    f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                )
                os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                await _page.screenshot(path=screenshot_path)
                logger.info(f"Error screenshot saved: {screenshot_path}")
        except Exception:
            pass
        raise Exception(tb) from None
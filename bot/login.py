from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from bot.config import (
    ACTION_DELAY,
    LoginError,
    MAX_LOGIN_RETRIES,
    REQUEST_TIMEOUT,
    SESSION_PATH,
    SIAKAD_PASSWORD,
    SIAKAD_URL,
    SIAKAD_USERNAME,
    ensure_runtime_dirs,
    load_selectors,
    require_credentials,
)
from bot.utils import get_logger, screenshot_path, with_retry


class BrowserSession:
    def __init__(
        self,
        playwright: Playwright,
        browser: Browser,
        context: BrowserContext,
        page: Page,
    ) -> None:
        self.playwright = playwright
        self.browser = browser
        self.context = context
        self.page = page

    async def close(self) -> None:
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()


async def create_browser(headless: bool = True) -> BrowserSession:
    ensure_runtime_dirs()
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context(
        viewport={"width": 1440, "height": 900},
        locale="id-ID",
    )
    context.set_default_timeout(REQUEST_TIMEOUT)
    page = await context.new_page()
    return BrowserSession(playwright, browser, context, page)


async def save_session(context: BrowserContext, path: Path | None = None) -> Path:
    ensure_runtime_dirs()
    target = path or SESSION_PATH
    await context.storage_state(path=str(target))
    return target


async def is_logged_in(page: Page, selectors: dict[str, Any] | None = None) -> bool:
    data = selectors or load_selectors()
    login_sel = data.get("login", {})
    success = login_sel.get("success_indicator") or "a:has-text('[ Logout ]')"
    form = login_sel.get("form") or "#form-login"
    if await page.locator(success).count() > 0:
        return True
    if await page.locator(form).count() > 0:
        return False
    return "logout" in (await page.content()).lower()


async def _fill_and_submit(page: Page, selectors: dict[str, Any]) -> None:
    login_sel = selectors["login"]
    await page.wait_for_selector(login_sel["username"], state="visible")
    await page.locator(login_sel["username"]).fill(SIAKAD_USERNAME)
    await page.locator(login_sel["password"]).fill(SIAKAD_PASSWORD)
    await page.locator(login_sel["submit"]).click()
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(ACTION_DELAY)


async def login(
    page: Page,
    *,
    selectors: dict[str, Any] | None = None,
    max_retries: int | None = None,
    screenshot_on_success: bool = True,
) -> None:
    log = get_logger("login")
    require_credentials()
    data = selectors or load_selectors()
    login_sel = data.get("login") or {}
    url = login_sel.get("url") or SIAKAD_URL
    retries = max_retries if max_retries is not None else MAX_LOGIN_RETRIES

    async def attempt() -> None:
        log.info("Membuka halaman login SIAKAD")
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(ACTION_DELAY)

        captcha = login_sel.get("captcha")
        if captcha and await page.locator(captcha).count() > 0:
            shot = screenshot_path("login", "captcha")
            await page.screenshot(path=str(shot), full_page=True)
            raise LoginError(
                f"CAPTCHA terdeteksi. Selesaikan manual di mode headed. Screenshot: {shot}"
            )

        if await is_logged_in(page, data):
            log.info("Sudah dalam sesi login")
            return

        await _fill_and_submit(page, data)

        if await is_logged_in(page, data):
            log.info("Login berhasil")
            if screenshot_on_success:
                shot = screenshot_path("login", "success")
                await page.screenshot(path=str(shot), full_page=True)
                log.info(f"Screenshot login disimpan: {shot.name}")
            return

        body = (await page.locator("body").inner_text()).lower()
        error_hints = login_sel.get("error_text_contains") or []
        if any(hint in body for hint in error_hints):
            raise LoginError("Login gagal — kredensial ditolak atau form error")
        if await page.locator(login_sel.get("form") or "#form-login").count() > 0:
            raise LoginError("Login gagal — masih di halaman form login")
        raise LoginError("Login gagal — indikator sukses tidak ditemukan")

    await with_retry(attempt, max_retries=retries, delay=2.0, module="login")


async def login_with_browser(
    *,
    headless: bool = True,
    save_state: bool = True,
) -> BrowserSession:
    log = get_logger("login")
    session = await create_browser(headless=headless)
    try:
        await login(session.page)
        if save_state:
            path = await save_session(session.context)
            log.info(f"Session disimpan: {path.name}")
        return session
    except Exception:
        await session.close()
        raise

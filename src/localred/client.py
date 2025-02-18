import asyncio
import base64
import os
import traceback
from time import time
from typing import Any, Awaitable, Callable, List, Optional

from playwright.async_api import Page, async_playwright

from .chrome_finder import find_chrome
from .models import Note
from .utils import build_search_url, load_js_file, logger


# returns None if not valid
def _js_note_to_note(js_note: dict) -> Note | None:
    if not js_note.get("url"):
        logger.warning(f"Invalid note: {js_note}")
        return None
    return Note(
        url=js_note["url"],
        title=js_note["title"] or None,
        author=js_note["author"] or None,
        like_count=js_note["like_count_num"] or None,
        cover_url=js_note["cover_url"] or None,
        is_video=js_note["is_video"],
    )


class BrowserClient:
    def __init__(
        self,
        remote_debugging_port: int = 9222,
        concurrency: int = 3,
        headless: bool = True,  # only used when remote_debugging_port is not provided
        browser_state_path: str
        | None = "~/.localred.browser_state.json",  # None means do not load browser state
    ):
        self.concurrency = concurrency
        self.semaphore = asyncio.Semaphore(self.concurrency)
        self.remote_debugging_port = remote_debugging_port
        self.headless = headless
        self.browser = None
        self.context = None
        self.browser_state_path = (
            os.path.expanduser(browser_state_path) if browser_state_path else None
        )

    async def __aenter__(self):
        playwright = await async_playwright().start()
        if self.remote_debugging_port:
            self.browser = await playwright.chromium.connect_over_cdp(
                f"http://localhost:{self.remote_debugging_port}"
            )
            self.context = self.browser.contexts[0]
        else:
            self.browser = await playwright.chromium.launch(
                executable_path=find_chrome(),
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--lang=en-US,en",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
                ignore_default_args=["--enable-automation"],
            )

            # Try to load saved state if it exists
            storage_state = None
            if self.browser_state_path and os.path.exists(self.browser_state_path):
                logger.info(
                    f"Loading browser state({int(os.stat(self.browser_state_path).st_size / 1024)}KB) from {self.browser_state_path}"
                )
                storage_state = self.browser_state_path

            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 2560},
                locale="en-US",
                timezone_id="Asia/Hong_Kong",
                bypass_csp=True,
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "DNT": "1",
                    "Upgrade-Insecure-Requests": "1",
                },
                permissions=["geolocation"],
                storage_state=storage_state,
            )
            await self.context.add_init_script(load_js_file("stealth"))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def _setup_page(self, page: Page) -> None:
        await page.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in ["image", "media"]
            else route.continue_(),
        )

    async def process_page(
        self,
        page: Page,
        url: str,
        needs_check_login: bool,
        wait_extra_selector: Optional[str] = None,
        extra_timeout: float = 10000,  # 10 seconds
    ):
        await self._setup_page(page)
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)

        if needs_check_login:
            if not await self._check_login(page):
                raise Exception("Not logged in")

        if wait_extra_selector:
            # logger.debug(f"Waiting for {wait_extra_selector}")
            await page.wait_for_selector(wait_extra_selector, timeout=extra_timeout)
            await page.route("**/*", lambda route: route.abort())

    async def visit_link(self, url_or_result: str | Note) -> Note:
        start_time = time()
        async with self.semaphore:
            wait_time = time() - start_time
            start_time = time()

            result = (
                Note(url=url_or_result)
                if isinstance(url_or_result, str)
                else url_or_result
            )
            try:
                page = await self.context.new_page()
                await self.process_page(
                    page,
                    result.url,
                    needs_check_login=False,
                    wait_extra_selector=".comments-el .list-container, .no-comments-text",
                    # async loading comments is slow in some cases, so we wait longer
                    extra_timeout=20000,
                )
                note = await page.evaluate(load_js_file("note_extract"))

                if not result.title:
                    result.title = note["title"]
                result.content = note["content"]
                result.comments = note["comments"]
                result.date_string = note["date"]

                visit_time = time() - start_time
                logger.debug(f"{visit_time:.2f}|{wait_time:.2f}s {result.title}")
                return result
            except Exception as e:
                logger.error(f"Error visit {result.title} {result.url}: {e}")
                return result
            finally:
                await page.close()

    # will only returns successfully fulfilled notes
    async def visit_links(self, url_or_notes: List[str | Note]) -> List[Note]:
        tasks = [self.visit_link(n) for n in url_or_notes]
        results = await asyncio.gather(*tasks)
        return [r for r in results if (r.content or r.comments or r.date_string)]

    # may will returns more than max_results
    async def search(
        self,
        query: Optional[str],
        max_results: int = 15,
        visit_links: bool = False,
        filters: List[
            Callable[[Note], bool]
        ] = [],  # returns True if the webpage should be included
    ) -> List[Note]:
        page = await self.context.new_page()
        try:
            url = build_search_url(query)
            await self.process_page(
                page,
                url,
                # no query will not need login
                needs_check_login=query is not None,
                wait_extra_selector=".note-item",
                extra_timeout=10000,
            )

            # Initial extraction of notes
            all_js_notes = await page.evaluate(load_js_file("explore_extract"))
            all_notes = [_js_note_to_note(note) for note in all_js_notes if note]
            if filters:
                all_notes = [n for n in all_notes if all(f(n) for f in filters)]

            seen_urls = set(note.url for note in all_notes)

            # Remove previous request blocking
            await page.unroute("**/*")

            # Set up selective request blocking:
            # 1. Allow homefeed API endpoint
            # 2. Block most other resources to speed up loading
            async def route_handler(route):
                if "homefeed" in route.request.url:
                    await route.continue_()
                elif route.request.resource_type in [
                    "image",
                    "media",
                    "stylesheet",
                    "font",
                    "script",
                ]:
                    await route.abort()
                else:
                    await route.continue_()

            await page.route(
                "**/*",
                route_handler,
            )

            # Load more if needed
            max_scroll_attempts = 8  # Increased to get more results
            scroll_attempts = 0

            while (
                len(all_notes) < max_results and scroll_attempts < max_scroll_attempts
            ):
                # Scroll to bottom to trigger loading more
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

                # Wait for potential new content to load
                try:
                    # Wait a bit for scroll to complete and new items to start loading
                    await asyncio.sleep(3)  # Increased wait time for API to respond

                    # Extract new batch of notes
                    new_js_notes = await page.evaluate(load_js_file("explore_extract"))
                    new_notes = [
                        _js_note_to_note(note) for note in new_js_notes if note
                    ]
                    if filters:
                        new_notes = [n for n in new_notes if all(f(n) for f in filters)]

                    # Check if content is different by comparing URLs
                    current_urls = set(note.url for note in new_notes)
                    new_urls = current_urls - seen_urls

                    # Add only new, unique notes
                    new_count = 0
                    for note in new_notes:
                        if note.url and note.url in new_urls:
                            all_notes.append(note)
                            seen_urls.add(note.url)
                            new_count += 1

                    logger.debug(
                        f"Scroll {scroll_attempts + 1}: Added {new_count} new notes, total: {len(all_notes)}"
                    )

                    # If no new notes appeared, try one more time before breaking
                    if new_count == 0:
                        # Sometimes the site needs another scroll to load more content
                        if scroll_attempts < max_scroll_attempts - 1:
                            logger.debug(
                                "No new results in this batch, trying one more scroll"
                            )
                        else:
                            logger.debug("No new unique results found, stopping")
                            break

                except Exception as e:
                    logger.debug(f"Error loading more results: {e}")
                    break

                scroll_attempts += 1

            video_count = sum(1 for note in all_notes if note.is_video)
            logger.info(
                f"Found {len(all_notes)} unique results ({video_count} videos) for "
                + (f"query: {query}" if query else "/explore")
            )

            # Sort notes to prioritize non-video content
            all_notes = sorted(
                all_notes,
                key=lambda x: (x.is_video, -x.like_count),
            )

            all_notes = all_notes[:max_results]

            return await self.visit_links(all_notes) if visit_links else all_notes
        except Exception as e:
            logger.error(f"Error during search: {e}\n{traceback.format_exc()}")
            return []
        finally:
            await page.close()

    async def _check_login(self, page: Page) -> bool:
        return await page.query_selector(".login-btn") is None

    # this will open a new page then check login and close it
    async def new_page_and_check_login(
        self, random_click_if_login_in: bool = True
    ) -> bool:
        page = await self.context.new_page()
        await self._setup_page(page)
        try:
            # Disable image blocking for this page as we need the QR code
            await page.goto(
                "https://www.xiaohongshu.com/explore",
                wait_until="domcontentloaded",
                timeout=10000,
            )
            is_login = await self._check_login(page)
            if not is_login:
                return False
            if not random_click_if_login_in:
                return is_login

            logger.info(
                f"login: {'✓' if is_login else '✗'}, continue to random click..."
            )

            js_notes = await page.evaluate(load_js_file("explore_extract"))
            if not js_notes:
                logger.error("No notes found when checking login")
                return is_login

            notes = [
                Note(
                    url=note["url"],
                    title=note["title"] or None,
                    author=note["author"] or None,
                )
                for note in js_notes
            ]

            notes = await self.visit_links(notes[:2])
            logger.info(
                f"visited {len(notes)}: {'\n-----------------\n'.join([n.to_md() for n in notes])}"
            )

            return is_login
        finally:
            await page.close()

    async def try_login(
        self,
        display_qrcode_callback: Callable[[bytes], Awaitable[Any]],
        timeout: float = 120,
    ) -> bool:
        """Try to login and return True if successful.

        Args:
            display_qrcode_callback: Async function to display the QR code image bytes
            timeout: Maximum time to wait for login in seconds

        Returns:
            True if login successful

        Raises:
            Exception: If login fails or times out
        """
        page = await self.context.new_page()
        await self._setup_page(page)
        try:
            # Disable image blocking for this page as we need the QR code
            await page.goto(
                "https://www.xiaohongshu.com/explore",
                wait_until="domcontentloaded",
                timeout=10000,
            )
            if await self._check_login(page):
                logger.info("Already logged in")
                return True

            await page.wait_for_selector(".qrcode-img", timeout=5000)

            # Extract QR code image from base64 data
            qrcode_img = await page.query_selector(".qrcode-img")
            if not qrcode_img:
                raise Exception("QR code image not found")

            src = await qrcode_img.get_attribute("src")
            if not src or not src.startswith("data:image/png;base64,"):
                raise Exception("Invalid QR code image format")

            # Extract base64 data and convert to raw bytes
            base64_data = src.replace("data:image/png;base64,", "")
            img_bytes = base64.b64decode(base64_data)

            # Call the callback with raw bytes instead of PIL Image
            await display_qrcode_callback(img_bytes)

            # Wait for login to complete or timeout
            start_time = time()
            while time() - start_time < timeout:
                # Check if we're logged in by looking for user avatar or other indicators
                if await self._check_login(page):
                    try:
                        # Wait for any user-related element to be in the DOM, not necessarily visible
                        await page.wait_for_selector(
                            ".user-avatar, .avatar, .user, .user.side-bar-component",
                            state="attached",
                            timeout=5000,
                        )
                        # Add a small delay to ensure the login is fully processed
                        await asyncio.sleep(1)
                        logger.info("Login successful!")
                        await self.save_state()
                        return True
                    except Exception as e:
                        logger.warning(
                            f"Found login state but couldn't verify user elements: {e}"
                        )
                        # Continue anyway as check_login passed
                        return True
                # Wait a bit before checking again
                await asyncio.sleep(2)

            raise Exception(f"Login timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise
        finally:
            await page.close()

    # Add method to save state when needed
    async def save_state(self):
        """Save the current browser state including cookies and storage"""
        if self.context:
            path = self.browser_state_path or "browser_state.json"
            await self.context.storage_state(path=path)
            logger.info(f"Browser state saved to {path}")

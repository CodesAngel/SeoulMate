import asyncio
from playwright.async_api import async_playwright
import sys


async def debug_html_fetch_with_playwright(url: str, filename: str):
    """
    Launches a VISIBLE (non-headless) browser to debug content loading issues.
    Saves the HTML even if the initial selector fails.
    """
    print(f"Starting Playwright DEBUG fetch from: {url}")

    async with async_playwright() as p:
        # --- DEBUG STEP 1: Launch in non-headless mode ---
        # Change 'headless=False' to 'headless=True' once debugging is done.
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # 1. Navigation
        try:
            print("Navigating with 60s timeout and 'domcontentloaded' strategy...")
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )
            # Add a short, fixed wait for initial content
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Navigation error encountered: {e}")

        # 2. Wait for initial cards to appear
        card_selector = '.movie-card'

        # --- DEBUG STEP 2: Enhanced Selector Check ---
        try:
            print(f"Checking for selector '{card_selector}' (timeout 20s)...")
            await page.wait_for_selector(card_selector, timeout=20000)
            print("SUCCESS: Initial cards detected.")

            # Continue with scrolling only if cards are found
            print("Starting scroll routine...")
            for i in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                print(f"  -> Scrolled down {i + 1}/5 times.")
                await asyncio.sleep(2)

                # Final wait
            await asyncio.sleep(3)

        except Exception:
            print("\n!!! WARNING: Selector NOT FOUND after initial load.")
            print("!!! Please examine the visible browser window for CAPTCHA, block pages, or different content.")
            # Do NOT exit, proceed to save the current page source for analysis
            await asyncio.sleep(5)  # Give you time to look at the browser

        # 3. Get the full rendered HTML
        full_html_content = await page.content()

        # 4. Save the content
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(full_html_content)

        # Wait a moment before closing so you can see the result
        print(f"\nClosing browser in 10 seconds. Check the window...")
        await asyncio.sleep(10)
        await browser.close()

        print("\n--- DEBUG RESULT ---")
        print(f"Saved the current page content to '{filename}'.")
        print(f"File size: {len(full_html_content) / 1024:.2f} KB")


# --- Configuration ---
URL = "https://kisskh.co/Explore?status=2&country=2&sub=1&type=1&order=1"
# Use a distinct filename for the debug run
FILENAME = "kissh_debug_output.html"

# Run the asynchronous function
if __name__ == "__main__":
    asyncio.run(debug_html_fetch_with_playwright(URL, FILENAME))
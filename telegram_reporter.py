import asyncio
from playwright.async_api import async_playwright
from playwright.stealth import stealth_async
from urllib.parse import urlparse
from scraper_utils import is_cloudflare_challenge, solve_cloudflare_challenge, USER_AGENT

# --- Configuration ---
TARGET_URL = "https://telegram.org/dsa-report"
PROXY_STRING = "http://user-sp7yo7yvvq-country-de:6=iq593lNSwfJTanxx@dc.decodo.com:10005"

def parse_proxy(proxy_string: str):
    """Parses a proxy string of format http://user:pass@host:port"""
    if not proxy_string:
        print("Proxy string is empty.")
        return None
    try:
        parsed = urlparse(proxy_string)
        if not all([parsed.scheme, parsed.hostname, parsed.port, parsed.username, parsed.password]):
            print(f"Proxy string '{proxy_string}' is malformed. It should be in 'http://user:pass@host:port' format.")
            return None
        
        return {
            "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
            "username": parsed.username,
            "password": parsed.password
        }
    except Exception as e:
        print(f"Could not parse proxy string: {e}")
        return None

async def main():
    """
    Main function to run the Playwright script.
    """
    proxy_config = parse_proxy(PROXY_STRING)
    if not proxy_config:
        print("Proxy configuration is invalid. Exiting.")
        return

    async with async_playwright() as p:
        print("Launching browser with proxy...")
        browser = await p.chromium.launch(
            headless=False,  # Set to True for production, False for debugging
            args=["--start-maximized"],
            proxy=proxy_config
        )
        
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        # Apply stealth measures
        await stealth_async(page)

        try:
            print(f"Navigating to {TARGET_URL}...")
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)

            if await is_cloudflare_challenge(page):
                if not await solve_cloudflare_challenge(context, page):
                    print("Failed to solve Cloudflare challenge. Exiting.")
                    return
                await page.wait_for_load_state("networkidle")
                if await is_cloudflare_challenge(page):
                    print("Cloudflare challenge persists after attempting to solve it.")
                    return

            print("Successfully navigated to the page.")
            
            report_button_selector = "button.btn.btn-primary.js-report-start-btn"
            print(f"Looking for button: '{report_button_selector}'")
            await page.locator(report_button_selector).click(timeout=30000)
            print("Button 'Report illegal content' clicked.")

            print("Waiting for 30 seconds...")
            await page.wait_for_timeout(30000)
            
            print("Wait finished. Script completed successfully.")

        except Exception as e:
            print(f"An error occurred during navigation or interaction: {e}")
        finally:
            if browser.is_connected():
                print("Closing browser.")
                await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth.stealth import stealth_async
from scraper_utils import is_cloudflare_challenge, solve_cloudflare_challenge, USER_AGENT

# --- Configuration ---
TARGET_URL = "https://linkpays.in/MHI6"

async def main():
    """
    Main function to run the Playwright script.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Set to True for production, False for debugging
            args=["--start-maximized"]
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

            # Check for Cloudflare challenge after initial navigation
            if await is_cloudflare_challenge(page):
                success = await solve_cloudflare_challenge(context, page)
                if not success:
                    print("Failed to solve Cloudflare challenge. Exiting.")
                    return

                # After reloading, wait for a final check
                await page.wait_for_load_state("networkidle")
                
                # Final check to see if the challenge is gone
                if await is_cloudflare_challenge(page):
                    print("Cloudflare challenge persists even after attempting to solve it.")
                    return

            print("Successfully bypassed any initial challenges.")
            print("Page loaded. Waiting for 30 seconds...")
            await page.wait_for_timeout(30000)
            
            print("Wait finished. Script completed successfully.")

        except Exception as e:
            print(f"An error occurred during navigation: {e}")
        finally:
            print("Closing browser.")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

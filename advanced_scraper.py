import asyncio
import httpx
from playwright.async_api import async_playwright, Page, BrowserContext
from playwright_extra.stealth import stealth_async

# --- Configuration ---
TARGET_URL = "https://linkpays.in/MHI6"
TURNSTILE_API_URL = "http://62.84.179.169:3000/cf-clearance-scraper"
# Set a realistic User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

async def is_cloudflare_challenge(page: Page) -> bool:
    """
    Checks if the current page is a Cloudflare challenge page (Turnstile or JS challenge).
    """
    title = await page.title()
    if "Just a moment..." in title:
        print("Cloudflare JS challenge detected by page title.")
        return True
    
    # Check for Turnstile or other challenge elements
    turnstile_selector = 'div.cf-turnstile, #cf-turnstile, iframe[src*="challenges.cloudflare.com"]'
    challenge_form_selector = '#challenge-form'
    
    try:
        if await page.query_selector(turnstile_selector):
            print("Cloudflare Turnstile challenge detected by element.")
            return True
        if await page.query_selector(challenge_form_selector):
            print("Cloudflare challenge form detected by element.")
            return True
    except Exception as e:
        print(f"An error occurred while checking for Cloudflare elements: {e}")

    return False

async def solve_cloudflare_challenge(context: BrowserContext, page: Page) -> bool:
    """
    Calls the external API to get clearance cookies and applies them.
    
    Note: This function assumes the API at TURNSTILE_API_URL returns a JSON
    object with a 'cookies' key, which is a list of cookie dictionaries.
    Example: {"status": "ok", "result": {"cookies": [{"name": "cf_clearance", ...}]}}
    """
    print(f"Attempting to solve Cloudflare challenge using API: {TURNSTILE_API_URL}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(TURNSTILE_API_URL, timeout=60)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            
            solver_data = response.json()

            # The structure of the response can vary. We adapt to a common format.
            # Adjust the keys ('result', 'cookies') if your API has a different structure.
            if "result" in solver_data and "cookies" in solver_data["result"]:
                cookies = solver_data["result"]["cookies"]
            elif "cookies" in solver_data:
                cookies = solver_data["cookies"]
            else:
                print("Error: Could not find 'cookies' in the API response.")
                return False

            if not cookies:
                print("API response did not contain any cookies.")
                return False

            # Add the cookies to the browser context
            await context.add_cookies(cookies)
            print("Successfully added clearance cookies to the browser context.")
            
            # Reload the page to apply the cookies
            print("Reloading the page...")
            await page.reload(wait_until="domcontentloaded")
            
            return True

    except httpx.RequestError as e:
        print(f"Error calling the captcha solver API: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while solving the challenge: {e}")
        
    return False

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

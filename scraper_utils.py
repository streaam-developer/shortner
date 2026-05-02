import httpx
from playwright.async_api import Page, BrowserContext

# --- Shared Configuration ---
TURNSTILE_API_URL = "http://62.84.179.169:3000/cf-clearance-scraper"
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
    verifying_selector = '#verifying'
    
    try:
        if await page.query_selector(turnstile_selector):
            print("Cloudflare Turnstile challenge detected by element.")
            return True
        if await page.query_selector(challenge_form_selector):
            print("Cloudflare challenge form detected by element.")
            return True
        if await page.query_selector(verifying_selector):
            print("Cloudflare 'Verifying...' challenge detected by element.")
            return True
    except Exception as e:
        print(f"An error occurred while checking for Cloudflare elements: {e}")

    return False

async def solve_cloudflare_challenge(context: BrowserContext, page: Page) -> bool:
    """
    Calls the external API to get clearance cookies and applies them.
    """
    print(f"Attempting to solve Cloudflare challenge using API: {TURNSTILE_API_URL}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(TURNSTILE_API_URL, timeout=60)
            response.raise_for_status()
            
            solver_data = response.json()

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

            await context.add_cookies(cookies)
            print("Successfully added clearance cookies to the browser context.")
            
            print("Reloading the page...")
            await page.reload(wait_until="domcontentloaded")
            
            return True

    except httpx.RequestError as e:
        print(f"Error calling the captcha solver API: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while solving the challenge: {e}")
        
    return False
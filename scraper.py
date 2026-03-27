"""
LinkedIn Profile Scraper Agent
Searches for BBA / B.Com / BTech graduates (2024-2025) and exports to Excel.

Uses a multi-strategy approach:
  1. BeautifulSoup parsing of page source (most reliable)
  2. Selenium CSS selectors (multiple fallbacks)
  3. JavaScript-based extraction (ultimate fallback)
"""

import os
import re
import sys
import time
import random
import urllib.parse

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)
from webdriver_manager.chrome import ChromeDriverManager

import config
from exporter import export_to_excel


# ═══════════════════════════════════════════════════════════════
#  Utility helpers
# ═══════════════════════════════════════════════════════════════

def random_delay(min_s: float, max_s: float) -> None:
    """Sleep for a random duration between min_s and max_s seconds."""
    time.sleep(random.uniform(min_s, max_s))


def human_scroll(driver, scrolls: int = 3) -> None:
    """Mimic human scrolling behaviour — scroll down slowly."""
    for _ in range(scrolls):
        scroll_px = random.randint(300, 700)
        driver.execute_script(f"window.scrollBy(0, {scroll_px});")
        time.sleep(random.uniform(0.5, 1.2))


def scroll_to_bottom(driver) -> None:
    """Scroll all the way down to trigger lazy-loaded content."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    # Scroll back up a bit so page is usable
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.5)


def safe_text(element) -> str:
    """Safely extract text from a Selenium element."""
    try:
        return element.text.strip()
    except Exception:
        return ""


def clean_name(raw: str) -> str:
    """Clean a name string — remove badges, connection degree, extra whitespace."""
    if not raw:
        return ""
    # Remove connection indicators like "• 2nd", "• 3rd", "• 1st"
    raw = re.sub(r'[•·]\s*(1st|2nd|3rd|3rd\+)', '', raw)
    # Remove "View … profile" type text
    raw = re.sub(r'View\s+.*?profile', '', raw, flags=re.IGNORECASE)
    # Remove extra newlines and whitespace
    raw = raw.split('\n')[0].strip()
    # Remove any remaining emojis / special badges
    raw = re.sub(r'[\U0001F300-\U0001F9FF]', '', raw).strip()
    return raw


# ═══════════════════════════════════════════════════════════════
#  Browser setup
# ═══════════════════════════════════════════════════════════════

def create_driver() -> webdriver.Chrome:
    """Create and return a configured Chrome WebDriver."""
    chrome_options = Options()

    # Anti-detection flags
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Remove webdriver flag from navigator
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )

    return driver


# ═══════════════════════════════════════════════════════════════
#  LinkedIn Login
# ═══════════════════════════════════════════════════════════════

def linkedin_login(driver: webdriver.Chrome, email: str, password: str) -> bool:
    """
    Log into LinkedIn. Returns True on success.
    Pauses for manual OTP / CAPTCHA if detected.
    """
    print("🔐  Navigating to LinkedIn login …")
    driver.get("https://www.linkedin.com/login")
    time.sleep(3)

    try:
        # Enter email
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        email_field.clear()
        for ch in email:  # type like a human
            email_field.send_keys(ch)
            time.sleep(random.uniform(0.04, 0.12))

        # Enter password
        pwd_field = driver.find_element(By.ID, "password")
        pwd_field.clear()
        for ch in password:
            pwd_field.send_keys(ch)
            time.sleep(random.uniform(0.04, 0.12))

        # Click Sign In
        random_delay(0.5, 1.5)
        pwd_field.send_keys(Keys.RETURN)
        time.sleep(config.LOGIN_WAIT)

        # Check for OTP / CAPTCHA / security challenge
        current_url = driver.current_url
        if "checkpoint" in current_url or "challenge" in current_url:
            print("\n⚠️   OTP / CAPTCHA detected!")
            print(f"     Please complete the verification in the browser within {config.OTP_TIMEOUT}s …")
            WebDriverWait(driver, config.OTP_TIMEOUT).until(
                lambda d: "feed" in d.current_url or "mynetwork" in d.current_url
                          or "search" in d.current_url or "in/" in d.current_url
            )
            print("✅  Verification completed!")

        # Confirm we are logged in
        if "feed" in driver.current_url or "mynetwork" in driver.current_url:
            print("✅  Logged into LinkedIn successfully!")
            return True
        else:
            # Give extra time in case page is slow
            time.sleep(5)
            if "feed" in driver.current_url or "mynetwork" in driver.current_url:
                print("✅  Logged into LinkedIn successfully!")
                return True

        print("⚠️   Login may not have succeeded. Current URL:", driver.current_url)
        print("     The script will continue — you may need to log in manually.")
        input("     Press ENTER after you are logged in … ")
        return True

    except TimeoutException:
        print("❌  Login timed out. Check your credentials or network.")
        return False


# ═══════════════════════════════════════════════════════════════
#  Search & Scrape — using BeautifulSoup on page source
# ═══════════════════════════════════════════════════════════════

def build_search_url(query: str, page: int = 1) -> str:
    """Build a LinkedIn People search URL for the given query and page."""
    encoded = urllib.parse.quote(query)
    return f"https://www.linkedin.com/search/results/people/?keywords={encoded}&page={page}"


def scrape_search_page(driver: webdriver.Chrome) -> list[dict]:
    """
    Scrape profile cards from the current LinkedIn search results page.
    Uses BeautifulSoup on page source for most reliable extraction.
    Returns a list of dicts with keys: name, profile_link, headline.
    """
    results = []

    # Scroll down to load all lazy-loaded results
    scroll_to_bottom(driver)
    human_scroll(driver, scrolls=3)
    time.sleep(2)

    # ─── Strategy 1: BeautifulSoup on page source ───────────────
    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Find all profile links — these are <a> tags pointing to /in/username
        # LinkedIn wraps each result in an <li> or <div> container
        profile_links = soup.find_all("a", href=re.compile(r"/in/[^/]+/?$"))

        seen_urls = set()
        for link_tag in profile_links:
            href = link_tag.get("href", "")
            if not href or "/in/" not in href:
                continue

            # Build clean profile URL
            if href.startswith("/"):
                profile_url = "https://www.linkedin.com" + href.split("?")[0]
            else:
                profile_url = href.split("?")[0]

            # De-duplicate (same profile can appear in multiple <a> tags)
            if profile_url in seen_urls:
                continue
            seen_urls.add(profile_url)

            # Extract name from the link or nearby elements
            name = ""

            # Method A: Look for <span aria-hidden="true"> inside the link (LinkedIn's pattern)
            name_span = link_tag.find("span", attrs={"aria-hidden": "true"})
            if name_span:
                name = name_span.get_text(strip=True)

            # Method B: Direct text of the link
            if not name:
                name = link_tag.get_text(strip=True)

            # Method C: Look in parent container for name
            if not name:
                parent = link_tag.find_parent("li") or link_tag.find_parent("div")
                if parent:
                    bold_span = parent.find("span", class_=re.compile(r"t-bold|t-16|entity-result__title"))
                    if bold_span:
                        name = bold_span.get_text(strip=True)

            name = clean_name(name)
            if not name or name.lower() == "linkedin member" or len(name) < 2:
                continue

            # Skip non-profile links (e.g., "View all" buttons)
            if any(skip in name.lower() for skip in ["view all", "see all", "try premium", "reactivate"]):
                continue

            # Extract headline — look in the parent container
            headline = ""
            parent_li = link_tag.find_parent("li")
            if not parent_li:
                parent_li = link_tag.find_parent("div", class_=re.compile(r"entity-result|search-result"))

            if parent_li:
                # Look for subtitle div
                for cls_pattern in [
                    re.compile(r"entity-result__primary-subtitle"),
                    re.compile(r"entity-result__summary"),
                    re.compile(r"t-14.*t-normal"),
                    re.compile(r"subline-level-1"),
                ]:
                    subtitle = parent_li.find("div", class_=cls_pattern)
                    if not subtitle:
                        subtitle = parent_li.find("span", class_=cls_pattern)
                    if subtitle:
                        headline = subtitle.get_text(strip=True)
                        break

                # Fallback: grab all text from the parent and extract the second line
                if not headline:
                    all_text = parent_li.get_text(separator="\n", strip=True)
                    lines = [l.strip() for l in all_text.split("\n") if l.strip()]
                    # The headline is usually the line right after the name
                    for i, line in enumerate(lines):
                        if name in line and i + 1 < len(lines):
                            headline = lines[i + 1]
                            break

            results.append({
                "name": name,
                "profile_link": profile_url,
                "headline": headline,
            })

    except Exception as e:
        print(f"     ⚠️  BeautifulSoup strategy failed: {e}")

    # ─── Strategy 2: Selenium fallback if BS4 found nothing ─────
    if not results:
        print("     🔄  Trying Selenium fallback for search results …")
        results = _selenium_scrape_search(driver)

    # ─── Strategy 3: JavaScript extraction as last resort ───────
    if not results:
        print("     🔄  Trying JavaScript extraction fallback …")
        results = _js_scrape_search(driver)

    return results


def _selenium_scrape_search(driver: webdriver.Chrome) -> list[dict]:
    """Fallback: use Selenium to scrape search results with multiple selector strategies."""
    results = []

    # Try multiple container selectors
    container_selectors = [
        "li.reusable-search__result-container",
        "div.entity-result",
        "li.search-result",
        "div.search-result__wrapper",
        "li[class*='search']",
        "div[class*='entity-result']",
    ]

    cards = []
    for selector in container_selectors:
        try:
            cards = driver.find_elements(By.CSS_SELECTOR, selector)
            if cards:
                print(f"     ✅  Found {len(cards)} cards using: {selector}")
                break
        except Exception:
            continue

    for card in cards:
        try:
            # Try multiple approaches to find name & profile link
            link_el = None
            link_selectors = [
                "a[href*='/in/']",
                "a.app-aware-link[href*='/in/']",
                "span.entity-result__title-text a",
                "a.search-result__result-link",
            ]
            for sel in link_selectors:
                try:
                    link_el = card.find_element(By.CSS_SELECTOR, sel)
                    if link_el:
                        break
                except NoSuchElementException:
                    continue

            if not link_el:
                continue

            raw_name = safe_text(link_el)
            name = clean_name(raw_name)
            profile_link = link_el.get_attribute("href")
            if profile_link:
                profile_link = profile_link.split("?")[0]

            if not name or name.lower() == "linkedin member":
                continue

            # Extract headline
            headline = ""
            headline_selectors = [
                "div.entity-result__primary-subtitle",
                "div.entity-result__summary",
                "p.entity-result__summary",
                "div.search-result__info div.subline-level-1",
                "div[class*='subtitle']",
            ]
            for sel in headline_selectors:
                try:
                    h_el = card.find_element(By.CSS_SELECTOR, sel)
                    headline = safe_text(h_el)
                    if headline:
                        break
                except NoSuchElementException:
                    continue

            results.append({
                "name": name,
                "profile_link": profile_link,
                "headline": headline,
            })

        except (StaleElementReferenceException, Exception):
            continue

    return results


def _js_scrape_search(driver: webdriver.Chrome) -> list[dict]:
    """Ultimate fallback: use JavaScript to extract all /in/ links from the page."""
    results = []
    try:
        js_code = """
        var results = [];
        var links = document.querySelectorAll('a[href*="/in/"]');
        var seen = new Set();
        links.forEach(function(link) {
            var href = link.href.split('?')[0];
            if (seen.has(href) || !href.includes('/in/')) return;
            seen.add(href);

            var name = '';
            // Try aria-hidden span inside the link
            var nameSpan = link.querySelector('span[aria-hidden="true"]');
            if (nameSpan) {
                name = nameSpan.textContent.trim();
            } else {
                name = link.textContent.trim().split('\\n')[0].trim();
            }

            // Skip junk
            if (!name || name.length < 2 || name.toLowerCase() === 'linkedin member') return;
            if (name.toLowerCase().includes('view all') || name.toLowerCase().includes('see all')) return;

            // Try to find headline from parent li
            var headline = '';
            var parentLi = link.closest('li');
            if (parentLi) {
                var subtitle = parentLi.querySelector('[class*="primary-subtitle"], [class*="subtitle"], [class*="summary"]');
                if (subtitle) {
                    headline = subtitle.textContent.trim();
                }
            }

            results.push({
                name: name,
                profile_link: href,
                headline: headline || ''
            });
        });
        return results;
        """
        js_results = driver.execute_script(js_code)
        if js_results:
            for r in js_results:
                name = clean_name(r.get("name", ""))
                if name and name.lower() != "linkedin member":
                    results.append({
                        "name": name,
                        "profile_link": r.get("profile_link", ""),
                        "headline": r.get("headline", ""),
                    })
    except Exception as e:
        print(f"     ❌  JavaScript extraction failed: {e}")

    return results


# ═══════════════════════════════════════════════════════════════
#  Profile Detail Extraction (using BeautifulSoup)
# ═══════════════════════════════════════════════════════════════

def extract_profile_details(driver: webdriver.Chrome, profile_url: str) -> dict:
    """
    Visit a profile page and extract education details and contact info.
    Returns a dict with: college_name, course, email, phone.
    """
    details = {"college_name": "", "course": "", "email": "", "phone": ""}

    try:
        driver.get(profile_url)
        random_delay(config.PROFILE_DELAY_MIN, config.PROFILE_DELAY_MAX)
        human_scroll(driver, scrolls=3)

        # Get page source and parse with BS4
        soup = BeautifulSoup(driver.page_source, "html.parser")
        page_text = soup.get_text(separator="\n", strip=True)

        # ── Extract education section ──────────────────
        try:
            # Strategy 1: Find the education section by ID
            edu_section = soup.find("section", id="education")

            # Strategy 2: Find section with "Education" heading
            if not edu_section:
                for section in soup.find_all("section"):
                    heading = section.find(["h2", "h3"])
                    if heading and "education" in heading.get_text(strip=True).lower():
                        edu_section = section
                        break

            # Strategy 3: Look for div with education in data-section
            if not edu_section:
                edu_section = soup.find("div", attrs={"data-section": "educationsDetails"})

            if edu_section:
                # Find all education items
                edu_items = edu_section.find_all("li")
                if not edu_items:
                    edu_items = [edu_section]

                for item in edu_items:
                    item_text = item.get_text(separator="\n", strip=True)

                    # Check if this education entry matches our target courses
                    matched_course = ""
                    for course in config.TARGET_COURSES:
                        if course.lower() in item_text.lower():
                            matched_course = course
                            break

                    if matched_course:
                        # Extract college name — usually the first bold/heading element
                        college = ""

                        # Try: <span class="t-bold"> or similar
                        bold_el = item.find("span", class_=re.compile(r"t-bold|t-16"))
                        if bold_el:
                            inner = bold_el.find("span", attrs={"aria-hidden": "true"})
                            college = (inner or bold_el).get_text(strip=True)

                        # Fallback: first non-empty line
                        if not college:
                            lines = [l.strip() for l in item_text.split("\n") if l.strip()]
                            if lines:
                                college = lines[0]

                        details["college_name"] = college
                        details["course"] = matched_course
                        break

            # Fallback: scan the whole page text
            if not details["course"]:
                for course in config.TARGET_COURSES:
                    if course.lower() in page_text.lower():
                        details["course"] = course
                        break

            # Fallback college: try to find from headline / About section
            if not details["college_name"] and details["course"]:
                # Look in the page for lines near the course mention
                lines = page_text.split("\n")
                for i, line in enumerate(lines):
                    if details["course"].lower() in line.lower():
                        # College name is usually right before or after the course
                        if i > 0:
                            candidate = lines[i - 1].strip()
                            if len(candidate) > 3 and len(candidate) < 100:
                                details["college_name"] = candidate
                        break

        except Exception as e:
            print(f"     ⚠️  Education extraction error: {e}")

        # ── Extract contact info ───────────────────────
        try:
            contact_url = profile_url.rstrip("/") + "/overlay/contact-info/"
            driver.get(contact_url)
            time.sleep(3)

            # Parse contact overlay with BS4
            contact_soup = BeautifulSoup(driver.page_source, "html.parser")
            contact_text = contact_soup.get_text(separator="\n", strip=True)

            # Extract email — look for mailto: links first
            email_link = contact_soup.find("a", href=re.compile(r"mailto:"))
            if email_link:
                details["email"] = email_link["href"].replace("mailto:", "").strip()
            else:
                # Regex fallback on all visible text
                email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', contact_text)
                if email_match:
                    details["email"] = email_match.group()

            # Extract phone — look for tel: links first
            phone_link = contact_soup.find("a", href=re.compile(r"tel:"))
            if phone_link:
                details["phone"] = phone_link["href"].replace("tel:", "").strip()
            else:
                # Look for phone section
                phone_section = contact_soup.find("section", class_=re.compile(r"ci-phone|phone"))
                if phone_section:
                    phone_text = phone_section.get_text(strip=True)
                    phone_match = re.search(r'[\+]?[\d\s\-\(\)]{10,}', phone_text)
                    if phone_match:
                        details["phone"] = phone_match.group().strip()
                else:
                    # Regex on full text
                    phone_match = re.search(r'[\+]?[\d\s\-\(\)]{10,}', contact_text)
                    if phone_match:
                        details["phone"] = phone_match.group().strip()

            # Go back to the profile page
            driver.back()
            time.sleep(1)

        except Exception as e:
            # Contact info not accessible — very common for non-connections
            if "timeout" not in str(e).lower():
                print(f"     ⚠️  Contact info extraction error: {e}")

    except WebDriverException as e:
        print(f"     ❌  Error visiting profile {profile_url}: {e}")

    return details


# ═══════════════════════════════════════════════════════════════
#  Main Orchestrator
# ═══════════════════════════════════════════════════════════════

def main():
    # Load environment variables
    load_dotenv()
    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")

    if not email or not password or email == "your_email@example.com":
        print("❌  Please set your LinkedIn credentials in the .env file!")
        print("    LINKEDIN_EMAIL=your_email@example.com")
        print("    LINKEDIN_PASSWORD=your_password_here")
        sys.exit(1)

    print("=" * 60)
    print("  LinkedIn Profile Scraper Agent")
    print("  Target: BBA / B.Com / BTech — Class of 2024 & 2025")
    print("=" * 60)

    driver = create_driver()

    try:
        # Step 1: Login
        if not linkedin_login(driver, email, password):
            print("❌  Login failed. Exiting.")
            driver.quit()
            sys.exit(1)

        # Step 2: Search and collect profile URLs
        all_profiles = {}  # url -> profile_data (de-duplication)
        total_scraped = 0

        for query in config.SEARCH_QUERIES:
            if total_scraped >= config.MAX_PROFILES:
                print(f"\n🛑  Reached maximum profile limit ({config.MAX_PROFILES}). Stopping.")
                break

            print(f"\n🔍  Searching: \"{query}\"")

            for page in range(1, config.MAX_PAGES_PER_QUERY + 1):
                if total_scraped >= config.MAX_PROFILES:
                    break

                url = build_search_url(query, page)
                print(f"     Page {page}: {url}")
                driver.get(url)
                random_delay(config.PAGE_DELAY_MIN, config.PAGE_DELAY_MAX)

                # Check if we're being blocked
                if "authwall" in driver.current_url.lower():
                    print("     ⚠️  Hit auth wall. Re-logging …")
                    linkedin_login(driver, email, password)
                    driver.get(url)
                    random_delay(3, 5)

                results = scrape_search_page(driver)

                if not results:
                    print(f"     ❌  No results on page {page}. Moving to next query.")
                    break

                print(f"     ✅  Found {len(results)} profiles on this page.")
                for r in results:
                    print(f"        • {r['name']}  →  {r['profile_link']}")

                for r in results:
                    link = r.get("profile_link", "")
                    if link and link not in all_profiles:
                        all_profiles[link] = {
                            "name": r["name"],
                            "profile_link": link,
                            "headline": r.get("headline", ""),
                            "email": "",
                            "phone": "",
                            "college_name": "",
                            "course": "",
                        }
                        total_scraped += 1

                random_delay(1, 3)

        print(f"\n📋  Total unique profiles found: {len(all_profiles)}")

        if not all_profiles:
            print("\n❌  No profiles were found. This could mean:")
            print("    1. LinkedIn's page structure changed — check the console for errors")
            print("    2. You were logged out or rate-limited")
            print("    3. The search queries returned no results")
            driver.quit()
            sys.exit(1)

        # Step 3: Visit each profile to extract details
        profiles_list = list(all_profiles.values())
        for idx, profile in enumerate(profiles_list, start=1):
            if idx > config.MAX_PROFILES:
                break

            print(f"\n👤  [{idx}/{len(profiles_list)}] Visiting: {profile['name']}")
            print(f"     {profile['profile_link']}")

            details = extract_profile_details(driver, profile["profile_link"])

            profile["email"] = details["email"]
            profile["phone"] = details["phone"]
            profile["college_name"] = details["college_name"]
            profile["course"] = details["course"] or profile.get("headline", "")[:50]

            # Print progress
            if details["college_name"]:
                print(f"     🎓 {details['college_name']} — {details['course']}")
            if details["email"]:
                print(f"     📧 {details['email']}")
            if details["phone"]:
                print(f"     📱 {details['phone']}")
            if not details["college_name"] and not details["email"]:
                print(f"     ℹ️  Limited data (headline: {profile.get('headline', 'N/A')[:60]})")

            # Periodic save every 20 profiles (safety net)
            if idx % 20 == 0:
                print(f"\n💾  Auto-saving progress ({idx} profiles so far) …")
                export_to_excel(profiles_list[:idx], config.OUTPUT_FILE)

        # Step 4: Final export
        print("\n" + "=" * 60)
        print("  Exporting all data to Excel …")
        print("=" * 60)
        export_to_excel(profiles_list, config.OUTPUT_FILE)

    except KeyboardInterrupt:
        print("\n\n⛔  Interrupted by user. Saving collected data …")
        profiles_list = list(all_profiles.values())
        if profiles_list:
            export_to_excel(profiles_list, config.OUTPUT_FILE)
        else:
            print("     No data to save.")

    except Exception as e:
        print(f"\n❌  Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        profiles_list = list(all_profiles.values())
        if profiles_list:
            print("     Saving whatever data was collected …")
            export_to_excel(profiles_list, config.OUTPUT_FILE)

    finally:
        print("\n🔒  Closing browser …")
        driver.quit()

    print("\n🎉  Done! Open the file to see your scraped profiles:")
    print(f"     {os.path.abspath(config.OUTPUT_FILE)}")


if __name__ == "__main__":
    main()

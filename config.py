"""
Configuration for LinkedIn Profile Scraper
"""

# ──────────────────────────────────────────────
# Search Parameters
# ──────────────────────────────────────────────

# Target courses to search for
TARGET_COURSES = ["BBA", "B.Com", "BTech", "B.Tech", "Bachelor of Business Administration",
                  "Bachelor of Commerce", "Bachelor of Technology"]

# Target graduation years
TARGET_YEARS = [2024, 2025]

# Search queries used on LinkedIn People Search
# Each query will be searched separately, results are merged and de-duplicated
SEARCH_QUERIES = [
    "BBA 2024",
    "BBA 2025",
    "B.Com 2024",
    "B.Com 2025",
    "BTech 2024",
    "BTech 2025",
    "B.Tech 2024",
    "B.Tech 2025",
]

# Maximum number of search result pages to scrape per query (each page ~ 10 results)
MAX_PAGES_PER_QUERY = 5

# Maximum total profiles to scrape (safety limit)
MAX_PROFILES = 200

# ──────────────────────────────────────────────
# Timing & Anti-Detection
# ──────────────────────────────────────────────

# Delay range (seconds) between visiting individual profiles
PROFILE_DELAY_MIN = 3
PROFILE_DELAY_MAX = 7

# Delay range (seconds) between paginating search results
PAGE_DELAY_MIN = 4
PAGE_DELAY_MAX = 8

# Delay (seconds) after login — wait for page to fully load
LOGIN_WAIT = 5

# Timeout (seconds) to wait for manual OTP/CAPTCHA entry
OTP_TIMEOUT = 120

# ──────────────────────────────────────────────
# Output
# ──────────────────────────────────────────────

OUTPUT_FILE = "linkedin_profiles.xlsx"

# 🔍 LinkedIn Profile Scraper Tool

An automated LinkedIn profile scraper that searches for graduates by course and batch year, extracts profile data, and exports it to a styled Excel spreadsheet.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-4.27-green?logo=selenium&logoColor=white)
![License](https://img.shields.io/badge/License-Educational-yellow)

---

## ✨ Features

- **Automated LinkedIn Search** — Searches for graduates by course type (BBA, B.Com, BTech, B.Tech) and batch year (2024–2025)
- **Smart Profile Extraction** — Extracts name, email, phone, college, course, and profile link
- **Multi-Strategy Scraping** — Uses BeautifulSoup, Selenium CSS selectors, and JS-based extraction as fallbacks
- **Human-Like Behavior** — Randomized delays (3–7s between profiles, 4–8s between pages), random scrolling, and anti-detection measures
- **OTP/CAPTCHA Handling** — Detects verification prompts and allows 120 seconds for manual entry
- **Duplicate Detection** — Prevents scraping the same profile twice across multiple queries
- **Styled Excel Export** — Outputs data to a formatted `.xlsx` file with proper fonts, borders, and alignment
- **Safety Limits** — Max 200 profiles per run to prevent excessive scraping

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.8+ | Core language |
| Selenium 4.27.1 | Browser automation |
| BeautifulSoup4 | HTML parsing |
| openpyxl | Excel file generation |
| webdriver-manager | Chrome WebDriver management |
| python-dotenv | Environment variable management |

---

## 📁 Project Structure

```
linkindin-scaper-tool/
├── scraper.py          # Main scraper logic (login, search, extraction)
├── config.py           # Configuration (courses, delays, search queries)
├── exporter.py         # Styled Excel export functionality
├── requirements.txt    # Python dependencies
├── .gitignore          # Excludes .env, __pycache__, output files
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Chrome installed
- LinkedIn account credentials

### Installation

```bash
# Clone the repository
git clone https://github.com/dipk2003/linkindin-scaper-tool.git
cd linkindin-scaper-tool

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Edit `config.py` to customize:

```python
TARGET_COURSES = ["BBA", "B.Com", "BTech", "B.Tech"]
TARGET_YEARS = [2024, 2025]
MAX_PAGES_PER_QUERY = 5
MAX_TOTAL_PROFILES = 200
PROFILE_DELAY = (3, 7)
PAGE_DELAY = (4, 8)
OTP_TIMEOUT = 120
```

Create a `.env` file:

```env
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password
```

### Run

```bash
python scraper.py
```

Output saved to `linkedin_profiles.xlsx`.

---

## 📊 Output Format

| Name | Email | Phone | Profile Link | College Name | Course |
|---|---|---|---|---|---|
| John Doe | john@email.com | 9876543210 | linkedin.com/in/... | XYZ University | BTech 2024 |

---

## ⚙️ How It Works

```
LinkedIn Login (with OTP/CAPTCHA handling)
    ↓
Search Queries (BBA 2024, BTech 2025, etc.)
    ↓
For Each Search Result Page:
├── Strategy 1: BeautifulSoup parsing
├── Strategy 2: Selenium CSS selectors (fallback)
└── Strategy 3: JavaScript extraction (final fallback)
    ↓
Extract Profile Details (name, email, phone, college)
    ↓
Deduplicate Results
    ↓
Export to Styled Excel (.xlsx)
```

---

## 🛡️ Safety and Ethics

- **Rate Limiting** — Randomized delays between all actions
- **Profile Cap** — Maximum 200 profiles per execution
- **Human Simulation** — Random scrolling and mouse movements
- **Educational Purpose** — Built for learning and research

---

## ⚠️ Disclaimer

This project is for **educational purposes only**. Automated scraping of LinkedIn may violate their Terms of Service. Use at your own risk.

---

Made with ❤️ by [Dipanshu Pandey](https://github.com/dipk2003)
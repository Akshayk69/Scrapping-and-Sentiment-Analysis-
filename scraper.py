import os
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


OUTPUT_CSV = "results.csv"


def run_scraper(query: str = "topgun maverick trailer", max_results: int = 10):
    """Run a simple YouTube search scraper and save results to a CSV file.

    This script is intended to run on a CI runner (GitHub Actions) with
    a headless Chromium/Chrome binary available. It uses webdriver-manager
    to download the matching chromedriver.
    """

    chrome_options = Options()
    # Use headless mode suitable for modern Chrome versions
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    # If the runner provides CHROME_BIN (we set this in the workflow), use it
    chrome_bin = os.environ.get("CHROME_BIN")
    if chrome_bin:
        chrome_options.binary_location = chrome_bin

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    records = []
    try:
        url = "https://www.youtube.com"
        driver.get(url)
        driver.implicitly_wait(5)

        # Locate the search box and submit the query
        try:
            search = driver.find_element(By.XPATH, "//input[@id='search']")
        except Exception:
            # fallback xpath from notebook (fragile)
            search = driver.find_element(By.XPATH, "/html/body/ytd-app/div[1]/div/ytd-masthead/div[3]/div[2]/ytd-searchbox/form/div[1]/div[1]/input")

        search.clear()
        search.send_keys(query)
        # click the search button
        try:
            button = driver.find_element(By.XPATH, "//button[@id='search-icon-legacy']")
        except Exception:
            button = driver.find_element(By.XPATH, "/html/body/ytd-app/div[1]/div/ytd-masthead/div[3]/div[2]/ytd-searchbox/button")
        button.click()

        time.sleep(3)

        # Collect video results (titles and urls)
        videos = driver.find_elements(By.CSS_SELECTOR, "a#video-title")
        for v in videos[:max_results]:
            title = v.get_attribute("title") or v.text
            href = v.get_attribute("href")
            records.append({"title": title, "url": href})

        # Save to CSV with timestamp
        if records:
            df = pd.DataFrame(records)
            df["scraped_at"] = datetime.utcnow().isoformat()
            df.to_csv(OUTPUT_CSV, index=False)
            print(f"Saved {len(df)} rows to {OUTPUT_CSV}")
        else:
            print("No results found; writing empty CSV")
            pd.DataFrame(columns=["title", "url", "scraped_at"]).to_csv(OUTPUT_CSV, index=False)

    except Exception as e:
        print("Scraper error:", str(e))
        # Save an error marker file
        pd.DataFrame([{"error": str(e), "scraped_at": datetime.utcnow().isoformat()}]).to_csv(OUTPUT_CSV, index=False)
        raise

    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    # Allow overriding via env vars
    q = os.environ.get("SCRAPER_QUERY", "topgun maverick trailer")
    try:
        max_r = int(os.environ.get("SCRAPER_MAX_RESULTS", "10"))
    except Exception:
        max_r = 10
    run_scraper(q, max_r)

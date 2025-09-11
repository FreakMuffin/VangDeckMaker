import os
import json
import time
import random
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Load JSON
with open("ridecore_cards000.json", "r", encoding="utf-8") as f:
    cards = json.load(f)

# Base folder for images
base_dir = "cardimg"
os.makedirs(base_dir, exist_ok=True)

# --- Setup headless Chrome ---
chrome_options = Options()
chrome_options.add_argument("--headless=new")  # headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def polite_wait(base=1, jitter=2):
    """Random delay to look like human browsing"""
    delay = base + random.uniform(0, jitter)
    print(f"⏳ Waiting {delay:.2f}s...")
    time.sleep(delay)

def fetch_image_with_selenium(url):
    """Use Selenium to load the image and get the final src"""
    driver.get(url)
    time.sleep(1.5)  # let the image load
    # Get final rendered src
    soup = BeautifulSoup(driver.page_source, "html.parser")
    img_tag = soup.find("img")
    if img_tag and img_tag.get("src"):
        return img_tag["src"]
    return None

def download_image(url, filepath, retries=5):
    headers = {"User-Agent": "Mozilla/5.0"}
    for attempt in range(1, retries + 1):
        try:
            res = requests.get(url, headers=headers, timeout=60, stream=True)
            res.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in res.iter_content(1024):
                    f.write(chunk)
            return True
        except Exception as e:
            wait = 2 ** attempt + random.uniform(0, 1)
            print(f"⚠️ Attempt {attempt} failed for {url}: {e}. Retrying in {wait:.2f}s...")
            time.sleep(wait)
    return False

# Function to process one set
def process_set(set_code):
    print(f"\n🔹 Processing {set_code}")
    cards_to_download = [card for card in cards if card["set"] == set_code]
    missing_cards = True

    while missing_cards:
        missing_cards = False
        for card in cards_to_download:
            number = card["number"]
            img_url = card.get("image")
            set_dir = os.path.join(base_dir, set_code)
            os.makedirs(set_dir, exist_ok=True)
            img_path = os.path.join(set_dir, f"{number}.png")

            if os.path.exists(img_path):
                card["image"] = img_path.replace("\\", "/")
                continue

            if img_url:
                # Use Selenium to fetch final image URL
                final_img_url = fetch_image_with_selenium(img_url)
                if final_img_url:
                    success = download_image(final_img_url, img_path)
                    if success:
                        print(f"✅ Downloaded {img_path}")
                        card["image"] = img_path.replace("\\", "/")
                    else:
                        print(f"❌ Could not download {img_path}, will retry later")
                        missing_cards = True
                else:
                    print(f"❌ Could not fetch image from {img_url}")
                    missing_cards = True
            else:
                card["image"] = None

            polite_wait(base=1, jitter=2)

# Loop through all sets BS1–BS11
for i in range(1, 12):
    set_code = f"BS{i}"
    process_set(set_code)

# Save updated JSON
with open("ridecore_cards_local.json", "w", encoding="utf-8") as f:
    json.dump(cards, f, indent=2, ensure_ascii=False)

driver.quit()
print("\n🎉 Finished! All sets processed.")

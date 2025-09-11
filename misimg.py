import os
import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# --- CONFIG ---
BASE_SAVE_DIR = "cards"
DB_FILE = "cards_db.json"
os.makedirs(BASE_SAVE_DIR, exist_ok=True)

# --- Mapping ---
set_name_mapping = {
    "BS1": "Descent_of_the_King_of_Knights",
    "BS2": "Onslaught_of_Dragon_Souls",
    "BS3": "Demonic_Lord_Invasion",
    "BS4": "Eclipse_of_Illusionary_Shadows",
    "BS5": "Awakening_of_Twin_Blades",
    "BS6": "Breaker_of_Limits",
    "BS7": "Rampage_of_the_Beast_King",
    "BS8": "Blue_Storm_Armada",
    "BS9": "Clash_of_the_Knights_%26_Dragons",
    "BS10": "Triumphant_Return_of_the_King_of_Knights",
    "BS11": "Seal_Dragons_Unleashed"
}

# --- Setup headless Chrome ---
options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(options=options)

def scroll_to_bottom(driver, pause_time=2):
    """Scrolls until no more new content is loaded."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def download_set(set_code, set_name, db):
    url = f"https://vanguardcard.io/pack/?search={set_name.replace('_', '%20')}"
    print(f"\nProcessing {set_code}: {url}")

    # Make directory for this set
    save_dir = os.path.join(BASE_SAVE_DIR, set_code)
    os.makedirs(save_dir, exist_ok=True)

    driver.get(url)
    scroll_to_bottom(driver, pause_time=2)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    figures = soup.find_all("figure", class_="card-figure")

    if not figures:
        print(f"No cards found for {set_code}.")
        return

    for idx, fig in enumerate(figures, start=1):
        img = fig.find("img")
        if not img:
            continue

        card_name = img.get("title", f"Unknown_{idx}")

        # Get image URL (prefer real one over card back)
        img_url = img.get("src")
        if "CardBack.jpg" in img_url:
            data_src = img.get("data-src")
            if data_src:
                img_url = data_src

        if not img_url:
            continue

        try:
            r = requests.get(img_url, timeout=10)
            if r.status_code == 200:
                file_name = os.path.join(save_dir, f"{idx}.jpg")
                with open(file_name, "wb") as f:
                    f.write(r.content)
                print(f"Downloaded {set_code} card {idx}: {card_name}")

                # Save to DB
                db.append({
                    "set": set_code,
                    "index": idx,
                    "name": card_name,
                    "image": file_name.replace("\\", "/")
                })
            else:
                print(f"Failed {set_code} card {idx}: HTTP {r.status_code}")
        except Exception as e:
            print(f"Error downloading {img_url}: {e}")

# --- Main ---
cards_db = []

for code, name in set_name_mapping.items():
    download_set(code, name, cards_db)

# Save DB file
with open(DB_FILE, "w", encoding="utf-8") as f:
    json.dump(cards_db, f, indent=2, ensure_ascii=False)

print(f"\nDone! Saved metadata for {len(cards_db)} cards into {DB_FILE}")
driver.quit()

import requests
from bs4 import BeautifulSoup
import json
import os
import time

# Load existing DB
db_file = "ridecore_cards.json"
if os.path.exists(db_file):
    with open(db_file, "r", encoding="utf-8") as f:
        all_cards = json.load(f)
else:
    all_cards = []

# Map card name -> entry for quick lookup
card_map = {c["name"]: c for c in all_cards}

set_urls = [
    "https://cardfight.fandom.com/wiki/Booster_Set_1:_Descent_of_the_King_of_Knights",
    "https://cardfight.fandom.com/wiki/Booster_Set_2:_Onslaught_of_Dragon_Souls",
    "https://cardfight.fandom.com/wiki/Booster_Set_3:_Demonic_Lord_Invasion",
    "https://cardfight.fandom.com/wiki/Booster_Set_4:_Eclipse_of_Illusionary_Shadows",
    "https://cardfight.fandom.com/wiki/Booster_Set_5:_Awakening_of_Twin_Blades",
    "https://cardfight.fandom.com/wiki/Booster_Set_6:_Breaker_of_Limits",
    "https://cardfight.fandom.com/wiki/Booster_Set_7:_Rampage_of_the_Beast_King",
    "https://cardfight.fandom.com/wiki/Booster_Set_8:_Blue_Storm_Armada",
    "https://cardfight.fandom.com/wiki/Booster_Set_9:_Clash_of_the_Knights_%26_Dragons",
    "https://cardfight.fandom.com/wiki/Booster_Set_10:_Triumphant_Return_of_the_King_of_Knights",
    "https://cardfight.fandom.com/wiki/Booster_Set_11:_Seal_Dragons_Unleashed"
]

# Numbering continues from last card in DB
card_number = max([c["number"] for c in all_cards], default=0) + 1

def get_card_effect(card_url):
    """Scrape Card Effect(s) section from individual card page."""
    try:
        res = requests.get(card_url, timeout=15)
        if res.status_code != 200:
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        effect_table = soup.find("table", class_="effect")
        effect_list = []
        if effect_table:
            td = effect_table.find("td")
            if td:
                for line in td.stripped_strings:
                    line = line.strip()
                    if line:
                        effect_list.append(line)
        return effect_list

    except Exception as e:
        print(f"⚠️ Could not scrape effects from {card_url}: {e}")
        return []

for url in set_urls:
    print(f"📦 Scraping set page: {url}")
    res = requests.get(url, timeout=15)
    soup = BeautifulSoup(res.text, "html.parser")

    set_name = soup.find("h1", {"class": "page-header__title"}).get_text(strip=True)

    tables = [t for t in soup.find_all("table") if "sortable" in t.get("class", [])]

    for table in tables:
        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 5:
                card_name = cols[1].get_text(strip=True).replace("\xa0", " ")

                # Get individual card page link
                link_tag = cols[1].find("a")
                card_url = (
                    "https://cardfight.fandom.com" + link_tag["href"]
                    if link_tag
                    else None
                )

                # Scrape card effects if link available
                effects = get_card_effect(card_url) if card_url else []

                if card_name in card_map:
                    # Update existing card only with effect field
                    card_map[card_name]["effect"] = effects
                    print(f"  🔄 Updated {card_name} ({len(effects)} effects)")
                else:
                    # New card: add fully
                    grade = cols[2].get_text(strip=True)
                    clan = cols[3].get_text(strip=True)
                    ctype = cols[4].get_text(strip=True)
                    card_entry = {
                        "number": card_number,
                        "name": card_name,
                        "grade": grade,
                        "clan": clan,
                        "type": ctype,
                        "set": set_name,
                        "image": None,  # leave for later image scripts
                        "effect": effects,
                    }
                    all_cards.append(card_entry)
                    card_map[card_name] = card_entry
                    card_number += 1
                    print(f"  ➕ Added {card_name} ({len(effects)} effects)")

                time.sleep(0.5)  # polite delay

# Save updated DB
with open(db_file, "w", encoding="utf-8") as f:
    json.dump(all_cards, f, indent=2, ensure_ascii=False)

print(f"✅ Updated DB: {len(all_cards)} cards total")

import requests
from bs4 import BeautifulSoup
import json
import time

base_url = "https://cardfight.fandom.com"

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

all_cards = []
card_number = 1

for url in set_urls:
    print(f"Scraping set page: {url}")
    res = requests.get(url)
    soup = BeautifulSoup(res.text, 'html.parser')

    set_name = soup.find("h1", {"class": "page-header__title"}).get_text(strip=True)
    tables = [t for t in soup.find_all("table") if "sortable" in t.get("class", [])]

    for table in tables:
        rows = table.find_all("tr")[1:]  # skip header row
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 5:
                link_tag = cols[1].find("a")
                card_name = cols[1].get_text(strip=True).replace('\xa0', ' ')
                grade = cols[2].get_text(strip=True)
                clan = cols[3].get_text(strip=True)
                ctype = cols[4].get_text(strip=True)

                # Default no image
                image_url = None
                if link_tag and link_tag.get("href"):
                    card_page_url = base_url + link_tag["href"]
                    try:
                        card_res = requests.get(card_page_url)
                        card_soup = BeautifulSoup(card_res.text, "html.parser")
                        img_tag = card_soup.select_one("a.image img")
                        if img_tag and img_tag.get("src"):
                            image_url = img_tag["src"]
                        # Delay between requests to avoid stressing the server
                        time.sleep(0.5)
                    except Exception as e:
                        print(f"⚠️ Failed to fetch image for {card_name}: {e}")

                all_cards.append({
                    "number": card_number,
                    "name": card_name,
                    "grade": grade,
                    "clan": clan,
                    "type": ctype,
                    "set": set_name,
                    "image": image_url
                })
                card_number += 1

# Save to JSON
with open("ridecore_cards.json", "w", encoding="utf-8") as f:
    json.dump(all_cards, f, indent=2, ensure_ascii=False)

print(f"✅ Scraped {len(all_cards)} cards with images (delay added).")

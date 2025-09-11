import os
import json
import requests
import time

# Load JSON
with open("ridecore_cards000.json", "r", encoding="utf-8") as f:
    cards = json.load(f)

# Base folder for images
base_dir = "cardimg"
os.makedirs(base_dir, exist_ok=True)

# List to store failed/missing cards
failed_cards = []

# Function to process one set
def process_set(set_code):
    print(f"\n🔹 Processing {set_code}")
    cards_to_download = [card for card in cards if card["set"] == set_code]

    for card in cards_to_download:
        number = card["number"]
        img_url = card.get("image")
        set_dir = os.path.join(base_dir, set_code)
        os.makedirs(set_dir, exist_ok=True)
        img_path = os.path.join(set_dir, f"{number}.png")

        if os.path.exists(img_path):
            card["image"] = img_path.replace("\\", "/")
            continue

        # If missing, save to failed_cards list
        if img_url:
            failed_cards.append({
                "set": set_code,
                "number": number,
                "url": img_url
            })
        else:
            failed_cards.append({
                "set": set_code,
                "number": number,
                "url": None
            })

# Loop through all sets BS1–BS11
for i in range(1, 12):
    set_code = f"BS{i}"
    process_set(set_code)

# Save updated JSON for local paths
with open("ridecore_cards_local.json", "w", encoding="utf-8") as f:
    json.dump(cards, f, indent=2, ensure_ascii=False)

# Save list of missing/failed cards
with open("ridecore_missing_cards.json", "w", encoding="utf-8") as f:
    json.dump(failed_cards, f, indent=2, ensure_ascii=False)

print(f"\n🎉 Finished! Missing cards saved: {len(failed_cards)}")

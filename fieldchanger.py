import os
import json

def update_image_paths(json_file, output_file, base_dir="cardimg"):
    # Load JSON
    with open(json_file, "r", encoding="utf-8") as f:
        cards = json.load(f)

    for card in cards:
        set_code = card.get("set")
        number = card.get("number")

        if set_code and number is not None:
            # Build new local path
            local_path = os.path.join(base_dir, set_code, f"{number}.png")
            # Use forward slashes for portability
            card["image"] = local_path.replace("\\", "/")

    # Save updated JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)

    print(f"✅ Updated image paths in {output_file}")

if __name__ == "__main__":
    update_image_paths("ridecore_cards.json", "ridecore_cards_local.json")

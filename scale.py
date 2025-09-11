import os
from PIL import Image

def upscale_small_images(base_dir, sets, target_width=700):
    """
    Upscales images smaller than target_width in each set folder to target_width
    using Pillow LANCZOS, keeping the aspect ratio.
    """
    for set_name in sets:
        set_path = os.path.join(base_dir, set_name)
        if not os.path.isdir(set_path):
            print(f"Skipping {set_name} (not a directory)")
            continue

        print(f"\nScanning {set_name}...")
        upscaled_count = 0

        for filename in os.listdir(set_path):
            filepath = os.path.join(set_path, filename)

            if not os.path.isfile(filepath):
                continue

            try:
                with Image.open(filepath) as img:
                    width, height = img.size
                    if width < target_width:
                        # Calculate new height to maintain aspect ratio
                        new_height = int(height * (target_width / width))
                        upscaled = img.resize((target_width, new_height), Image.LANCZOS)
                        upscaled.save(filepath)  # overwrite original
                        upscaled_count += 1
                        print(f"  Upscaled {filename} from {width}px to {target_width}px")
            except Exception as e:
                print(f"  Skipping {filename}: {e}")

        if upscaled_count == 0:
            print(f"  No images needed upscaling in {set_name}.")
        else:
            print(f"  Upscaled {upscaled_count} images in {set_name}.")

if __name__ == "__main__":
    base_dir = os.path.join(os.getcwd(), "cardimg")  # parent folder of sets
    # Get all subdirectories in cardimg
    sets = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    upscale_small_images(base_dir, sets, target_width=700)

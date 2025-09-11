import os
import math
from tkinter import Tk, filedialog, Button, Label
from PIL import Image, ImageTk

CARD_WIDTH = 677
CARD_HEIGHT = 991
COLS = 3
ROWS = 3
MARGIN = 50
PADDING = 30
TEMPLATE_WIDTH = MARGIN * 2 + COLS * CARD_WIDTH + (COLS - 1) * PADDING
TEMPLATE_HEIGHT = MARGIN * 2 + ROWS * CARD_HEIGHT + (ROWS - 1) * PADDING

def generate_proxy_sheets(image_paths):
    batches = math.ceil(len(image_paths) / (ROWS * COLS))
    for batch_num in range(batches):
        output_image = Image.new("RGB", (TEMPLATE_WIDTH, TEMPLATE_HEIGHT), "white")
        batch_files = image_paths[batch_num * ROWS * COLS : (batch_num + 1) * ROWS * COLS]
        for idx, card_path in enumerate(batch_files):
            card_img = Image.open(card_path).convert("RGB")
            card_img = card_img.resize((CARD_WIDTH, CARD_HEIGHT))
            row = idx // COLS
            col = idx % COLS
            x = MARGIN + col * (CARD_WIDTH + PADDING)
            y = MARGIN + row * (CARD_HEIGHT + PADDING)
            output_image.paste(card_img, (x, y))
        output_filename = f"deck_name{batch_num + 1}.png"
        output_image.save(output_filename, dpi=(300, 300))
        print(f"Saved: {output_filename}")

def select_folder():
    folder_path = filedialog.askdirectory()
    if folder_path:
        supported_exts = (".png", ".jpg", ".jpeg")
        image_paths = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.lower().endswith(supported_exts)
        ]
        if image_paths:
            image_paths.sort()  # Optional: consistent order
            generate_proxy_sheets(image_paths)
            status_label.config(text="✅ Sheets generated successfully!")
        else:
            status_label.config(text="⚠️ No image files found in folder.")

# GUI Setup
root = Tk()
root.title("Vanguard Proxy Sheet Generator")

Label(root, text="Select a folder with up to 9 images per sheet.").pack(pady=10)
Button(root, text="Choose Folder", command=select_folder).pack(pady=5)
status_label = Label(root, text="")
status_label.pack(pady=10)

root.mainloop()

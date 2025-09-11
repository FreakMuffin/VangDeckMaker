import sys, os, json, hashlib, math
from collections import Counter
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QLineEdit, QPushButton,
    QSplitter, QScrollArea, QSizePolicy, QMessageBox, QComboBox,
    QFileDialog
)
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, QSize, QTimer
from PIL import Image

# --- Config constants ---
CARD_DB_PATH = "ridecore_cards.json"
REMOTE_BASE = "https://drive.google.com/drive/folders/11bjDuem3_Xf4-yPIXoPk8kpVB3pr1Nqb?usp=sharing"

GALLERY_ICON_W, GALLERY_ICON_H = 100, 140
DECK_ICON_W, DECK_ICON_H = 60, 84

THUMB_DIR = "thumbs_cache"
THUMB_SIZE = (GALLERY_ICON_W, GALLERY_ICON_H)
DEBOUNCE_MS = 300

MAIN_LIMIT = 34
TRIGGER_LIMIT = 16
MAX_COPIES = 4

DECK_FOLDER = "decks"  # Folder to store decks
DECK_EXT = ".deck"     # Custom extension

CARD_WIDTH = 677
CARD_HEIGHT = 991
COLS = 3
ROWS = 3
MARGIN = 50
PADDING = 30
TEMPLATE_WIDTH = MARGIN * 2 + COLS * CARD_WIDTH + (COLS - 1) * PADDING
TEMPLATE_HEIGHT = MARGIN * 2 + ROWS * CARD_HEIGHT + (ROWS - 1) * PADDING


# --- Helpers ---
def load_card_db(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    db = {}
    for c in data:
        c = dict(c)
        trig = c.get("type", "").strip()
        if trig in ["Critical", "Draw", "Stand", "Heal"]:
            c["trigger"] = trig
        else:
            c["trigger"] = None
        db[c["name"]] = c
    return db

def is_trigger(card):
    return card.get("trigger") is not None

def can_go_to_main(card):
    return not is_trigger(card)

def can_go_to_triggers(card):
    return is_trigger(card)

def get_cached_pixmap(path):
    if not path:
        pm = QPixmap(THUMB_SIZE[0], THUMB_SIZE[1])
        pm.fill(Qt.lightGray)
        return pm

    key = hashlib.md5(path.encode("utf-8")).hexdigest()
    thumb_fname = f"{key}.png"
    os.makedirs(THUMB_DIR, exist_ok=True)
    thumb_path = os.path.join(THUMB_DIR, thumb_fname)

    if os.path.exists(thumb_path):
        pm = QPixmap(thumb_path)
        if not pm.isNull():
            return pm

    try:
        im = Image.open(path).convert("RGB")
        im.thumbnail(THUMB_SIZE, Image.LANCZOS)
        thumb = Image.new("RGB", THUMB_SIZE, (255, 255, 255))
        x = (THUMB_SIZE[0] - im.width) // 2
        y = (THUMB_SIZE[1] - im.height) // 2
        thumb.paste(im, (x, y))
        thumb.save(thumb_path, format="PNG")
        pm = QPixmap(thumb_path)
        if not pm.isNull():
            return pm
    except Exception as e:
        print(f"⚠️ Thumbnail creation failed for {path}: {e}")

    try:
        pm = QPixmap(path)
        if pm.isNull():
            raise ValueError("QPixmap failed")
        return pm.scaled(THUMB_SIZE[0], THUMB_SIZE[1],
                         Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception:
        pm = QPixmap(THUMB_SIZE[0], THUMB_SIZE[1])
        pm.fill(Qt.lightGray)
        return pm


# --- Deck Data ---
class Deck:
    def __init__(self):
        self.main = Counter()
        self.triggers = Counter()

    def total_main(self): return sum(self.main.values())
    def total_triggers(self): return sum(self.triggers.values())
    def total(self): return self.total_main() + self.total_triggers()

    def add(self, section, name, card_db):
        card = card_db[name]
        if section == "main":
            if not can_go_to_main(card):
                return False, "Only non-trigger units can be added to Main."
            if self.total_main() >= MAIN_LIMIT:
                return False, f"Main deck is capped at {MAIN_LIMIT}."
            if self.main[name] >= MAX_COPIES:
                return False, f"Max {MAX_COPIES} copies of {name}."
            self.main[name] += 1
            return True, ""
        elif section == "triggers":
            if not can_go_to_triggers(card):
                return False, "Only trigger units can be added to Triggers."
            if self.total_triggers() >= TRIGGER_LIMIT:
                return False, f"Trigger deck is capped at {TRIGGER_LIMIT}."
            if card.get("trigger") == "Over" and self.triggers[name] >= 1:
                return False, "Only 1 OverTrigger allowed."
            if self.triggers[name] >= MAX_COPIES:
                return False, f"Max {MAX_COPIES} copies of {name}."
            self.triggers[name] += 1
            return True, ""
        return False, "Unknown section."

    def remove(self, section, name):
        group = self.main if section == "main" else self.triggers
        if group[name] > 0:
            group[name] -= 1
            if group[name] == 0:
                del group[name]
            return True
        return False


# --- Main Editor ---
class Editor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Deck Editor")
        self.resize(1200, 800)

        try:
            self.card_db = load_card_db(CARD_DB_PATH)
        except Exception as ex:
            QMessageBox.critical(self, "Error", f"Failed to load {CARD_DB_PATH}:\n{ex}")
            sys.exit(1)

        self.deck = Deck()
        self.pixmap_cache = {}

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        # --- Search & Filters ---
        filter_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by name...")
        filter_row.addWidget(QLabel("Search:"))
        filter_row.addWidget(self.search, 2)

        self.filter_grade = QComboBox()
        self.filter_grade.addItems(["Any Grade", "0", "1", "2", "3"])
        filter_row.addWidget(QLabel("Grade:"))
        filter_row.addWidget(self.filter_grade)

        self.filter_trigger = QComboBox()
        self.filter_trigger.addItems(
            ["Any Trigger", "Critical", "Draw", "Stand", "Heal", "Non-Trigger"]
        )
        filter_row.addWidget(QLabel("Trigger:"))
        filter_row.addWidget(self.filter_trigger)
        
        # --- Clan Filter ---
        self.filter_clan = QComboBox()
        # First item is "Any Clan"
        clans = sorted({card.get("clan", "") for card in self.card_db.values() if card.get("clan")})
        self.filter_clan.addItem("Any Clan")
        self.filter_clan.addItems(clans)
        filter_row.addWidget(QLabel("Clan:"))
        filter_row.addWidget(self.filter_clan)
        self.filter_clan.currentIndexChanged.connect(self.refresh_gallery)



        outer.addLayout(filter_row)

        # search debounce
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.refresh_gallery)
        self.search.textChanged.connect(lambda _: self.search_timer.start(DEBOUNCE_MS))
        self.filter_grade.currentIndexChanged.connect(self.refresh_gallery)
        self.filter_trigger.currentIndexChanged.connect(self.refresh_gallery)

        # --- Splitter ---
        splitter = QSplitter()
        outer.addWidget(splitter)

        # Left: Gallery
        self.gallery = QListWidget()
        self.gallery.itemDoubleClicked.connect(self.gallery_double_click)
        splitter.addWidget(self.gallery)

        # --- Lazy load state ---
        self.batch_size = 50       # load 50 cards at a time
        self.loaded_count = 0      # how many are shown right now
        self.filtered_cache = []   # stores last filter results

        # Detect scroll to bottom
        self.gallery.verticalScrollBar().valueChanged.connect(self.check_scroll)


        # Right: Deck lists
        deck_panel = QWidget()
        deck_layout = QVBoxLayout(deck_panel)
        splitter.addWidget(deck_panel)

        # Main row: Main label + grade counters
        main_row = QHBoxLayout()
        self.main_label = QLabel("Main (0/34)")
        main_row.addWidget(self.main_label)

        # Grade counters
        self.grade0_label = QLabel("Grade 0 (0)")
        self.grade0_label.setStyleSheet("color: gray;")
        self.grade1_label = QLabel("Grade 1 (0)")
        self.grade1_label.setStyleSheet("color: green;")
        self.grade2_label = QLabel("Grade 2 (0)")
        self.grade2_label.setStyleSheet("color: red;")
        self.grade3_label = QLabel("Grade 3 (0)")
        self.grade3_label.setStyleSheet("color: blue;")

        main_row.addWidget(self.grade0_label)
        main_row.addWidget(self.grade1_label)
        main_row.addWidget(self.grade2_label)
        main_row.addWidget(self.grade3_label)

        # Add the horizontal row to the vertical deck layout
        deck_layout.addLayout(main_row)
                
        self.main_list = QListWidget()
        deck_layout.addWidget(self.main_list)

        self.trig_label = QLabel("Triggers (0/16)")
        deck_layout.addWidget(self.trig_label)
        self.trig_list = QListWidget()
        deck_layout.addWidget(self.trig_list)
        
        # --- Deck Manager UI ---
        deck_manager_row = QHBoxLayout()
        self.deck_name_input = QLineEdit()
        self.deck_name_input.setPlaceholderText("Enter deck name")
        deck_manager_row.addWidget(self.deck_name_input)

        self.save_deck_btn = QPushButton("Save/Update Deck")
        self.save_deck_btn.clicked.connect(self.save_named_deck)
        deck_manager_row.addWidget(self.save_deck_btn)
        
        self.export_sheets_btn = QPushButton("Export to Proxy")
        self.export_sheets_btn.clicked.connect(self.export_current_deck_to_sheets)
        deck_manager_row.addWidget(self.export_sheets_btn)

        self.deck_dropdown = QComboBox()
        self.deck_dropdown.currentIndexChanged.connect(self.load_selected_deck)
        deck_manager_row.addWidget(self.deck_dropdown)

        deck_layout.addLayout(deck_manager_row)
        
        self.main_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.main_list.customContextMenuRequested.connect(
        lambda pos: self.remove_on_right_click(self.main_list, "main", pos)
        )

        self.trig_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.trig_list.customContextMenuRequested.connect(
        lambda pos: self.remove_on_right_click(self.trig_list, "triggers", pos)
        )

        self.refresh_gallery()
        self.refresh_deck_lists()
        self.refresh_deck_list_dropdown()

        
    def ensure_deck_folder(self):
        os.makedirs(DECK_FOLDER, exist_ok=True)

    def deck_file_path(self, name):
        safe_name = "".join(c for c in name if c.isalnum() or c in "_- ")
        return os.path.join(DECK_FOLDER, f"{safe_name}{DECK_EXT}")

    def refresh_deck_list_dropdown(self):
        self.ensure_deck_folder()
        self.deck_dropdown.blockSignals(True)
        self.deck_dropdown.clear()
        decks = [f[:-len(DECK_EXT)] for f in os.listdir(DECK_FOLDER) if f.endswith(DECK_EXT)]
        self.deck_dropdown.addItems(decks)
        self.deck_dropdown.blockSignals(False)

        # auto-load the first deck if available
        if decks:
            self.deck_dropdown.setCurrentIndex(0)
            self.load_selected_deck(0)

    def save_named_deck(self):
        name = self.deck_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "No Name", "Please enter a deck name.")
            return
        path = self.deck_file_path(name)
        data = {
            "main": dict(self.deck.main),
            "triggers": dict(self.deck.triggers)
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.refresh_deck_list_dropdown()
            QMessageBox.information(self, "Deck Saved", f"Deck '{name}' saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save deck:\n{e}")

    def load_selected_deck(self, index):
        if index < 0:
            return
        name = self.deck_dropdown.currentText()
        path = self.deck_file_path(name)
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.deck.main = Counter(data.get("main", {}))
            self.deck.triggers = Counter(data.get("triggers", {}))
            self.deck_name_input.setText(name)
            self.refresh_deck_lists()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load deck '{name}':\n{e}")
            
    def export_current_deck_to_sheets(self):
        if not self.deck.main and not self.deck.triggers:
            QMessageBox.warning(self, "Empty Deck", "The current deck is empty!")
            return

        # Ask where to save sheets
        folder_path = QFileDialog.getExistingDirectory(self, "Select folder to save sheets")

        if not folder_path:
            return

        # Gather card image paths from the deck
        image_paths = []
        for name, cnt in self.deck.main.items():
            card = self.card_db.get(name)
            if not card:
                continue
            img_path = card.get("image")
            if img_path and os.path.exists(img_path):
                image_paths.extend([img_path] * cnt)

        for name, cnt in self.deck.triggers.items():
            card = self.card_db.get(name)
            if not card:
                continue
            img_path = card.get("image")
            if img_path and os.path.exists(img_path):
                image_paths.extend([img_path] * cnt)

        if not image_paths:
            QMessageBox.warning(self, "No Images", "No card images found for the current deck!")
            return

        # Generate sheets
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

            deck_name_safe = "".join(c for c in self.deck_name_input.text() if c.isalnum() or c in "_- ")
            output_filename = os.path.join(folder_path, f"{deck_name_safe}_sheet_{batch_num + 1}.png")
            output_image.save(output_filename, dpi=(300, 300))
            print(f"Saved: {output_filename}")

        QMessageBox.information(self, "Export Complete", f"✅ Proxy sheets exported to:\n{folder_path}")


    # --- Gallery ---
    def filtered_cards(self):
        q = self.search.text().strip().lower()
        gsel = self.filter_grade.currentText()
        tsel = self.filter_trigger.currentText()

        def match(card):
            if q and q not in card["name"].lower():
                return False
            if gsel != "Any Grade" and str(card.get("grade","")) != gsel:
                return False
            if tsel != "Any Trigger":
                if tsel == "Non-Trigger" and is_trigger(card):
                    return False
                elif tsel != "Non-Trigger" and card.get("trigger") != tsel:
                    return False
            # --- Clan filter ---
            csel = self.filter_clan.currentText()
            if csel != "Any Clan" and card.get("clan","") != csel:
                return False
            return True


        return [c for c in self.card_db.values() if match(c)]

    def refresh_gallery(self):
        # Clear out old items
        self.gallery.clear()

        # Reset lazy load state
        self.loaded_count = 0
        self.filtered_cache = self.filtered_cards()

        # Load the first batch (e.g. 50 cards)
        self.load_more_cards()

    def gallery_double_click(self, item):   # ✅ now a real method
        name = item.data(Qt.UserRole)
        card = self.card_db[name]
        section = "triggers" if is_trigger(card) else "main"
        ok, msg = self.deck.add(section, name, self.card_db)
        if not ok:
            QMessageBox.warning(self, "Cannot add", msg)
            return
        self.refresh_deck_lists()
    
    def remove_on_right_click(self, list_widget, section, pos):
        item = list_widget.itemAt(pos)
        if not item:
            return
        name = item.text()
        if self.deck.remove(section, name):
            self.refresh_deck_lists()
            
    def load_more_cards(self):
        next_count = min(self.loaded_count + self.batch_size, len(self.filtered_cache))
        for i in range(self.loaded_count, next_count):
            card = self.filtered_cache[i]
            self.add_card_to_gallery(card)
        self.loaded_count = next_count

    def check_scroll(self, value):
        sb = self.gallery.verticalScrollBar()
        if value >= sb.maximum() - 50:  # near bottom
            if self.loaded_count < len(self.filtered_cache):
                self.load_more_cards()
                
    def add_card_to_gallery(self, card):
        path = self.get_card_image(card.get("image", ""))
        pm = self.pixmap_cache.get(path) or get_cached_pixmap(path)
        self.pixmap_cache[path] = pm

        pm_scaled = pm.scaled(GALLERY_ICON_W, GALLERY_ICON_H,
                              Qt.KeepAspectRatio, Qt.SmoothTransformation)

        widget = QWidget()
        h_layout = QHBoxLayout(widget)
        h_layout.setContentsMargins(5, 5, 5, 5)

        img_label = QLabel()
        img_label.setPixmap(pm_scaled)
        img_label.setFixedSize(GALLERY_ICON_W, GALLERY_ICON_H)
        h_layout.addWidget(img_label)

        v_layout = QVBoxLayout()
        name_label = QLabel(f"<b>{card['name']}</b>")
        name_label.setWordWrap(True)
        v_layout.addWidget(name_label)

        effect_text = card.get("effect", "No effects")
        if isinstance(effect_text, list):
            effect_text = "\n".join(effect_text)
        effects_label = QLabel(effect_text)
        effects_label.setWordWrap(True)
        effects_label.setAlignment(Qt.AlignTop)
        v_layout.addWidget(effects_label)

        h_layout.addLayout(v_layout)

        it = QListWidgetItem()
        it.setSizeHint(widget.sizeHint())
        it.setData(Qt.UserRole, card["name"])
        it.setToolTip(self.card_tooltip(card))
        self.gallery.addItem(it)
        self.gallery.setItemWidget(it, widget)
        

    def get_card_image(self, image_path, local_base=""):
        local_path = os.path.join(local_base, image_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        if not os.path.exists(local_path):
            remote_url = REMOTE_BASE + image_path
            print(f"Downloading missing card image: {remote_url}")
            try:
                import requests
                r = requests.get(remote_url)
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(r.content)
            except Exception as e:
                print(f"⚠️ Failed to download {remote_url}: {e}")
                return "placeholder.png"

        return local_path



    # --- Deck lists ---
    def refresh_deck_lists(self):
        self.main_list.clear()
        
        
        for name, cnt in self.deck.main.items():
            pm = get_cached_pixmap(self.get_card_image(self.card_db[name].get("image", "")))
            icon = QIcon(pm)
            for _ in range(cnt):
                it = QListWidgetItem(icon, name)
                it.setToolTip(self.card_tooltip(self.card_db[name]))
                self.main_list.addItem(it)
                
        grade_counts = {0:0, 1:0, 2:0, 3:0}
        
        for name, cnt in self.deck.main.items():
            grade = int(self.card_db[name].get("grade", 0))
            if grade in grade_counts:
                grade_counts[grade] += cnt

        self.grade1_label.setText(f"Grade 0 ({grade_counts[0]})")
        self.grade1_label.setText(f"Grade 1 ({grade_counts[1]})")
        self.grade2_label.setText(f"Grade 2 ({grade_counts[2]})")
        self.grade3_label.setText(f"Grade 3 ({grade_counts[3]})")

        self.trig_list.clear()
        for name, cnt in self.deck.triggers.items():
            pm = get_cached_pixmap(self.card_db[name].get("image", ""))
            icon = QIcon(pm)
            for _ in range(cnt):
                it = QListWidgetItem(icon, name)
                it.setToolTip(self.card_tooltip(self.card_db[name]))
                self.trig_list.addItem(it)

        self.main_label.setText(f"Main ({self.deck.total_main()}/{MAIN_LIMIT})")
        self.trig_label.setText(f"Triggers ({self.deck.total_triggers()}/{TRIGGER_LIMIT})")

    def card_tooltip(self, card):
        return (
            f"Name: {card['name']}\n"
            f"Grade: {card.get('grade','?')}\n"
            f"Type: {card.get('type','')}\n"
            f"Clan: {card.get('clan','')}\n"
            f"Trigger: {card.get('trigger') or '—'}"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Editor()
    win.show()
    sys.exit(app.exec())

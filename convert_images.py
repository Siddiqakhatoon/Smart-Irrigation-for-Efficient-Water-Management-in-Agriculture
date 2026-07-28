"""
convert_images.py
------------------
Place this file inside your smart_irrigation folder.

Folder structure:
    smart_irrigation/
    ├── images/
    │   ├── rice.jpg
    │   ├── wheat.jpg
    │   └── cotton.jpg
    ├── convert_images.py   <- THIS FILE
    ├── app.py
    └── templates/
        └── index.html

Run with:
    python convert_images.py
"""

import base64
import os
import shutil

IMAGES_FOLDER = "images"
INDEX_HTML    = os.path.join("templates", "index.html")
BACKUP_HTML   = os.path.join("templates", "index_backup.html")

CROP_FILES = {
    "RICE":   ["rice.jpg",   "rice.jpeg",   "rice.png",   "rice.webp"],
    "WHEAT":  ["wheat.jpg",  "wheat.jpeg",  "wheat.png",  "wheat.webp"],
    "COTTON": ["cotton.jpg", "cotton.jpeg", "cotton.png", "cotton.webp"],
}

PLACEHOLDERS = {
    "RICE":   "RICE_BASE64_HERE",
    "WHEAT":  "WHEAT_BASE64_HERE",
    "COTTON": "COTTON_BASE64_HERE",
}

print("\n" + "="*58)
print("  SMART IRRIGATION - Auto Image Embedder")
print("="*58)

# Check templates/index.html exists
if not os.path.exists(INDEX_HTML):
    print(f"\n[ERROR] Could not find: {INDEX_HTML}")
    print("        Make sure you are running this from inside")
    print("        the smart_irrigation folder.")
    input("\nPress Enter to exit...")
    exit(1)

# Backup original index.html before modifying
shutil.copy2(INDEX_HTML, BACKUP_HTML)
print(f"[OK]  Backup saved: {BACKUP_HTML}")

# Convert each image to base64
base64_map = {}

for crop, filenames in CROP_FILES.items():
    found_path = None
    for fname in filenames:
        candidate = os.path.join(IMAGES_FOLDER, fname)
        if os.path.exists(candidate):
            found_path = candidate
            break

    if not found_path:
        print(f"\n[ERROR] {crop} image not found in '{IMAGES_FOLDER}/' folder.")
        print(f"        Rename your file to one of: {filenames}")
        input("\nPress Enter to exit...")
        exit(1)

    ext  = found_path.split(".")[-1].lower()
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    with open(found_path, "rb") as f:
        raw = f.read()

    b64  = base64.b64encode(raw).decode("utf-8")
    size = round(len(raw) / 1024)
    base64_map[crop] = f"data:{mime};base64,{b64}"
    print(f"[OK]  {crop:<6} converted — {found_path} ({size} KB)")

# Read index.html
with open(INDEX_HTML, "r", encoding="utf-8") as f:
    html = f.read()

# Replace placeholders
replaced = 0
for crop, placeholder in PLACEHOLDERS.items():
    if placeholder in html:
        html = html.replace(placeholder, base64_map[crop])
        replaced += 1
        print(f"[OK]  Replaced {crop} image in templates/index.html")
    else:
        print(f"[!]   Placeholder '{placeholder}' not found — already replaced or missing")
        replaced += 1  # count as done if already embedded

# Write updated index.html
with open(INDEX_HTML, "w", encoding="utf-8") as f:
    f.write(html)

print("\n" + "="*58)
print(f"  Done! {replaced}/3 images embedded into templates/index.html")
print("  Now run:    python app.py")
print("  Then open:  http://localhost:5000")
print("="*58 + "\n")

input("Press Enter to close...")

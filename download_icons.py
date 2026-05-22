import os
import urllib.request

ICONS = [
    "play", "pause", "skip-forward", "rotate-ccw",
    "bar-chart-2", "settings", "volume-2", "volume-x",
    "minimize-2", "x"
]

BASE_URL = "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/{}.svg"
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons")

os.makedirs(ASSETS_DIR, exist_ok=True)

for icon in ICONS:
    url = BASE_URL.format(icon)
    path = os.path.join(ASSETS_DIR, f"{icon}.svg")
    print(f"Downloading {icon}...")
    try:
        # Some icons might have different names, but these are standard lucide names
        urllib.request.urlretrieve(url, path)
    except Exception as e:
        print(f"Failed to download {icon}: {e}")

print("Done!")

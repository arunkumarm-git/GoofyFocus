import os, glob
import urllib.request

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons")

# download missing bar-chart.svg
url = "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/bar-chart.svg"
try:
    urllib.request.urlretrieve(url, os.path.join(ASSETS_DIR, "bar-chart.svg"))
except Exception as e:
    print(e)

for f in glob.glob(os.path.join(ASSETS_DIR, "*.svg")):
    with open(f, 'r') as file:
        data = file.read()
    data = data.replace('currentColor', '#ffffff')
    data = data.replace('stroke-width="2"', 'stroke-width="2.5"')
    with open(f, 'w') as file:
        file.write(data)

print("SVGs recolored!")

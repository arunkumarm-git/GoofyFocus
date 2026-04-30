from PIL import Image

img = Image.open("assets/icon.png")
img.save("assets/icon.ico", format="ICO", sizes=[
    (16,16), (32,32), (48,48), (64,64), (128,128), (256,256)
])

print("Done! icon.ico created in assets/")
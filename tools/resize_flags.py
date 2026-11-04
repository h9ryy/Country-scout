from pathlib import Path

from PIL import Image

FLAGS = Path(__file__).resolve().parent.parent / "flags"
WIDTH = 640

for f in sorted(FLAGS.rglob("*.png")):
    with Image.open(f) as im:
        img = im.convert("RGB")
    if img.width > WIDTH:
        height = round(img.height * WIDTH / img.width)
        img = img.resize((WIDTH, height), Image.LANCZOS)
    img.save(f, optimize=True)
    print(f.relative_to(FLAGS), img.size, f"{f.stat().st_size // 1024} КБ")
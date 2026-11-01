import json
from pathlib import Path

from PIL import Image

BASE = Path(__file__).resolve().parent.parent
FLAGS = BASE / "flags"
data = json.loads((BASE / "data" / "europe.json").read_text(encoding="utf-8"))

# 1. webp -> png
for f in FLAGS.glob("*.webp"):
    Image.open(f).convert("RGB").save(f.with_suffix(".png"))
    f.unlink()
    print("конвертирован:", f.name)

# 2. проверка, что все флаги на месте
missing = [
    c["code"] for c in data["countries"]
    if not (FLAGS / f"{c['code']}.png").exists()
]
print("не хватает:", missing or "всё на месте ✅")
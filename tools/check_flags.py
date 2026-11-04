import json
from pathlib import Path

from PIL import Image

BASE = Path(__file__).resolve().parent.parent
FLAGS = BASE / "flags"

# 1. webp -> png (во всех подпапках)
for f in FLAGS.rglob("*.webp"):
    Image.open(f).convert("RGB").save(f.with_suffix(".png"))
    f.unlink()
    print("конвертирован:", f.relative_to(FLAGS))

# 2. проверка по всем файлам материков: flags/<материк>/<код>.png
for data_file in sorted((BASE / "data").glob("*.json")):
    data = json.loads(data_file.read_text(encoding="utf-8"))
    missing = [
        f'{c["continent"]}/{c["code"]}'
        for c in data["countries"]
        if not (FLAGS / c["continent"] / f'{c["code"]}.png').exists()
    ]
    print(f"{data_file.name}: не хватает:", missing or "всё на месте ✅")
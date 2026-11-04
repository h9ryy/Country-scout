import json
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
FLAGS = BASE / "flags"
URL = "https://flagcdn.com/w640/{code}.png"

failed = []
for data_file in sorted((BASE / "data").glob("*.json")):
    data = json.loads(data_file.read_text(encoding="utf-8"))
    for c in data["countries"]:
        target = FLAGS / c["continent"] / f'{c["code"]}.png'
        if target.exists():
            continue
        # Если картинка лежит на сайте под другим кодом, укажи "source" в JSON
        source = c.get("source", c["code"])
        target.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            URL.format(code=source), headers={"User-Agent": "Mozilla/5.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                target.write_bytes(r.read())
            print("скачан:", target.relative_to(FLAGS))
        except (urllib.error.URLError, TimeoutError) as e:
            print("ОШИБКА:", target.relative_to(FLAGS), e)
            failed.append(f'{c["continent"]}/{c["code"]}')
        time.sleep(0.2)

print("не скачались:", failed or "нет, все на месте ✅")
"""FastAPI şemasını `frontend/openapi.json` dosyasına yazar.

Ön yüzün TypeScript tipleri bu dosyadan üretilir (`npm run api-tipleri`); CI, dosyanın ve üretilen
tiplerin güncel olduğunu denetler. Şema üretimi veri yüklemez.
"""

import json
import sys
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "frontend" / "openapi.json"


def schema() -> dict[str, object]:
    from sinek.api.app import create_app

    data: dict[str, object] = create_app().openapi()
    return data


def main() -> int:
    text = json.dumps(schema(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if "--denetle" in sys.argv:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != text:
            print("frontend/openapi.json güncel değil: uv run python scripts/openapi_aktar.py")
            return 1
        return 0
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"yazıldı: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

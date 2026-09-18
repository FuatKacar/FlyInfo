"""`.env.example` dosyasına yanlışlıkla gerçek API anahtarı yazılmasını engeller.

Anahtar/gizli değer içeren değişkenlerin şablonda boş kalması zorunludur.
pre-commit ve CI tarafından çalıştırılır.
"""

import re
import sys
from pathlib import Path

SECRET_NAME = re.compile(r"(API_KEY|SECRET|TOKEN|PASSWORD)$")


def find_leaks(path: Path) -> list[str]:
    leaks = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = (part.strip() for part in stripped.split("=", 1))
        if SECRET_NAME.search(name) and value:
            leaks.append(f"{path}:{number}: {name} boş olmalı")
    return leaks


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".env.example")
    leaks = find_leaks(path)
    for leak in leaks:
        print(leak)
    if leaks:
        print("Gerçek anahtarları yalnızca .env dosyasına yazın (git dışıdır).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

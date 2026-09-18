"""`docs/kaynakca.bib` → `frontend/src/assets/kaynakca.json` (arayüzdeki atıf listesi).

Arayüz kaynakçayı yalnızca bu dosyadan okur; böylece belgeler ve arayüz aynı kaynağı kullanır.
`--denetle` ile dosyanın güncel olduğu doğrulanır (CI ve testler).
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIB_PATH = ROOT / "docs" / "kaynakca.bib"
OUTPUT = ROOT / "frontend" / "src" / "assets" / "kaynakca.json"
ENTRY = re.compile(r"@\w+\{(?P<key>[^,]+),(?P<body>.*?)\n\}", re.DOTALL)
FIELD = re.compile(r"(?P<name>\w+)\s*=\s*\{(?P<value>.*?)\},?\s*$", re.MULTILINE)
LATEX = {'{\\"o}': "ö", '{\\"u}': "ü", '{\\"a}': "ä", "--": "–"}
MAX_AUTHORS = 6


def _clean(text: str) -> str:
    for source, target in LATEX.items():
        text = text.replace(source, target)
    return re.sub(r"[{}]", "", text).strip()


def _authors(raw: str) -> str:
    names = [n.strip() for n in raw.split(" and ")]
    others = "others" in names
    names = [n for n in names if n != "others"]
    formatted = []
    for name in names:
        family, _, given = name.partition(",")
        initials = " ".join(f"{part[0]}." for part in re.split(r"[\s.]+", given.strip()) if part)
        formatted.append(f"{family.strip()}, {initials}".strip(", "))
    shown = formatted[:MAX_AUTHORS]
    text = ", ".join(shown)
    if others or len(formatted) > MAX_AUTHORS:
        text += " vd."
    return _clean(text)


def entries(bib: str) -> list[dict[str, object]]:
    result = []
    for match in ENTRY.finditer(bib):
        fields = {f["name"]: f["value"] for f in FIELD.finditer(match["body"])}
        number = int(re.sub(r"\D", "", fields["note"]))
        result.append(
            {
                "number": number,
                "key": match["key"].strip(),
                "authors": _authors(fields["author"]),
                "title": _clean(fields["title"]),
                "journal": _clean(fields.get("journal", fields.get("publisher", ""))),
                "year": int(fields["year"]),
                "volume": fields.get("volume"),
                "issue": fields.get("number"),
                "pages": _clean(fields["pages"]) if "pages" in fields else None,
                "doi": fields["doi"],
            }
        )
    return sorted(result, key=lambda e: int(str(e["number"])))


def render() -> str:
    data = entries(BIB_PATH.read_text(encoding="utf-8"))
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    text = render()
    if "--denetle" in sys.argv:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != text:
            print("kaynakca.json güncel değil: uv run python scripts/kaynakca_aktar.py")
            return 1
        return 0
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"yazıldı: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

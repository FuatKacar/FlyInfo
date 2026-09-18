"""`docs/kaynakca.bib` içindeki DOI'leri Crossref kayıtlarıyla doğrular.

Her kayıt için DOI'nin çözümlendiği ve başlığın eşleştiği kontrol edilir.
Crossref'te bulunmayan bioRxiv ön baskıları bioRxiv API'si üzerinden denetlenir.
Yalnızca standart kütüphane kullanır.
"""

import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

BIB_PATH = Path(__file__).resolve().parent.parent / "docs" / "kaynakca.bib"
USER_AGENT = "flyinfo-reference-check/1.0 (+https://github.com/FuatKacar/FlyInfo)"
ENTRY = re.compile(r"@\w+\{(?P<key>[^,]+),(?P<body>.*?)\n\}", re.DOTALL)
FIELD = re.compile(r"(?P<name>\w+)\s*=\s*\{(?P<value>.*?)\},?\s*$", re.MULTILINE)


def normalize(text: str) -> str:
    text = re.sub(r"<[^>]+>|[{}\\*]", "", text)
    text = unicodedata.normalize("NFKD", text)
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


RETRIES = 3


class ServiceError(RuntimeError):
    """Kayıt servisi geçici olarak geçerli yanıt vermedi (boş gövde, bozuk JSON, ağ hatası)."""


def fetch_json(url: str, accept: str = "application/json") -> dict[str, object]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    last_error: Exception | None = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data: dict[str, object] = json.load(response)
                return data
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
            time.sleep(2**attempt)
    raise ServiceError(f"{url}: {last_error}")


def _biorxiv_title(doi: str) -> str:
    data = fetch_json(f"https://api.biorxiv.org/details/biorxiv/{doi}")
    collection = data.get("collection")
    if not isinstance(collection, list) or not collection:
        raise ServiceError("bioRxiv kaydı boş")
    return str(collection[-1]["title"])


def _doi_org_title(doi: str) -> str:
    """DOI çözümleyicisinden içerik anlaşmasıyla (CSL JSON) başlık."""
    data = fetch_json(f"https://doi.org/{doi}", accept="application/vnd.citationstyles.csl+json")
    return str(data["title"])


def remote_title(doi: str) -> str:
    if doi.startswith("10.1101/"):
        try:
            return _biorxiv_title(doi)
        except ServiceError:
            return _doi_org_title(doi)  # bioRxiv API'si geçici olarak boş yanıt verebiliyor
    message = fetch_json(f"https://api.crossref.org/works/{doi}")["message"]
    if not isinstance(message, dict):
        raise ServiceError("Crossref yanıtı beklenen biçimde değil")
    return str(message["title"][0])


def main() -> int:
    entries = list(ENTRY.finditer(BIB_PATH.read_text(encoding="utf-8")))
    failures = 0
    for entry in entries:
        fields = {m["name"].lower(): m["value"] for m in FIELD.finditer(entry["body"])}
        key, doi, title = entry["key"], fields.get("doi"), fields.get("title", "")
        if not doi:
            print(f"EKSİK   {key}: DOI alanı yok")
            failures += 1
            continue
        try:
            found = remote_title(doi)
        except (ServiceError, KeyError, IndexError) as error:
            print(f"HATA    {key}: {doi} çözümlenemedi ({error})")
            failures += 1
            continue
        if normalize(found) != normalize(title):
            print(f"UYUŞMAZ {key}: bib='{title}' kayıt='{found}'")
            failures += 1
        else:
            print(f"TAMAM   {key}")
        time.sleep(0.2)  # Crossref'e nazik davran

    print(f"\n{len(entries)} kaynaktan {len(entries) - failures} tanesi doğrulandı.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

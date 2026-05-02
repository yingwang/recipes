"""Insert a hero image after the chapter intro of each chapter file."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent
CHAPTERS = ROOT / "docs" / "chapters"

SLUG_BY_FILE = {
    "01-hangzhou.md":       "01-hangzhou",
    "02-jiangzhe.md":       "02-jiangzhe",
    "03-cantonese.md":      "03-cantonese",
    "04-sichuan.md":        "04-sichuan",
    "05-northern.md":       "05-northern",
    "06-japan-korea.md":    "06-japan-korea",
    "07-southeast-asia.md": "07-southeast-asia",
    "08-india.md":          "08-india",
    "09-french.md":         "09-french",
    "10-italian.md":        "10-italian",
    "11-spanish.md":        "11-spanish",
}


def main() -> None:
    for fname, slug in SLUG_BY_FILE.items():
        fp = CHAPTERS / fname
        text = fp.read_text()
        if "../images/chapters/" in text:
            print(f"[skip] {fname}: already has image")
            continue
        marker = "\n---\n"
        idx = text.find(marker)
        if idx == -1:
            print(f"[fail] {fname}: no `---` separator")
            continue
        intro = text[:idx].rstrip()
        rest = text[idx:]
        img = f"\n\n![{slug}](../images/chapters/{slug}.jpg)\n"
        new_text = intro + img + rest
        fp.write_text(new_text)
        print(f"[ok]   {fname}")


if __name__ == "__main__":
    main()

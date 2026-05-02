"""Insert downloaded dish images into chapter files.

Walks docs/images/dishes/, derives chapter + dish slug from filename,
finds the matching `## 菜名` heading in the chapter (allowing trailing
parenthetical translations), and inserts the image markdown after it.

Idempotent.

Run: python3 scripts/insert_dish_images.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHAPTERS = ROOT / "docs" / "chapters"
DISH_IMG_DIR = ROOT / "docs" / "images" / "dishes"

CHAPTER_SLUGS = [
    "01-hangzhou", "02-jiangzhe", "03-cantonese", "04-sichuan",
    "05-northern", "06-japan-korea", "07-southeast-asia",
    "08-india", "09-french", "10-italian", "11-spanish",
]


def main() -> None:
    inserted = 0
    skipped = 0
    not_found = 0
    for img_path in sorted(DISH_IMG_DIR.iterdir()):
        if not img_path.is_file():
            continue
        stem = img_path.stem
        chapter_slug = next((c for c in CHAPTER_SLUGS if stem.startswith(c + "-")), None)
        if not chapter_slug:
            print(f"[skip] {img_path.name}: cannot infer chapter")
            continue
        dish_name = stem[len(chapter_slug) + 1:]

        chapter_path = CHAPTERS / f"{chapter_slug}.md"
        text = chapter_path.read_text()

        rel = f"../images/dishes/{img_path.name}"
        if rel in text:
            skipped += 1
            continue

        # Find heading like `## {dish_name}` optionally followed by parentheses
        pattern = re.compile(rf"^(## {re.escape(dish_name)}[（(].*?[)）]?\s*|## {re.escape(dish_name)}\s*)$", re.MULTILINE)
        m = pattern.search(text)
        if not m:
            print(f"[miss] {chapter_slug} / {dish_name}: no heading match")
            not_found += 1
            continue

        heading_line = m.group(0).rstrip()
        img_md = f'![{dish_name}]({rel})' + '{ width="360" .center }'
        new_text = text.replace(
            heading_line + "\n",
            heading_line + "\n\n" + img_md + "\n",
            1,
        )
        if new_text == text:
            print(f"[miss] {chapter_slug} / {dish_name}: replace failed")
            not_found += 1
            continue
        chapter_path.write_text(new_text)
        inserted += 1
        print(f"[ok]   {chapter_slug} / {dish_name}")

    print(f"\nDone. inserted={inserted} skipped={skipped} not_found={not_found}")


if __name__ == "__main__":
    main()

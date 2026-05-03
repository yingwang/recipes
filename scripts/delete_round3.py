"""Round 3: delete more confirmed-wrong dish images."""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHAPTERS = ROOT / "docs" / "chapters"
DISH_IMG_DIR = ROOT / "docs" / "images" / "dishes"

BAD = [
    ("05-northern", "05-northern-葱爆羊肉"),     # Western braised lamb dinner
    ("05-northern", "05-northern-西红柿打卤面"), # HK macaroni soup
    ("03-cantonese", "03-cantonese-上汤娃娃菜"), # Western minestrone
    ("04-sichuan", "04-sichuan-蒜泥白肉"),        # American Chinese pork rice
    ("06-japan-korea", "06-japan-korea-韩式海鲜葱饼"),  # marginal UK restaurant version
]


def remove_image_line(p, stem):
    text = p.read_text()
    for n in range(2, 0, -1):
        pat = re.compile(rf"^!\[[^\]]*\]\(\.\./images/dishes/{re.escape(stem)}\.[a-z]+\)\{{[^}}]*\}}\n{{,{n}}}", re.MULTILINE)
        new = pat.sub("", text)
        if new != text:
            p.write_text(new)
            return True
    return False


def main():
    for chapter, stem in BAD:
        for ext in ["jpg","png","webp"]:
            f = DISH_IMG_DIR / f"{stem}.{ext}"
            if f.exists():
                f.unlink()
                print(f"[del] {f.name}")
        if remove_image_line(CHAPTERS / f"{chapter}.md", stem):
            print(f"[md]  {stem}")


if __name__ == "__main__":
    main()

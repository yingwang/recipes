"""Delete dish images that are still clearly wrong after refetch attempts.
For these, no image is better than a misleading one.

Run: python3 scripts/delete_still_bad.py
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHAPTERS = ROOT / "docs" / "chapters"
DISH_IMG_DIR = ROOT / "docs" / "images" / "dishes"

# (chapter, image_stem)
STILL_BAD = [
    ("01-hangzhou", "01-hangzhou-油焖春笋"),       # train
    ("01-hangzhou", "01-hangzhou-红烧带鱼"),       # train
    ("01-hangzhou", "01-hangzhou-番茄炒蛋"),       # tomato macaroni
    ("01-hangzhou", "01-hangzhou-家常红烧肉"),     # bao bun
    ("01-hangzhou", "01-hangzhou-韭黄炒蛋"),       # garden plants
    ("01-hangzhou", "01-hangzhou-萝卜丝鲫鱼汤"),   # historical drawing
    ("01-hangzhou", "01-hangzhou-炒青菜"),         # Italian pasta
    ("01-hangzhou", "01-hangzhou-油爆虾"),         # water spinach beef
    ("01-hangzhou", "01-hangzhou-腌笃鲜"),         # salted duck eggs
    ("01-hangzhou", "01-hangzhou-葱油拌面"),       # restaurant exterior
    ("02-jiangzhe", "02-jiangzhe-响油鳝糊"),       # post office boxes
    ("02-jiangzhe", "02-jiangzhe-松鼠桂鱼"),       # historical portrait
    ("02-jiangzhe", "02-jiangzhe-雪菜黄鱼"),       # mango pudding
    ("02-jiangzhe", "02-jiangzhe-葱油海蜇"),       # generic kurage, marginal
    ("04-sichuan", "04-sichuan-青椒肉丝"),         # yu xiang shredded pork (wrong dish)
    ("04-sichuan", "04-sichuan-醋溜白菜"),         # chicken salad
    ("05-northern", "05-northern-韭菜盒子"),       # restaurant building
    ("07-southeast-asia", "07-southeast-asia-越南鸡饭"),       # woman painting
    ("07-southeast-asia", "07-southeast-asia-越南鱼露蘸汁"),   # bun tron noodle
    ("03-cantonese", "03-cantonese-蜜汁叉烧"),     # char siu bagel sandwich
]


def remove_image_line(chapter_path: Path, stem: str) -> bool:
    text = chapter_path.read_text()
    pat = re.compile(rf"^!\[[^\]]*\]\(\.\./images/dishes/{re.escape(stem)}\.[a-z]+\)\{{[^}}]*\}}\n\n", re.MULTILINE)
    new = pat.sub("", text)
    if new == text:
        pat2 = re.compile(rf"^!\[[^\]]*\]\(\.\./images/dishes/{re.escape(stem)}\.[a-z]+\)\{{[^}}]*\}}\n", re.MULTILINE)
        new = pat2.sub("", text)
    if new == text: return False
    chapter_path.write_text(new)
    return True


def main():
    deleted = 0
    line_removed = 0
    for chapter, stem in STILL_BAD:
        for ext in ["jpg","png","webp"]:
            p = DISH_IMG_DIR / f"{stem}.{ext}"
            if p.exists():
                p.unlink()
                deleted += 1
                print(f"[del] {p.name}")
        chap = CHAPTERS / f"{chapter}.md"
        if remove_image_line(chap, stem):
            line_removed += 1
            print(f"[md]  removed line for {stem} in {chapter}.md")
    print(f"\nfiles_deleted={deleted} markdown_lines_removed={line_removed}")


if __name__ == "__main__":
    main()

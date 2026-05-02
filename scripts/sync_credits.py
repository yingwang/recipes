"""Sync CREDITS.md dish-level entries to match actual files in docs/images/dishes/.

Removes entries for deleted images, updates File: paths for renamed images,
keeps order.

Run: python3 scripts/sync_credits.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
CREDITS = ROOT / "docs" / "images" / "CREDITS.md"
DISH_DIR = ROOT / "docs" / "images" / "dishes"

# old_stem -> new_stem (must match RENAME_MAP in rename_and_insert_dishes.py)
RENAME_PAIRS = {
    "02-jiangzhe-狮子头":     "02-jiangzhe-蟹粉狮子头",
    "02-jiangzhe-松鼠鳜鱼":   "02-jiangzhe-松鼠桂鱼",
    "02-jiangzhe-醉鸡":       "02-jiangzhe-绍兴醉鸡",
    "03-cantonese-叉烧":      "03-cantonese-蜜汁叉烧",
    "05-northern-饺子":       "05-northern-猪肉白菜饺子",
    "05-northern-西红柿鸡蛋面": "05-northern-西红柿打卤面",
    "06-japan-korea-韩式煎饼": "06-japan-korea-韩式海鲜葱饼",
    "07-southeast-asia-绿咖喱": "07-southeast-asia-泰式青咖喱鸡",
    "07-southeast-asia-越南春卷": "07-southeast-asia-越南生春卷",
    "08-india-印度烤饼":      "08-india-Naan",
    "08-india-印度香饭":      "08-india-家常版印度香饭",
    "08-india-帕尼尔":        "08-india-菠菜咖喱奶酪",
    "08-india-达尔":          "08-india-黄豆泥",
    "08-india-黄油鸡":        "08-india-黄油咖喱鸡",
    "09-french-普罗旺斯炖菜":  "09-french-普罗旺斯杂烩",
    "09-french-法式洋葱汤":    "09-french-焗烤洋葱汤",
    "09-french-法式蛋饼":      "09-french-洛林乡村咸派",
    "10-italian-卡邦尼意面":   "10-italian-Carbonara",
    "10-italian-提拉米苏":     "10-italian-Tiramisù",
    "10-italian-烩饭":         "10-italian-Risotto",
    "10-italian-青酱意面":     "10-italian-Pesto",
    "11-spanish-土豆煎蛋饼":   "11-spanish-Tortilla",
    "11-spanish-海鲜饭":       "11-spanish-Paella",
    "11-spanish-番茄面包":     "11-spanish-Pan",
    "11-spanish-蒜虾":         "11-spanish-Gambas",
    "11-spanish-辣味土豆":     "11-spanish-Patatas",
}


def main() -> None:
    text = CREDITS.read_text()

    # Apply renames
    for old, new in RENAME_PAIRS.items():
        # File: `images/dishes/old.jpg` -> ...new.jpg
        text = text.replace(f"images/dishes/{old}.jpg", f"images/dishes/{new}.jpg")
        # ### 01-hangzhou / 狮子头 -> 蟹粉狮子头 (extract dish name from new)
        chapter, _, dish_old = old.partition("-")
        # actually old like "02-jiangzhe-狮子头": chapter=02, rest=jiangzhe-狮子头
        # split first two segments
        parts = old.split("-", 2)
        chapter_slug = "-".join(parts[:2])
        dish_old_name = parts[2]
        new_parts = new.split("-", 2)
        dish_new_name = new_parts[2]
        text = text.replace(
            f"### {chapter_slug} / {dish_old_name}",
            f"### {chapter_slug} / {dish_new_name}",
        )

    # Remove entries for files that no longer exist
    existing_files = {p.name for p in DISH_DIR.iterdir() if p.is_file()}

    blocks = re.split(r"(?m)^### ", text)
    head = blocks[0]
    kept_blocks = []
    removed = 0
    for blk in blocks[1:]:
        m = re.search(r"images/dishes/([^`]+)`", blk)
        if not m:
            kept_blocks.append(blk)
            continue
        fname = m.group(1).strip()
        if fname in existing_files:
            kept_blocks.append(blk)
        else:
            removed += 1

    new_text = head + "".join("### " + b for b in kept_blocks)
    CREDITS.write_text(new_text)
    print(f"Renamed entries; removed {removed} orphan entries")


if __name__ == "__main__":
    main()

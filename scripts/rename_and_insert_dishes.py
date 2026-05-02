"""Rename downloaded dish images to match actual chapter headings,
then insert them. Drops orphan images that don't correspond to any heading.

Run: python3 scripts/rename_and_insert_dishes.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHAPTERS = ROOT / "docs" / "chapters"
DISH_IMG_DIR = ROOT / "docs" / "images" / "dishes"

# Map of downloaded slug -> (chapter_slug, exact heading line text after "## ")
RENAME_MAP: dict[str, tuple[str, str]] = {
    # 01-hangzhou: all already correct, no rename needed
    # 02-jiangzhe
    "02-jiangzhe-狮子头":     ("02-jiangzhe", "蟹粉狮子头"),
    "02-jiangzhe-松鼠鳜鱼":   ("02-jiangzhe", "松鼠桂鱼"),
    "02-jiangzhe-醉鸡":       ("02-jiangzhe", "绍兴醉鸡"),
    # 03-cantonese
    "03-cantonese-叉烧":      ("03-cantonese", "蜜汁叉烧（家庭烤箱版）"),
    # 04-sichuan: all matched but only 4 inserted; recheck
    # 05-northern
    "05-northern-饺子":       ("05-northern", "猪肉白菜饺子"),
    "05-northern-西红柿鸡蛋面": ("05-northern", "西红柿打卤面"),
    # 06-japan-korea
    "06-japan-korea-韩式煎饼": ("06-japan-korea", "韩式海鲜葱饼（해물파전 / haemul pajeon）"),
    # 07-southeast-asia
    "07-southeast-asia-绿咖喱": ("07-southeast-asia", "泰式青咖喱鸡（Gaeng Khiao Wan Gai）"),
    "07-southeast-asia-越南春卷": ("07-southeast-asia", "越南生春卷（Gỏi Cuốn）"),
    # 08-india
    "08-india-印度烤饼":      ("08-india", "Naan（家庭烤箱版）"),
    "08-india-印度香饭":      ("08-india", "家常版印度香饭 Chicken Biryani"),
    "08-india-帕尼尔":        ("08-india", "菠菜咖喱奶酪 Saag Paneer"),
    "08-india-达尔":          ("08-india", "黄豆泥 Dal Tadka"),
    "08-india-黄油鸡":        ("08-india", "黄油咖喱鸡 Butter Chicken"),
    # 09-french
    "09-french-普罗旺斯炖菜":  ("09-french", "普罗旺斯杂烩 / Ratatouille"),
    "09-french-法式洋葱汤":    ("09-french", "焗烤洋葱汤 / Soupe à l'Oignon Gratinée"),
    "09-french-法式蛋饼":      ("09-french", "洛林乡村咸派 / Quiche Lorraine"),
    "09-french-红酒炖鸡":      ("09-french", "红酒炖鸡 / Coq au Vin"),
    # 10-italian
    "10-italian-卡邦尼意面":   ("10-italian", "Carbonara（罗马蛋黄培根意面）"),
    "10-italian-提拉米苏":     ("10-italian", "Tiramisù（提拉米苏）"),
    "10-italian-烩饭":         ("10-italian", "Risotto alla Milanese（米兰藏红花烩饭）"),
    "10-italian-青酱意面":     ("10-italian", "Pesto alla Genovese（青酱意面）"),
    # 11-spanish
    "11-spanish-土豆煎蛋饼":   ("11-spanish", "Tortilla Española（西班牙土豆煎蛋）"),
    "11-spanish-海鲜饭":       ("11-spanish", "Paella Valenciana（家常版瓦伦西亚海鲜饭）"),
    "11-spanish-番茄面包":     ("11-spanish", "Pan con Tomate（番茄面包）"),
    "11-spanish-蒜虾":         ("11-spanish", "Gambas al Ajillo（蒜油烩虾）"),
    "11-spanish-辣味土豆":     ("11-spanish", "Patatas Bravas（辣酱炸土豆）"),
}

# Already-correct (no rename, just insert)
KEEP_AS_IS: list[tuple[str, str]] = [
    # 01-hangzhou: already inserted, list anyway for completeness
    ("01-hangzhou", "家常红烧肉"),
    ("01-hangzhou", "梅干菜烧肉"),
    ("01-hangzhou", "油焖春笋"),
    ("01-hangzhou", "番茄炒蛋"),
    ("01-hangzhou", "糖醋排骨"),
    ("01-hangzhou", "红烧带鱼"),
    ("01-hangzhou", "腌笃鲜"),
    ("01-hangzhou", "葱油拌面"),
    # 02-jiangzhe
    ("02-jiangzhe", "响油鳝糊"),
    # 03-cantonese
    ("03-cantonese", "白切鸡"),
    ("03-cantonese", "豉油鸡"),
    # 04-sichuan
    ("04-sichuan", "回锅肉"),
    ("04-sichuan", "宫保鸡丁"),
    ("04-sichuan", "鱼香肉丝"),
    ("04-sichuan", "麻婆豆腐"),
    # 05-northern
    ("05-northern", "炸酱面"),
    ("05-northern", "葱爆羊肉"),
    ("05-northern", "锅包肉"),
    # 06-japan-korea (heading has parens but image stem matches before parens)
    ("06-japan-korea", "亲子丼（おやこどん）"),
    ("06-japan-korea", "石锅拌饭（비빔밥 / bibimbap）"),
    ("06-japan-korea", "部队锅（부대찌개 / budae jjigae）"),
    ("06-japan-korea", "泡菜炒饭（김치볶음밥 / kimchi bokkeumbap）"),
    # 07-southeast-asia (need to rename images for correct slug)
    ("07-southeast-asia", "冬阴功汤（Tom Yum Goong）"),
    ("07-southeast-asia", "泰式炒河粉（Pad Thai）"),
    ("07-southeast-asia", "芒果糯米饭（Khao Niao Mamuang）"),
    ("07-southeast-asia", "越南河粉（Phở Bò / Phở Gà）"),
]

# Orphan images to delete (no matching heading)
ORPHANS = [
    "02-jiangzhe-八宝饭", "02-jiangzhe-白切鸡", "02-jiangzhe-阳春面",
    "03-cantonese-烧鹅", "03-cantonese-肠粉", "03-cantonese-艇仔粥",
    "03-cantonese-虾饺", "03-cantonese-蚝油生菜",
    "04-sichuan-担担面", "04-sichuan-水煮牛肉", "04-sichuan-辣子鸡",
    "05-northern-地三鲜", "05-northern-烙饼", "05-northern-醋溜白菜",
    "06-japan-korea-味噌汤", "06-japan-korea-照烧鸡腿", "06-japan-korea-生姜烧",
    "07-southeast-asia-叻沙", "07-southeast-asia-越南法包",
    "08-india-玛萨拉茶", "08-india-羊肉咖喱", "08-india-羊肉巴尔蒂",
    "09-french-克拉芙缇", "09-french-奶油蘑菇汤", "09-french-尼斯沙拉",
    "09-french-红酒炖牛肉",
    "10-italian-帕尔玛火腿", "10-italian-玛格丽特披萨", "10-italian-番茄意面",
    "10-italian-肉酱面",
    "11-spanish-加斯帕乔", "11-spanish-墨鱼", "11-spanish-大虾大蒜",
]


def slugify_heading(heading: str) -> str:
    """First token of heading before space, slash, or paren."""
    h = heading
    for sep in ["（", "(", " / ", " "]:
        if sep in h:
            h = h.split(sep, 1)[0]
    return h.strip()


def insert_image(chapter_slug: str, heading: str, image_filename: str) -> bool:
    chapter_path = CHAPTERS / f"{chapter_slug}.md"
    text = chapter_path.read_text()
    rel = f"../images/dishes/{image_filename}"
    if rel in text:
        return False
    heading_line = f"## {heading}"
    if heading_line + "\n" not in text:
        return False
    img_md = f'![{slugify_heading(heading)}]({rel})' + '{ width="360" .center }'
    new_text = text.replace(
        heading_line + "\n",
        heading_line + "\n\n" + img_md + "\n",
        1,
    )
    if new_text == text:
        return False
    chapter_path.write_text(new_text)
    return True


def main() -> None:
    # 1. Delete orphans
    deleted = 0
    for orphan in ORPHANS:
        for ext in ["jpg", "png", "webp"]:
            p = DISH_IMG_DIR / f"{orphan}.{ext}"
            if p.exists():
                p.unlink()
                deleted += 1
                print(f"[del]  {p.name}")

    # 2. Rename + insert
    renamed = 0
    inserted_count = 0
    for old_stem, (chapter, heading) in RENAME_MAP.items():
        new_stem = f"{chapter}-{slugify_heading(heading)}"
        for ext in ["jpg", "png", "webp"]:
            old_path = DISH_IMG_DIR / f"{old_stem}.{ext}"
            if not old_path.exists():
                continue
            new_path = DISH_IMG_DIR / f"{new_stem}.{ext}"
            if new_path.exists() and old_path != new_path:
                old_path.unlink()
                continue
            if old_path != new_path:
                old_path.rename(new_path)
                renamed += 1
                print(f"[rn]   {old_stem}.{ext} -> {new_stem}.{ext}")
            if insert_image(chapter, heading, new_path.name):
                inserted_count += 1

    # 3. Insert KEEP_AS_IS (use slug as image stem)
    for chapter, heading in KEEP_AS_IS:
        slug = slugify_heading(heading)
        for ext in ["jpg", "png", "webp"]:
            p = DISH_IMG_DIR / f"{chapter}-{slug}.{ext}"
            if p.exists():
                if insert_image(chapter, heading, p.name):
                    inserted_count += 1
                break

    print(f"\nDone. deleted={deleted} renamed={renamed} inserted={inserted_count}")


if __name__ == "__main__":
    main()

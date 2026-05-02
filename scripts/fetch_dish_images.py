"""Fetch CC-licensed dish-level images from Wikimedia Commons.

For each chapter, walk through ## headings (skipping 历史与地理), search
Commons for that dish, download the best CC-licensed result, insert the
image markdown after the dish heading, and append a CREDITS entry.

Idempotent: if an image already exists for a dish slug, skip it. Re-run
to fill gaps.

Run with: python3 scripts/fetch_dish_images.py
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHAPTERS = ROOT / "docs" / "chapters"
DISH_IMG_DIR = ROOT / "docs" / "images" / "dishes"
CREDITS = ROOT / "docs" / "images" / "CREDITS.md"

# Per-chapter dish -> Wikimedia search query candidates.
# Skipping dishes too generic to find good CC images for.
DISH_QUERIES: dict[str, list[tuple[str, list[str]]]] = {
    "01-hangzhou": [
        ("家常红烧肉",   ["Red braised pork", "Hong shao rou"]),
        ("腌笃鲜",       ["Yan du xian", "Pickled fresh soup"]),
        ("糖醋排骨",     ["Sweet and sour spare ribs", "Tangcu paigu"]),
        ("梅干菜烧肉",   ["Mei cai kou rou", "Mei gan cai"]),
        ("油焖春笋",     ["Braised bamboo shoots", "You men sun"]),
        ("番茄炒蛋",     ["Tomato scrambled egg", "Stir-fried tomato eggs"]),
        ("红烧带鱼",     ["Braised hairtail", "Hong shao dai yu"]),
        ("葱油拌面",     ["Cong you ban mian", "Scallion oil noodles"]),
    ],
    "02-jiangzhe": [
        ("狮子头",       ["Lion's head meatball", "Shizitou"]),
        ("响油鳝糊",     ["Eel paste shanghai", "Xiang you shan hu"]),
        ("醉鸡",         ["Drunken chicken", "Zui ji"]),
        ("松鼠鳜鱼",     ["Squirrel fish", "Songshu guiyu"]),
        ("八宝饭",       ["Eight treasure rice", "Babao fan"]),
        ("阳春面",       ["Yang chun mian", "Plain noodles soup"]),
        ("白切鸡",       ["White cut chicken", "Bai qie ji"]),
    ],
    "03-cantonese": [
        ("白切鸡",       ["White cut chicken", "Bai qie ji"]),
        ("叉烧",         ["Char siu", "Chinese barbecue pork"]),
        ("豉油鸡",       ["Soy sauce chicken", "See yau gai"]),
        ("虾饺",         ["Har gow", "Shrimp dumpling"]),
        ("烧鹅",         ["Roast goose", "Siu ngo"]),
        ("艇仔粥",       ["Sampan congee", "Ting zai juk"]),
        ("肠粉",         ["Cheung fun", "Rice noodle roll"]),
        ("蚝油生菜",     ["Oyster sauce lettuce"]),
    ],
    "04-sichuan": [
        ("麻婆豆腐",     ["Mapo tofu"]),
        ("回锅肉",       ["Twice cooked pork", "Hui guo rou"]),
        ("鱼香肉丝",     ["Yu xiang rou si", "Fish fragrant pork"]),
        ("宫保鸡丁",     ["Kung pao chicken"]),
        ("夫妻肺片",     ["Fu qi fei pian"]),
        ("水煮牛肉",     ["Shui zhu beef"]),
        ("担担面",       ["Dan dan noodles"]),
        ("辣子鸡",       ["La zi ji"]),
    ],
    "05-northern": [
        ("饺子",         ["Jiaozi", "Chinese dumpling"]),
        ("炸酱面",       ["Zha jiang mian"]),
        ("葱爆羊肉",     ["Cong bao yang rou", "Scallion lamb"]),
        ("锅包肉",       ["Guo bao rou"]),
        ("地三鲜",       ["Di san xian"]),
        ("醋溜白菜",     ["Vinegar cabbage"]),
        ("西红柿鸡蛋面", ["Tomato egg noodles"]),
        ("烙饼",         ["Lao bing", "Chinese flatbread"]),
    ],
    "06-japan-korea": [
        ("亲子丼",       ["Oyakodon"]),
        ("照烧鸡腿",     ["Teriyaki chicken"]),
        ("味噌汤",       ["Miso soup"]),
        ("生姜烧",       ["Shogayaki", "Ginger pork"]),
        ("石锅拌饭",     ["Bibimbap"]),
        ("泡菜炒饭",     ["Kimchi fried rice"]),
        ("部队锅",       ["Budae jjigae", "Army stew"]),
        ("韩式煎饼",     ["Pajeon", "Kimchi pancake"]),
    ],
    "07-southeast-asia": [
        ("冬阴功汤",     ["Tom yum kung"]),
        ("绿咖喱",       ["Green curry"]),
        ("泰式炒河粉",   ["Pad thai"]),
        ("芒果糯米饭",   ["Mango sticky rice"]),
        ("越南河粉",     ["Pho bo"]),
        ("越南春卷",     ["Goi cuon", "Vietnamese spring roll"]),
        ("越南法包",     ["Banh mi"]),
        ("叻沙",         ["Laksa"]),
    ],
    "08-india": [
        ("黄油鸡",       ["Butter chicken"]),
        ("羊肉咖喱",     ["Lamb curry"]),
        ("印度香饭",     ["Biryani"]),
        ("达尔",         ["Dal", "Indian lentil"]),
        ("印度烤饼",     ["Naan"]),
        ("玛萨拉茶",     ["Masala chai"]),
        ("羊肉巴尔蒂",   ["Balti curry"]),
        ("帕尼尔",       ["Palak paneer"]),
    ],
    "09-french": [
        ("红酒炖牛肉",   ["Boeuf bourguignon"]),
        ("红酒炖鸡",     ["Coq au vin"]),
        ("奶油蘑菇汤",   ["Cream of mushroom soup"]),
        ("法式洋葱汤",   ["French onion soup"]),
        ("普罗旺斯炖菜", ["Ratatouille"]),
        ("尼斯沙拉",     ["Salade nicoise"]),
        ("克拉芙缇",     ["Clafoutis"]),
        ("法式蛋饼",     ["Quiche lorraine"]),
    ],
    "10-italian": [
        ("番茄意面",     ["Spaghetti pomodoro"]),
        ("卡邦尼意面",   ["Carbonara"]),
        ("青酱意面",     ["Pesto pasta"]),
        ("玛格丽特披萨", ["Pizza margherita"]),
        ("烩饭",         ["Risotto milanese"]),
        ("肉酱面",       ["Ragu bolognese"]),
        ("提拉米苏",     ["Tiramisu"]),
        ("帕尔玛火腿",   ["Prosciutto melon"]),
    ],
    "11-spanish": [
        ("土豆煎蛋饼",   ["Tortilla espanola", "Spanish omelette"]),
        ("蒜虾",         ["Gambas al ajillo"]),
        ("大虾大蒜",     ["Gambas pil pil"]),
        ("辣味土豆",     ["Patatas bravas"]),
        ("番茄面包",     ["Pan con tomate"]),
        ("海鲜饭",       ["Paella valenciana"]),
        ("加斯帕乔",     ["Gazpacho"]),
        ("墨鱼",         ["Calamares a la romana"]),
    ],
}

ACCEPTABLE_LICENSES = {
    "CC BY 2.0", "CC BY 2.5", "CC BY 3.0", "CC BY 4.0",
    "CC BY-SA 2.0", "CC BY-SA 2.5", "CC BY-SA 3.0", "CC BY-SA 4.0",
    "CC0", "PDM", "Public domain",
}

UA = "RecipeBookImageFetcher/1.0 (https://github.com/yingwang/recipes)"


def slugify(name: str) -> str:
    s = re.sub(r"[^一-鿿A-Za-z0-9]+", "-", name).strip("-")
    return s.lower()


def search_commons(query: str, limit: int = 15) -> list[dict]:
    params = {
        "action": "query", "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    pages = data.get("query", {}).get("pages", {})
    return list(pages.values())


def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def pick_image(results: list[dict]) -> dict | None:
    candidates = []
    for p in results:
        info = (p.get("imageinfo") or [{}])[0]
        em = info.get("extmetadata") or {}
        license_short = (em.get("LicenseShortName") or {}).get("value", "")
        mime = info.get("mime", "")
        w = info.get("width", 0) or 0
        h = info.get("height", 0) or 0
        if license_short not in ACCEPTABLE_LICENSES:
            continue
        if mime not in {"image/jpeg", "image/png", "image/webp"}:
            continue
        if max(w, h) < 800:
            continue
        candidates.append((w * h, p, info, em, license_short))
    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0], reverse=True)
    _, page, info, em, license_short = candidates[0]
    return {
        "title": page.get("title"),
        "url": info.get("url").split("?")[0],
        "license": license_short,
        "author": strip_html((em.get("Artist") or {}).get("value", "")),
        "credit": strip_html((em.get("Credit") or {}).get("value", "")),
        "width": info.get("width"),
        "height": info.get("height"),
        "mime": info.get("mime"),
    }


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r, dest.open("wb") as f:
        while chunk := r.read(64 * 1024):
            f.write(chunk)


def insert_image_in_chapter(chapter_path: Path, dish_name: str, rel_image: str) -> bool:
    """Insert ![dish](path){ width="360" .center } after the `## 菜名` heading.

    Returns True if file was modified. Skips if image already inserted for
    this dish (idempotent).
    """
    text = chapter_path.read_text()
    heading = f"## {dish_name}"
    if heading not in text:
        return False
    img_md = f'![{dish_name}]({rel_image})' + '{ width="360" .center }'
    # Skip if already inserted
    if img_md in text or f"({rel_image})" in text:
        return False
    # Insert blank line then image after the heading line
    new_text = text.replace(
        heading + "\n",
        heading + "\n\n" + img_md + "\n",
        1,
    )
    if new_text == text:
        return False
    chapter_path.write_text(new_text)
    return True


def main() -> None:
    DISH_IMG_DIR.mkdir(parents=True, exist_ok=True)
    credits_existing = CREDITS.read_text() if CREDITS.exists() else ""
    new_credit_blocks: list[str] = []

    success = 0
    failed = 0
    skipped = 0

    for chapter_slug, dishes in DISH_QUERIES.items():
        chapter_path = CHAPTERS / f"{chapter_slug}.md"
        if not chapter_path.exists():
            print(f"[skip] {chapter_slug}: chapter file missing", file=sys.stderr)
            continue

        for dish_name, queries in dishes:
            slug = f"{chapter_slug}-{slugify(dish_name)}"
            existing = list(DISH_IMG_DIR.glob(f"{slug}.*"))
            if existing:
                skipped += 1
                continue

            chosen = None
            for q in queries:
                try:
                    results = search_commons(q)
                except Exception as e:
                    print(f"[warn] {slug}: search '{q}' failed: {e}", file=sys.stderr)
                    continue
                chosen = pick_image(results)
                if chosen:
                    chosen["query"] = q
                    break
                time.sleep(0.3)

            if not chosen:
                print(f"[fail] {slug}: no acceptable image found")
                failed += 1
                continue

            ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[chosen["mime"]]
            dest = DISH_IMG_DIR / f"{slug}.{ext}"
            try:
                download(chosen["url"], dest)
            except Exception as e:
                print(f"[fail] {slug}: download failed: {e}", file=sys.stderr)
                failed += 1
                continue

            rel = f"../images/dishes/{dest.name}"
            inserted = insert_image_in_chapter(chapter_path, dish_name, rel)
            if not inserted:
                print(f"[warn] {slug}: insert into chapter failed (heading not found?)")

            commons_url = f"https://commons.wikimedia.org/wiki/{chosen['title'].replace(' ', '_')}"
            new_credit_blocks.append(
                f"### {chapter_slug} / {dish_name}\n\n"
                f"- File: `images/dishes/{dest.name}`\n"
                f"- Original: [{chosen['title']}]({commons_url})\n"
                f"- Author: {chosen['author'] or 'Unknown'}\n"
                f"- License: {chosen['license']}\n"
                f"- Search query: `{chosen['query']}`\n"
            )
            print(f"[ok]   {slug}: {dest.name}  [{chosen['license']}]  ({chosen['width']}x{chosen['height']})")
            success += 1
            time.sleep(0.5)

    if new_credit_blocks:
        marker = "## 菜级别图片"
        if marker not in credits_existing:
            credits_existing = credits_existing.rstrip() + f"\n\n{marker}\n\n"
        credits_existing = credits_existing.rstrip() + "\n\n" + "\n".join(new_credit_blocks) + "\n"
        CREDITS.write_text(credits_existing)

    print(f"\nDone. ok={success} skipped={skipped} failed={failed}")
    print(f"Images: {DISH_IMG_DIR}")
    print(f"Credits: {CREDITS}")


if __name__ == "__main__":
    main()

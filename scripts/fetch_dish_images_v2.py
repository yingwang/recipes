"""Fetch CC images for dishes that still don't have one.

Maps real chapter heading -> fallback search queries. Inserts after the
exact heading line. Uses slugify_heading to derive image filename.

Run: python3 scripts/fetch_dish_images_v2.py
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

# (chapter_slug, exact heading, [search queries])
TARGETS: list[tuple[str, str, list[str]]] = [
    # 01-hangzhou
    ("01-hangzhou", "萝卜烧肉", ["Daikon braised pork", "Luobu shao rou", "Pork radish stew"]),
    ("01-hangzhou", "韭黄炒蛋", ["Yellow chives egg stir fry", "Jiu huang"]),
    ("01-hangzhou", "雪菜笋丝肉丝", ["Xue cai bamboo pork", "Snow vegetable bamboo shoots"]),
    ("01-hangzhou", "萝卜丝鲫鱼汤", ["Crucian carp daikon soup", "Ji yu tang"]),
    ("01-hangzhou", "炒青菜", ["Stir fried greens", "Bok choy stir fry"]),
    ("01-hangzhou", "肉饼蛋汤", ["Steamed pork egg cake", "Rou bing"]),
    ("01-hangzhou", "油爆虾", ["You bao xia", "Oil exploded shrimp"]),
    # 02-jiangzhe
    ("02-jiangzhe", "大煮干丝", ["Da zhu gan si", "Tofu skin julienne soup"]),
    ("02-jiangzhe", "文思豆腐", ["Wensi tofu"]),
    ("02-jiangzhe", "红烧划水", ["Hong shao hua shui", "Braised fish tail"]),
    ("02-jiangzhe", "葱烤鲫鱼", ["Cong kao ji yu", "Scallion crucian carp"]),
    ("02-jiangzhe", "雪菜黄鱼", ["Xue cai huang yu", "Snow vegetable yellow croaker"]),
    ("02-jiangzhe", "葱油海蜇", ["Cong you hai zhe", "Jellyfish salad scallion"]),
    # 03-cantonese
    ("03-cantonese", "清蒸鱼", ["Cantonese steamed fish", "Qing zheng yu"]),
    ("03-cantonese", "滑蛋虾仁", ["Hua dan xia ren", "Soft scrambled egg shrimp"]),
    ("03-cantonese", "干炒牛河", ["Beef chow fun", "Gan chao niu he"]),
    ("03-cantonese", "上汤娃娃菜", ["Shang tang wa wa cai", "Baby cabbage broth"]),
    ("03-cantonese", "莲藕排骨汤", ["Lotus root pork rib soup", "Lian ou pai gu"]),
    ("03-cantonese", "番茄炖牛腩", ["Tomato beef brisket stew", "Niu nan"]),
    ("03-cantonese", "煲仔饭", ["Claypot rice", "Bo zai fan"]),
    # 04-sichuan
    ("04-sichuan", "蒜泥白肉", ["Suan ni bai rou", "Pork garlic sauce"]),
    ("04-sichuan", "凉拌口水鸡", ["Mouth watering chicken", "Kou shui ji"]),
    ("04-sichuan", "干煸四季豆", ["Gan bian si ji dou", "Dry fried green beans"]),
    ("04-sichuan", "青椒肉丝", ["Qing jiao rou si", "Green pepper pork shred"]),
    ("04-sichuan", "醋溜白菜", ["Cu liu bai cai", "Vinegar cabbage stir fry"]),
    ("04-sichuan", "红油抄手", ["Hong you chao shou", "Sichuan wonton chili oil"]),
    # 05-northern
    ("05-northern", "小鸡炖蘑菇", ["Xiao ji dun mo gu", "Chicken mushroom stew"]),
    ("05-northern", "拍黄瓜", ["Pai huang gua", "Smashed cucumber"]),
    ("05-northern", "醋溜土豆丝", ["Cu liu tu dou si", "Vinegar potato shred"]),
    ("05-northern", "韭菜盒子（家常烫面版）", ["Jiu cai he zi", "Chinese chive pocket"]),
    ("05-northern", "凉拌粉丝", ["Liang ban fen si", "Cellophane noodles cold"]),
    # 06-japan-korea
    ("06-japan-korea", "寿司饭基础（醋饭）", ["Sushi rice", "Sumeshi"]),
    ("06-japan-korea", "日式高汤 dashi 一番出汁（一番だし）", ["Dashi", "Japanese stock"]),
    ("06-japan-korea", "茶碗蒸（ちゃわんむし）", ["Chawanmushi", "Steamed egg custard"]),
    ("06-japan-korea", "日式煎蛋卷 出汁玉子焼き（だしたまごやき）", ["Tamagoyaki", "Dashimaki"]),
    ("06-japan-korea", "韩式辣豆腐汤（순두부찌개 / sundubu jjigae）", ["Sundubu jjigae", "Soft tofu stew"]),
    # 07-southeast-asia
    ("07-southeast-asia", "泰式罗勒猪肉碎饭（Pad Krapow Moo）", ["Pad krapow", "Thai basil pork rice"]),
    ("07-southeast-asia", "越南鸡饭（Cơm Gà）", ["Com ga", "Vietnamese chicken rice"]),
    ("07-southeast-asia", "越南鱼露蘸汁（Nước Chấm）", ["Nuoc cham", "Vietnamese fish sauce"]),
    ("07-southeast-asia", "越南炼乳冰咖啡（Cà Phê Sữa Đá）", ["Vietnamese iced coffee", "Ca phe sua da"]),
    # 08-india
    ("08-india", "鹰嘴豆咖喱 Chana Masala", ["Chana masala", "Chickpea curry"]),
    ("08-india", "土豆花椰菜咖喱 Aloo Gobi", ["Aloo gobi", "Potato cauliflower curry"]),
    ("08-india", "黄瓜酸奶 Raita", ["Raita", "Indian yogurt sauce"]),
    ("08-india", "Chicken Tikka Masala", ["Chicken tikka masala"]),
    ("08-india", "Garam Masala 香料配方（印度菜的灵魂复合香料）", ["Garam masala spices"]),
    # 09-french
    ("09-french", "马赛海鲜汤 / Bouillabaisse", ["Bouillabaisse"]),
    ("09-french", "牛排薯条 + 黑椒汁 / Steak Frites + Sauce au Poivre", ["Steak frites", "Steak au poivre"]),
    ("09-french", "焦糖布丁 / Crème Brûlée", ["Creme brulee"]),
    ("09-french", "甜薄饼 / Crêpes Sucrées", ["Crepes sucrees", "French crepes"]),
    # 10-italian
    ("10-italian", "Cacio e Pepe（黑椒奶酪意面）", ["Cacio e pepe"]),
    ("10-italian", "Aglio e Olio（蒜油意面）", ["Aglio e olio", "Spaghetti aglio olio"]),
    ("10-italian", "Osso Buco（炖牛膝）", ["Osso buco", "Veal shank"]),
    ("10-italian", "Caprese（番茄莫扎里拉沙拉）", ["Caprese salad"]),
    # 11-spanish
    ("11-spanish", "Croquetas de Jamón（火腿可乐饼）", ["Croquetas jamon", "Spanish ham croquettes"]),
    ("11-spanish", "Pulpo a la Gallega（加利西亚章鱼）", ["Pulpo a la gallega", "Galician octopus"]),
    ("11-spanish", "Sangría（夏日水果红酒）", ["Sangria"]),
]

ACCEPTABLE_LICENSES = {
    "CC BY 2.0", "CC BY 2.5", "CC BY 3.0", "CC BY 4.0",
    "CC BY-SA 2.0", "CC BY-SA 2.5", "CC BY-SA 3.0", "CC BY-SA 4.0",
    "CC0", "PDM", "Public domain",
}

UA = "RecipeBookImageFetcher/1.0 (https://github.com/yingwang/recipes)"


def slugify_heading(heading: str) -> str:
    h = heading
    for sep in ["（", "(", " / ", " "]:
        if sep in h:
            h = h.split(sep, 1)[0]
    return h.strip().replace("è", "e").replace("é", "e").replace("ç", "c")\
        .replace("à", "a").replace("ñ", "n").replace("í", "i").replace("ó", "o")


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
    return list(data.get("query", {}).get("pages", {}).values())


def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def pick_image(results: list[dict]) -> dict | None:
    candidates = []
    for p in results:
        info = (p.get("imageinfo") or [{}])[0]
        em = info.get("extmetadata") or {}
        license_short = (em.get("LicenseShortName") or {}).get("value", "")
        mime = info.get("mime", "")
        w, h = info.get("width", 0) or 0, info.get("height", 0) or 0
        if license_short not in ACCEPTABLE_LICENSES: continue
        if mime not in {"image/jpeg", "image/png", "image/webp"}: continue
        if max(w, h) < 800: continue
        candidates.append((w * h, p, info, em, license_short))
    if not candidates: return None
    candidates.sort(key=lambda c: c[0], reverse=True)
    _, page, info, em, ls = candidates[0]
    return {
        "title": page.get("title"),
        "url": info.get("url").split("?")[0],
        "license": ls,
        "author": strip_html((em.get("Artist") or {}).get("value", "")),
        "width": info.get("width"),
        "height": info.get("height"),
        "mime": info.get("mime"),
    }


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r, dest.open("wb") as f:
        while chunk := r.read(64 * 1024):
            f.write(chunk)


def insert_image(chapter_path: Path, heading: str, rel: str, alt: str) -> bool:
    text = chapter_path.read_text()
    if rel in text: return False
    heading_line = f"## {heading}"
    if heading_line + "\n" not in text: return False
    img_md = f'![{alt}]({rel})' + '{ width="360" .center }'
    new = text.replace(heading_line + "\n", heading_line + "\n\n" + img_md + "\n", 1)
    if new == text: return False
    chapter_path.write_text(new)
    return True


def main() -> None:
    DISH_IMG_DIR.mkdir(parents=True, exist_ok=True)
    new_credits = []
    ok = fail = skipped = 0

    for chapter, heading, queries in TARGETS:
        slug = slugify_heading(heading)
        stem = f"{chapter}-{slug}"
        existing = list(DISH_IMG_DIR.glob(f"{stem}.*"))
        if existing:
            skipped += 1
            continue

        chosen = None
        for q in queries:
            try:
                results = search_commons(q)
            except Exception as e:
                print(f"[warn] {stem}: '{q}': {e}", file=sys.stderr)
                continue
            chosen = pick_image(results)
            if chosen:
                chosen["query"] = q
                break
            time.sleep(0.3)

        if not chosen:
            print(f"[fail] {stem}: no image"); fail += 1; continue

        ext = {"image/jpeg":"jpg","image/png":"png","image/webp":"webp"}[chosen["mime"]]
        dest = DISH_IMG_DIR / f"{stem}.{ext}"
        try:
            download(chosen["url"], dest)
        except Exception as e:
            print(f"[fail] {stem}: dl: {e}"); fail += 1; continue

        rel = f"../images/dishes/{dest.name}"
        chapter_path = CHAPTERS / f"{chapter}.md"
        inserted = insert_image(chapter_path, heading, rel, slug)
        if not inserted:
            print(f"[warn] {stem}: insert failed (heading not found)")

        commons_url = f"https://commons.wikimedia.org/wiki/{chosen['title'].replace(' ', '_')}"
        new_credits.append(
            f"### {chapter} / {slug}\n\n"
            f"- File: `images/dishes/{dest.name}`\n"
            f"- Original: [{chosen['title']}]({commons_url})\n"
            f"- Author: {chosen['author'] or 'Unknown'}\n"
            f"- License: {chosen['license']}\n"
            f"- Search query: `{chosen['query']}`\n"
        )
        print(f"[ok]   {stem}: {dest.name} [{chosen['license']}]")
        ok += 1
        time.sleep(0.5)

    if new_credits:
        text = CREDITS.read_text()
        text = text.rstrip() + "\n\n" + "\n".join(new_credits) + "\n"
        CREDITS.write_text(text)

    print(f"\nok={ok} skipped={skipped} fail={fail}")


if __name__ == "__main__":
    main()

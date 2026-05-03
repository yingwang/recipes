"""Delete clearly-wrong dish images, try better-targeted refetch.

Each entry is (chapter, dish_slug, [better_queries]). For each:
1. Delete current image and remove markdown line in chapter
2. Try better queries on Commons; download best CC match
3. Re-insert markdown line if found; otherwise leave empty (better none than wrong)

Run: python3 scripts/fix_bad_images.py
"""
from __future__ import annotations

import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHAPTERS = ROOT / "docs" / "chapters"
DISH_IMG_DIR = ROOT / "docs" / "images" / "dishes"
CREDITS = ROOT / "docs" / "images" / "CREDITS.md"

BAD = [
    # (chapter, image_stem, heading_in_chapter, [better_queries])
    ("01-hangzhou", "01-hangzhou-腌笃鲜", "腌笃鲜",
     ["yan du xian soup", "Salted Fresh", "pickled fresh soup pork bamboo"]),
    ("01-hangzhou", "01-hangzhou-油焖春笋", "油焖春笋",
     ["braised bamboo shoots Chinese", "you men sun", "spring bamboo shoots cooked"]),
    ("01-hangzhou", "01-hangzhou-红烧带鱼", "红烧带鱼",
     ["braised hairtail", "largehead hairtail cooked", "belt fish dish"]),
    ("01-hangzhou", "01-hangzhou-番茄炒蛋", "番茄炒蛋",
     ["scrambled eggs tomatoes Chinese", "fan qie chao dan", "tomato eggs stir fry"]),
    ("01-hangzhou", "01-hangzhou-葱油拌面", "葱油拌面",
     ["cong you ban mian", "Shanghai scallion oil noodles"]),
    ("01-hangzhou", "01-hangzhou-家常红烧肉", "家常红烧肉",
     ["hong shao rou", "red cooked pork belly", "braised pork belly Chinese"]),
    ("01-hangzhou", "01-hangzhou-梅干菜烧肉", "梅干菜烧肉",
     ["mei cai kou rou", "preserved vegetable pork", "mei gan cai pork"]),
    ("01-hangzhou", "01-hangzhou-萝卜烧肉", "萝卜烧肉",
     ["pork radish stew Chinese", "Chinese braised pork daikon"]),
    ("01-hangzhou", "01-hangzhou-韭黄炒蛋", "韭黄炒蛋",
     ["yellow chives egg", "blanched chives stir fried egg"]),
    ("01-hangzhou", "01-hangzhou-萝卜丝鲫鱼汤", "萝卜丝鲫鱼汤",
     ["crucian carp soup", "white fish soup daikon"]),
    ("01-hangzhou", "01-hangzhou-炒青菜", "炒青菜",
     ["stir fried bok choy", "stir fried green vegetables Chinese"]),
    ("01-hangzhou", "01-hangzhou-油爆虾", "油爆虾",
     ["shanghai oil shrimp dish", "Chinese stir fried shrimp"]),
    ("02-jiangzhe", "02-jiangzhe-响油鳝糊", "响油鳝糊",
     ["xiang you shan hu", "Shanghai eel rice", "stir fried eel Chinese"]),
    ("02-jiangzhe", "02-jiangzhe-松鼠桂鱼", "松鼠桂鱼",
     ["squirrel mandarin fish dish", "Songshu Yu", "Suzhou sweet sour fish"]),
    ("02-jiangzhe", "02-jiangzhe-葱烤鲫鱼", "葱烤鲫鱼",
     ["crucian carp scallion", "fish stew scallion Chinese"]),
    ("02-jiangzhe", "02-jiangzhe-雪菜黄鱼", "雪菜黄鱼",
     ["yellow croaker dish", "Chinese yellow fish"]),
    ("02-jiangzhe", "02-jiangzhe-葱油海蜇", "葱油海蜇",
     ["jellyfish salad", "Chinese cold jellyfish"]),
    ("04-sichuan", "04-sichuan-麻婆豆腐", "麻婆豆腐",
     ["mapo doufu", "ma po tofu", "Sichuan tofu dish"]),
    ("04-sichuan", "04-sichuan-蒜泥白肉", "蒜泥白肉",
     ["garlic pork slices Sichuan", "suan ni bai rou", "Chinese garlic pork"]),
    ("04-sichuan", "04-sichuan-凉拌口水鸡", "凉拌口水鸡",
     ["saliva chicken", "kou shui ji"]),
    ("04-sichuan", "04-sichuan-青椒肉丝", "青椒肉丝",
     ["green pepper pork shred", "qing jiao rou si", "stir fried bell pepper pork"]),
    ("04-sichuan", "04-sichuan-醋溜白菜", "醋溜白菜",
     ["vinegar cabbage Chinese", "stir fried cabbage vinegar"]),
    ("04-sichuan", "04-sichuan-红油抄手", "红油抄手",
     ["Sichuan wonton chili oil", "hong you chao shou", "Chengdu wonton spicy"]),
    ("05-northern", "05-northern-韭菜盒子", "韭菜盒子（家常烫面版）",
     ["Chinese chive pocket pan fried", "jiu cai he zi"]),
    ("07-southeast-asia", "07-southeast-asia-越南鸡饭", "越南鸡饭（Cơm Gà）",
     ["com ga Vietnamese", "Vietnamese chicken rice plate"]),
    ("07-southeast-asia", "07-southeast-asia-越南鱼露蘸汁", "越南鱼露蘸汁（Nước Chấm）",
     ["nuoc cham", "Vietnamese fish sauce dipping"]),
    ("07-southeast-asia", "07-southeast-asia-越南炼乳冰咖啡", "越南炼乳冰咖啡（Cà Phê Sữa Đá）",
     ["ca phe sua da", "Vietnamese iced coffee condensed milk"]),
    ("03-cantonese", "03-cantonese-番茄炖牛腩", "番茄炖牛腩",
     ["tomato beef brisket Cantonese", "Chinese tomato beef stew"]),
    ("03-cantonese", "03-cantonese-蜜汁叉烧", "蜜汁叉烧（家庭烤箱版）",
     ["char siu Cantonese", "honey roast pork Chinese", "char siew"]),
    ("10-italian", "10-italian-Carbonara", "Carbonara（罗马蛋黄培根意面）",
     ["spaghetti alla carbonara", "carbonara pasta Roman"]),
    ("09-french", "09-french-牛排薯条", "牛排薯条 + 黑椒汁 / Steak Frites + Sauce au Poivre",
     ["steak frites French bistro", "steak fries Paris"]),
]

ACCEPTABLE = {
    "CC BY 2.0", "CC BY 2.5", "CC BY 3.0", "CC BY 4.0",
    "CC BY-SA 2.0", "CC BY-SA 2.5", "CC BY-SA 3.0", "CC BY-SA 4.0",
    "CC0", "PDM", "Public domain",
}
UA = "RecipeBookImageFetcher/1.0 (https://github.com/yingwang/recipes)"

# Filename keyword filters: if title contains any of these, reject
# (prevents the historical-painting / random-junk traps we saw)
TITLE_REJECT = [
    "painting", "statue", "figure", "character", "currency", "coin",
    "banknote", "Cash-note", "pellet", "platform", "station", "train",
    "publishing", "förlags", "DeepSeek", "pipeline", "diagram", "menu",
    "Western Xia", "Sui and Tang", "Wang Ximeng", "scroll", "manuscript",
    "calligraphy", "map of", "logo", "icon", "chart",
]


def search(q, limit=20):
    params = {"action":"query","format":"json","generator":"search","gsrsearch":q,
              "gsrnamespace":"6","gsrlimit":str(limit),"prop":"imageinfo",
              "iiprop":"url|extmetadata|size|mime"}
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return list(json.load(r).get("query",{}).get("pages",{}).values())


def strip_html(s):
    s = re.sub(r"<[^>]+>","",s or "")
    return re.sub(r"\s+"," ",s).strip()


def pick(results):
    candidates = []
    for p in results:
        info = (p.get("imageinfo") or [{}])[0]
        em = info.get("extmetadata") or {}
        ls = (em.get("LicenseShortName") or {}).get("value","")
        mime = info.get("mime","")
        w, h = info.get("width",0) or 0, info.get("height",0) or 0
        title = p.get("title","")
        if ls not in ACCEPTABLE: continue
        if mime not in {"image/jpeg","image/png","image/webp"}: continue
        if max(w,h) < 800: continue
        if any(kw.lower() in title.lower() for kw in TITLE_REJECT): continue
        candidates.append((w*h, p, info, em, ls))
    if not candidates: return None
    candidates.sort(key=lambda c: c[0], reverse=True)
    _, page, info, em, ls = candidates[0]
    return {"title":page.get("title"),"url":info.get("url").split("?")[0],
            "license":ls,"author":strip_html((em.get("Artist") or {}).get("value","")),
            "width":info.get("width"),"height":info.get("height"),"mime":info.get("mime")}


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent":UA})
    with urllib.request.urlopen(req, timeout=60) as r, dest.open("wb") as f:
        while c := r.read(64*1024): f.write(c)


def remove_image_line(chapter_path: Path, stem: str) -> bool:
    text = chapter_path.read_text()
    pattern = re.compile(rf"^!\[[^\]]*\]\(\.\./images/dishes/{re.escape(stem)}\.[a-z]+\)\{{[^}}]*\}}\n\n", re.MULTILINE)
    new = pattern.sub("", text)
    if new == text:
        # try without trailing blank line
        pattern2 = re.compile(rf"^!\[[^\]]*\]\(\.\./images/dishes/{re.escape(stem)}\.[a-z]+\)\{{[^}}]*\}}\n", re.MULTILINE)
        new = pattern2.sub("", text)
    if new == text: return False
    chapter_path.write_text(new)
    return True


def insert_after_heading(chapter_path: Path, heading: str, image_filename: str, alt: str) -> bool:
    text = chapter_path.read_text()
    rel = f"../images/dishes/{image_filename}"
    if rel in text: return False
    line = f"## {heading}"
    if line + "\n" not in text: return False
    img = f'![{alt}]({rel})' + '{ width="360" .center }'
    new = text.replace(line + "\n", line + "\n\n" + img + "\n", 1)
    if new == text: return False
    chapter_path.write_text(new)
    return True


def main():
    refetched = 0
    deleted_only = 0

    for chapter, stem, heading, queries in BAD:
        # Step 1: delete current bad file
        for ext in ["jpg","png","webp"]:
            p = DISH_IMG_DIR / f"{stem}.{ext}"
            if p.exists():
                p.unlink()
                print(f"[del] {stem}.{ext}")

        # Step 2: remove markdown line in chapter
        chapter_path = CHAPTERS / f"{chapter}.md"
        remove_image_line(chapter_path, stem)

        # Step 3: try better queries
        chosen = None
        for q in queries:
            try:
                results = search(q)
            except Exception as e:
                print(f"[warn] {stem}: '{q}': {e}", file=sys.stderr)
                continue
            chosen = pick(results)
            if chosen:
                chosen["query"] = q
                break
            time.sleep(0.3)

        if not chosen:
            print(f"[no replacement] {stem}: deleted, no usable replacement found")
            deleted_only += 1
            continue

        ext = {"image/jpeg":"jpg","image/png":"png","image/webp":"webp"}[chosen["mime"]]
        dest = DISH_IMG_DIR / f"{stem}.{ext}"
        try:
            download(chosen["url"], dest)
        except Exception as e:
            print(f"[fail dl] {stem}: {e}")
            deleted_only += 1
            continue

        alt = stem.split("-",2)[2]
        ok = insert_after_heading(chapter_path, heading, dest.name, alt)
        commons_url = f"https://commons.wikimedia.org/wiki/{chosen['title'].replace(' ','_')}"
        print(f"[refetched] {stem}: {chosen['title']} [{chosen['license']}] {'inserted' if ok else 'INSERT FAILED'}")
        refetched += 1
        time.sleep(0.5)

    print(f"\nrefetched={refetched} deleted_only={deleted_only}")


if __name__ == "__main__":
    main()

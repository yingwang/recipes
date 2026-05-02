"""Fetch one Creative Commons hero image per chapter from Wikimedia Commons.

For each (chapter, search_term) pair: query the Commons search API in the
File namespace, walk results until we find a CC-licensed image of decent
size, download it to docs/images/chapters/, and append a CREDITS entry.

Run with: python3 scripts/fetch_images.py
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
IMG_DIR = ROOT / "docs" / "images" / "chapters"
CREDITS = ROOT / "docs" / "images" / "CREDITS.md"

# Chapter slug -> (search query, fallback queries...)
TARGETS: list[tuple[str, list[str]]] = [
    ("01-hangzhou",       ["Dongpo pork", "West Lake fish vinegar", "Hangzhou cuisine"]),
    ("02-jiangzhe",       ["Lion's head meatball", "Yangzhou cuisine", "Shizitou"]),
    ("03-cantonese",      ["Dim sum", "Char siu", "Cantonese cuisine"]),
    ("04-sichuan",        ["Mapo tofu", "Sichuan cuisine", "Hui guo rou"]),
    ("05-northern",       ["Jiaozi", "Chinese dumpling", "Beijing cuisine"]),
    ("06-japan-korea",    ["Sushi assortment", "Bibimbap", "Japanese cuisine"]),
    ("07-southeast-asia", ["Pho bo", "Pad Thai", "Tom yum kung"]),
    ("08-india",          ["Butter chicken", "Chicken biryani", "Indian cuisine"]),
    ("09-french",         ["Coq au vin", "Boeuf bourguignon", "Ratatouille dish"]),
    ("10-italian",        ["Spaghetti carbonara", "Risotto alla milanese", "Pesto pasta"]),
    ("11-spanish",        ["Paella valenciana", "Tapas", "Patatas bravas"]),
]

ACCEPTABLE_LICENSES = {
    "CC BY 2.0", "CC BY 2.5", "CC BY 3.0", "CC BY 4.0",
    "CC BY-SA 2.0", "CC BY-SA 2.5", "CC BY-SA 3.0", "CC BY-SA 4.0",
    "CC0", "PDM", "Public domain",
}

UA = "RecipeBookImageFetcher/1.0 (https://github.com/yingwang/recipes)"


def search_commons(query: str, limit: int = 20) -> list[dict]:
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
    # Prefer larger photos with acceptable license, JPEG/PNG only, min 800px
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


def main() -> None:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    credits_lines: list[str] = ["# Image credits\n"]
    credits_lines.append(
        "All chapter hero images are sourced from Wikimedia Commons under "
        "Creative Commons licenses. Each image's original Commons file, author, "
        "and license are listed below. Reuse must follow the per-image license.\n"
    )

    for slug, queries in TARGETS:
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
        if not chosen:
            print(f"[fail] {slug}: no acceptable image found")
            continue

        ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[chosen["mime"]]
        dest = IMG_DIR / f"{slug}.{ext}"
        try:
            download(chosen["url"], dest)
        except Exception as e:
            print(f"[fail] {slug}: download failed: {e}", file=sys.stderr)
            continue

        commons_url = f"https://commons.wikimedia.org/wiki/{chosen['title'].replace(' ', '_')}"
        credits_lines.append(
            f"## {slug}\n\n"
            f"- File: `images/chapters/{dest.name}`\n"
            f"- Original: [{chosen['title']}]({commons_url})\n"
            f"- Author: {chosen['author'] or 'Unknown'}\n"
            f"- License: {chosen['license']}\n"
            f"- Search query: `{chosen['query']}`\n"
        )
        print(f"[ok]   {slug}: {dest.name}  [{chosen['license']}]  ({chosen['width']}x{chosen['height']})")

    CREDITS.write_text("\n".join(credits_lines) + "\n")
    print(f"\nWrote credits to {CREDITS}")


if __name__ == "__main__":
    main()

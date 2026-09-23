# -*- coding: utf-8 -*-
"""Разбор sitemap.xml основного и стейджинг-домена prom-opora.

Результат: sitemap/main-urls.txt (адреса основного домена),
sitemap/new-urls.txt (стейджинг), sitemap/compare-main-new.txt (сверка путей).
"""
import re
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parent


def parse_loc(path):
    locs = re.findall(r"<loc>([^<]+)</loc>", path.read_text(encoding="utf-8"))
    return [u.strip() for u in locs]


def norm(url):
    """Путь без схемы/домена, без хвостового слэша (кроме корня), без параметров."""
    p = urlsplit(url)
    path = p.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return path + (("?" + p.query) if p.query else "")


def main():
    main_urls = parse_loc(BASE / "sitemap" / "sitemap-prom-opora.ru.xml")
    new_urls = parse_loc(BASE / "sitemap" / "sitemap-new.prom-opora.ru.xml")

    (BASE / "sitemap" / "main-urls.txt").write_text(
        "\n".join(sorted(main_urls)) + "\n", encoding="utf-8")
    (BASE / "sitemap" / "new-urls.txt").write_text(
        "\n".join(sorted(new_urls)) + "\n", encoding="utf-8")

    main_paths = {norm(u) for u in main_urls}
    new_paths = {norm(u) for u in new_urls}

    lines = []
    lines.append("Пути в main, которых нет в new:")
    lines += sorted(main_paths - new_paths) or ["(нет)"]
    lines.append("")
    lines.append("Пути в new, которых нет в main:")
    lines += sorted(new_paths - main_paths) or ["(нет)"]
    (BASE / "sitemap" / "compare-main-new.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")

    print(f"main: {len(main_urls)} адресов, {len(main_paths)} путей")
    print(f"new:  {len(new_urls)} адресов, {len(new_paths)} путей")
    print(f"только в main: {len(main_paths - new_paths)}, только в new: {len(new_paths - main_paths)}")
    dup = len(main_urls) - len(main_paths)
    print(f"дубли путей в main (с параметрами): {dup}")


if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
"""Сбор уникальных ссылок со страниц обхода и проверка доступности.

Логика:
- внутренние HTML-адреса, которые есть в sitemap: статус уже известен из обхода;
- внутренние адреса вне sitemap и все ресурсы (картинки, стили, скрипты):
  проверяются HEAD-запросом (при 405/403 — GET с обрезкой тела);
- внешние домены: проверяются HEAD с таймаутом, недоступные помечаются.

Результат: crawl/targets.json — уникальные адреса с источниками и статусами.
"""
import json
import sys
import time
from pathlib import Path
from urllib import request as urlreq
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parent
DOMAINS = ("prom-opora.ru", "www.prom-opora.ru")
UA = "Mozilla/5.0 (compatible; prom-opora-inventar/1.0; site owner audit)"
DELAY = 0.3
RETRY_WAIT = 15
ASSET_EXT = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".avif",
    ".css", ".js", ".pdf", ".zip", ".rar", ".woff", ".woff2", ".ttf", ".eot",
    ".otf", ".mp4", ".webm", ".xls", ".xlsx", ".doc", ".docx", ".csv",
)
SKIP_PREFIX = ("mailto:", "tel:", "javascript:", "data:", "#", "skype:", "viber:")

sys.stdout.reconfigure(encoding="utf-8")


def kind_of(url):
    low = url.lower()
    if any(low.startswith(p) for p in SKIP_PREFIX):
        return "skip"
    p = urlsplit(url)
    if not p.scheme:
        return "relative"
    if p.netloc in DOMAINS:
        if low.endswith(ASSET_EXT):
            return "asset"
        return "internal"
    # ресурс на чужом домене (картинки, стили, шрифты)
    if low.endswith(ASSET_EXT):
        return "external-asset"
    return "external"


def main():
    pages = json.loads((BASE / "crawl" / "pages.json").read_text(encoding="utf-8"))
    sitemap = {l.strip() for l in (BASE / "sitemap" / "main-urls.txt")
               .read_text(encoding="utf-8").splitlines() if l.strip()}

    targets = {}
    for src, rec in pages.items():
        fields = (("link", rec["links"]), ("img", rec["img"]),
                  ("css", rec["css"]), ("js", rec["js"]), ("iframe", rec["iframe"]))
        for field, urls in fields:
            for u in urls:
                # обрезаем якорь, склеиваем по каноническому виду
                frag = urlsplit(u)
                norm = u.split("#")[0]
                if not norm or norm.startswith(SKIP_PREFIX):
                    continue
                t = targets.setdefault(norm, {"kinds": set(), "sources": []})
                t["kinds"].add(field)
                if src not in t["sources"]:
                    t["sources"].append(src)

    # статусы страниц из обхода
    page_status = {r["url"]: r["status"] for r in pages.values()}
    # страница может быть записана и под другим адресом (после редиректа)
    # это учтено: ключи pages.json — адреса из sitemap

    def head_check(url):
        for attempt in range(3):
            try:
                req = urlreq.Request(url, headers={"User-Agent": UA},
                                     method="HEAD")
                with urlreq.urlopen(req, timeout=20) as r:
                    return r.status
            except urlreq.HTTPError as e:
                if e.code in (405, 403, 400, 501):
                    try:
                        req = urlreq.Request(url, headers={"User-Agent": UA},
                                             method="GET")
                        with urlreq.urlopen(req, timeout=20) as r:
                            r.read(2048)
                            return r.status
                    except urlreq.HTTPError as e2:
                        return e2.code
                    except Exception as e2:
                        return f"ошибка: {type(e2).__name__}"
                if e.code in (429, 503):
                    time.sleep(RETRY_WAIT)
                    continue
                return e.code
            except Exception as e:
                return f"ошибка: {type(e).__name__}"
        return "повторы исчерпаны"

    out = {}
    done = 0
    total = len(targets)
    for url, t in sorted(targets.items()):
        kind = kind_of(url)
        status = None
        if kind == "internal":
            st = page_status.get(url)
            if st is not None:
                status = st  # статус уже известен из обхода
            else:
                status = head_check(url)
                time.sleep(DELAY)
        elif kind in ("asset", "external-asset", "external"):
            status = head_check(url)
            time.sleep(DELAY)
        else:
            status = "не проверяется"
        done += 1
        if done % 50 == 0:
            print(f"[{done}/{total}]")
        out[url] = {
            "kind": kind, "status": status,
            "kinds": sorted(t["kinds"]), "sources": t["sources"],
            "in_sitemap": url in sitemap,
        }
        (BASE / "crawl" / "targets.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # сводка
    codes = {}
    for v in out.values():
        codes[str(v["status"])] = codes.get(str(v["status"]), 0) + 1
    print("статусы:", codes)
    print("уникальных адресов:", total)


if __name__ == "__main__":
    main()
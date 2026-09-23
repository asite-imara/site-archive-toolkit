# -*- coding: utf-8 -*-
"""Обход 462 страниц из sitemap prom-opora.ru.

Скачивает HTML (сохраняет в html/), извлекает мета-теги, canonical и ссылки.
Соседние страницы не скачивает — только записывает найденные ссылки
(сверка охвата делается позже сравнением с sitemap).

Результат: crawl/pages.json — постраничные данные.
"""
import json
import re
import sys
import time
import html as htmllib
from pathlib import Path
from urllib import request as urlreq
from urllib.parse import urljoin, urlsplit
from html.parser import HTMLParser

BASE = Path(__file__).resolve().parent
DOMAIN = "prom-opora.ru"
ORIGIN = f"https://{DOMAIN}"
UA = "Mozilla/5.0 (compatible; prom-opora-inventar/1.0; site owner audit)"
DELAY = 0.4
RETRY_WAIT = 15

sys.stdout.reconfigure(encoding="utf-8")


class PageParser(HTMLParser):
    """Сбор мета-тегов, ссылок и картинок с учётом тега base."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.base = None
        self.title = None
        self._in_title = False
        self.meta = {}
        self.h1 = []
        self._in_h1 = False
        self.a = []          # href ссылок
        self.img = []        # src картинок
        self.css = []        # link rel=stylesheet
        self.js = []         # script src
        self.iframe = []
        self._cur_img = None
        self._img_srcset = []

    def resolve(self, url):
        if not url:
            return None
        base = self.base or ""
        return urljoin(base, url.strip()) if base else url.strip()

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "base" and self.base is None:
            self.base = d.get("href")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = d.get("name", "").lower() or d.get("property", "").lower()
            if key and d.get("content") is not None:
                self.meta.setdefault(key, d["content"])
        elif tag == "h1":
            self._in_h1 = True
        elif tag == "a":
            u = self.resolve(d.get("href"))
            if u:
                self.a.append(u)
        elif tag == "img":
            self._cur_img = self.resolve(d.get("src"))
            if self._cur_img:
                self.img.append(self._cur_img)
            if d.get("srcset"):
                self._img_srcset = [s.strip().split(" ")[0] for s in d["srcset"].split(",")]
                for s in self._img_srcset:
                    r = self.resolve(s)
                    if r:
                        self.img.append(r)
        elif tag == "link":
            rel = d.get("rel", "").lower()
            if rel in ("stylesheet", "icon", "shortcut icon", "canonical", "alternate"):
                u = self.resolve(d.get("href"))
                if u:
                    if rel == "stylesheet":
                        self.css.append(u)
                    elif rel == "canonical":
                        self.meta.setdefault("canonical", u)
                    elif rel in ("icon", "shortcut icon"):
                        self.img.append(u)
        elif tag == "script" and d.get("src"):
            u = self.resolve(d.get("src"))
            if u:
                self.js.append(u)
        elif tag == "iframe" and d.get("src"):
            u = self.resolve(d.get("src"))
            if u:
                self.iframe.append(u)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False

    def handle_data(self, data):
        if self._in_title and self.title is None:
            self.title = data.strip()
        elif self._in_h1:
            t = data.strip()
            if t:
                self.h1.append(t)


def fetch(url, redirects=None):
    """GET без автоперехода: возвращает (код, тело, заголовки, location)."""
    redirects = redirects or []
    req = urlreq.Request(url, headers={"User-Agent": UA})
    try:
        with urlreq.urlopen(req, timeout=30) as r:
            return r.status, r.read(), dict(r.headers), None
    except urlreq.HTTPError as e:
        loc = e.headers.get("Location")
        return e.code, e.read() or b"", dict(e.headers), loc


def fetch_follow(url):
    """Ручное следование за редиректами с записью цепочки."""
    chain = []
    cur = url
    for _ in range(6):
        code, body, headers, loc = fetch(cur)
        if code in (301, 302, 303, 307, 308) and loc:
            chain.append({"code": code, "to": loc})
            cur = urljoin(cur, loc)
            time.sleep(0.2)
            continue
        return code, body, chain
    return code, body, chain


def decode(body):
    for enc in ("utf-8", "cp1251"):
        try:
            return body.decode(enc)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="replace")


def safe_name(path):
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", path.strip("/")) or "root"


def main():
    urls = [l.strip() for l in (BASE / "sitemap" / "main-urls.txt")
            .read_text(encoding="utf-8").splitlines() if l.strip()]
    out_dir = BASE / "html"
    out_dir.mkdir(exist_ok=True)
    crawl_dir = BASE / "crawl"
    crawl_dir.mkdir(exist_ok=True)

    pages = {}
    if (crawl_dir / "pages.json").exists():
        pages = json.loads((crawl_dir / "pages.json").read_text(encoding="utf-8"))
        print(f"продолжение: уже собрано {len(pages)}")

    for i, url in enumerate(urls, 1):
        if url in pages:
            continue
        for attempt in range(3):
            code, body, chain = fetch_follow(url)
            if code in (429, 503):
                time.sleep(RETRY_WAIT)
                continue
            break
        rec = {
            "url": url,
            "status": code,
            "redirect_chain": chain,
            "bytes": len(body),
            "base": None, "title": None, "meta": {}, "h1": [],
            "links": [], "img": [], "css": [], "js": [], "iframe": [],
        }
        if code == 200 and body:
            text = decode(body)
            p = PageParser()
            try:
                p.feed(text)
                p.close()
            except Exception as e:
                print(f"  разбор: {e}")
            rec["base"] = p.base
            rec["title"] = p.title
            rec["meta"] = p.meta
            rec["h1"] = p.h1[:3]
            rec["links"] = p.a
            rec["img"] = p.img
            rec["css"] = p.css
            rec["js"] = p.js
            rec["iframe"] = p.iframe
            (out_dir / f"{safe_name(urlsplit(url).path)}.html").write_text(
                text, encoding="utf-8")
        pages[url] = rec
        if i % 25 == 0 or code != 200:
            print(f"[{i}/{len(urls)}] {code} {url}")
        (crawl_dir / "pages.json").write_text(
            json.dumps(pages, ensure_ascii=False, indent=1), encoding="utf-8")
        time.sleep(DELAY)

    codes = {}
    for r in pages.values():
        codes[r["status"]] = codes.get(r["status"], 0) + 1
    print("коды ответов:", codes)
    print(f"итого страниц: {len(pages)}")


if __name__ == "__main__":
    main()
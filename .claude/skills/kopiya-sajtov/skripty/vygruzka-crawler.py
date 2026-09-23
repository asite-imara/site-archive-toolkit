# -*- coding: utf-8 -*-
"""
Архивная выгрузка сайта (продукт 1, скилл kopiya-sajtov).
BFS волнами, классификация по Content-Type, temp с хэш-именами,
коллизии путей, повторы с бэкоффом, mapping + failures.
Запуск: python vygruzka-crawler.py https://адрес-сайта/
Папка архива: ./site-backup-<домен>-html (переопределяется -o),
temp: ./TMP/arhiv-<домен>-tmp.
Первый экземпляр скрипта отработал catalog.prom-opora.ru (192 страницы,
6925 файлов); при переносе на другой сайт править нечего — только аргументы.
"""
import hashlib
import json
import os
import posixpath
import re
import shutil
import sys
import time
import html as htmllib
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# ---------- конфигурация (аргументы командной строки) ----------
import argparse

_p = argparse.ArgumentParser(description="Архивная выгрузка сайта (скилл kopiya-sajtov, продукт 1)")
_p.add_argument("site", help="адрес сайта, например https://example.ru")
_p.add_argument("-o", "--out", default=None,
                help="папка архива (по умолчанию ./site-backup-<домен>-html)")
_p.add_argument("--tmp", default=None,
                help="temp-папка (по умолчанию ./TMP/arhiv-<домен>-tmp)")
_a = _p.parse_args()

SITE = _a.site if _a.site.endswith("/") else _a.site + "/"
HOST = urllib.parse.urlparse(SITE).netloc
if not HOST:
    raise SystemExit("Не удалось определить домен из адреса: %s" % _a.site)
PROJ = os.getcwd()
FINAL_DIR = _a.out or os.path.join(PROJ, "site-backup-%s-html" % HOST)
TMP_DIR = _a.tmp or os.path.join(PROJ, "TMP", "arhiv-%s-tmp" % HOST)
STATE_PATH = os.path.join(TMP_DIR, "state.json")
MAP_PATH = os.path.join(TMP_DIR, "mapping.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

BATCH = 48            # размер волны
WORKERS = 5           # параллельные запросы
PAUSE = 1.5           # пауза между волнами, сек
MAX_PAGES = 6000
MAX_RES = 10000
MAX_FILE = 60 * 1024 * 1024
TIMEOUT = 30
RETRY_STATUSES = {429, 502, 503, 504}
RETRY_DELAYS = (5, 15, 30)

SKIP_PATH_PARTS = ("/wp-admin", "/wp-login", "/wp-json", "/feed", "/comment-page-",
                   "/author/", "/tag/", "/xmlrpc.php", "/blackhole/")
SKIP_QUERY_KEYS = {"add-to-cart", "add_to_wishlist", "remove_item", "wc-ajax",
                   "quantity", "orderby", "filter", "s", "subscribe"}
KEEP_QUERY_KEYS = {"paged", "page"}

# ---------- канонический ключ ----------
def canon(url: str):
    """Ключ: срез схемы/www/слеша (кроме корня), распаковка path, query сохраняется."""
    p = urllib.parse.urlsplit(url)
    host = (p.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = urllib.parse.unquote(p.path)
    if path and path != "/" and path.endswith("/"):
        path = path[:-1]
    return (host, path, p.query)

def canon_str(key):
    return "%s|%s|%s" % key

def key_parts(key: str):
    """Обратное превращение canon_str -> (host, path, query)."""
    host, rest = key.split("|", 1)
    path, query = rest.rsplit("|", 1)
    return (host, path, query)

def temp_name(key: str, ext: str):
    """Имя temp-файла по хэшу ключа — длинные percent-адреса не рвут лимит пути."""
    return "t_%s.%s" % (hashlib.md5(key.encode("utf-8")).hexdigest()[:16], ext)

def is_internal(url: str):
    p = urllib.parse.urlsplit(url)
    host = (p.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host == HOST

def scheme_ok(url: str):
    s = url.split(":", 1)[0].lower() if ":" in url.split("/", 2)[0] else ""
    return s not in ("mailto", "tel", "javascript", "data", "ftp", "skype", "viber", "whatsapp")

# ---------- нормализация URL ----------
def normalize(raw: str, base_url: str):
    """Разворачивает адрес от base, чистит фрагмент, фильтрует мусор.
    Возвращает (url, skip_reason) или (None, reason)."""
    raw = raw.strip()
    if not raw:
        return None, "empty"
    if raw.startswith("#"):
        return None, "fragment"
    if raw.startswith("data:"):
        return None, "data-uri"
    url = urllib.parse.urljoin(base_url, raw)
    url = urllib.parse.urldefrag(url)[0]
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https"):
        return None, "scheme"
    # мусорные адреса с пробелами/сущностями после распаковки — дефект источника
    unq = urllib.parse.unquote(p.path)
    if " " in unq or "&" in unq:
        return None, "dirty-path"
    if " " in p.query:
        return None, "dirty-query"
    return url, None

def filter_url(url: str):
    """Границы обхода: движковые и корзинные адреса не в очередь.
    Возвращает skip_reason или None."""
    p = urllib.parse.urlsplit(url)
    path = urllib.parse.unquote(p.path)
    for part in SKIP_PATH_PARTS:
        if part in path:
            return "engine-path"
    if p.query:
        keys = []
        for kv in p.query.split("&"):
            keys.append(kv.split("=", 1)[0].lower())
        if keys and all(k in SKIP_QUERY_KEYS for k in keys):
            return "skip-query"
        keep = [k for k in keys if k in KEEP_QUERY_KEYS]
        if len(keep) != len(keys):
            return "skip-query"
    return None

# ---------- загрузка ----------
def fetch(url: str):
    """Возвращает (status, content_type, body, final_url). Поворы с бэкоффом."""
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "*/*",
                                               "Accept-Language": "ru,en;q=0.9"})
    last = None
    for attempt, delay in enumerate((0,) + RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read(MAX_FILE + 1)
                ct = resp.headers.get("Content-Type", "") or ""
                if len(body) > MAX_FILE:
                    return 0, ct, b"", resp.geturl(), "too-big"
                return resp.status, ct, body, resp.geturl(), None
        except urllib.error.HTTPError as e:
            last = (e.code, "", b"", url, "http-%d" % e.code)
            if e.code in RETRY_STATUSES:
                continue
            return last
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = (0, "", b"", url, "net-" + type(e).__name__)
            continue
    return last

# ---------- классификация по Content-Type ----------
def classify(ct: str, url: str):
    ct = (ct or "").split(";")[0].strip().lower()
    if "html" in ct:
        return "page"
    if "css" in ct:
        return "css"
    if ct.endswith("+xml") or ct in ("application/xml", "text/xml", "application/rss+xml"):
        return "xml"
    return "resource"

# ---------- извлечение ссылок ----------
ATTR_URL = re.compile(
    r'\b(href|src|poster|data-src|data-lazy-src|data-original)\s*=\s*"([^"]*)"|'
    r"\b(href|src|poster|data-src|data-lazy-src|data-original)\s*=\s*'([^']*)'", re.I)
ATTR_SRCSET = re.compile(
    r'\b(srcset|data-srcset|imagesrcset)\s*=\s*"([^"]*)"|'
    r"\b(srcset|data-srcset|imagesrcset)\s*=\s*'([^']*)'", re.I)
CSS_URL = re.compile(r'url\(\s*([\'"]?)([^\'")]+)\1\s*\)', re.I)
CSS_IMPORT = re.compile(r'@import\s+(?:url\(\s*)?([\'"])([^\'"]+)\1', re.I)
STYLE_ATTR = re.compile(r'\bstyle\s*=\s*"([^"]*)"|\'\bstyle\s*=\s*\'([^\']*)\'', re.I)
BASE_TAG = re.compile(r"<base\b[^>]*>", re.I)

def decode_body(body: bytes, ct: str, is_markup: bool):
    """Декодировка по charset из Content-Type, потом meta charset, иначе utf-8/cp1251."""
    m = re.search(r"charset=([\w\-]+)", (ct or ""), re.I)
    enc = m.group(1) if m else None
    if not enc and is_markup:
        head = body[:4096]
        m2 = re.search(rb'charset\s*=\s*["\']?([\w\-]+)', head, re.I)
        if m2:
            enc = m2.group(1).decode("ascii", "ignore")
    for cand in ([enc] if enc else []) + ["utf-8", "cp1251"]:
        try:
            return body.decode(cand), cand
        except (UnicodeDecodeError, LookupError):
            continue
    return body.decode("utf-8", "replace"), "utf-8"

def split_srcset(value: str):
    """srcset → [(url, полный_элемент)]. Возвращает парсы по запятым вне скобок."""
    items = []
    buf = ""
    for ch in value:
        buf += ch
        if ch == ",":
            items.append(buf.strip())
            buf = ""
    if buf.strip():
        items.append(buf.strip())
    out = []
    for it in items:
        parts = it.split()
        if parts:
            out.append((parts[0], it))
    return out

# ---------- состояние ----------
class State:
    def __init__(self):
        self.pages = {}      # canon_str -> {"url": fetch_url, "temp": name, "base": bool,
                             #                 "enc": enc, "ct": ct, "status": code,
                             #                 "final_url": u, "type": "page"}
        self.resources = {}  # canon_str -> {..., "type": "css|resource|xml"}
        self.failures = {}   # canon_str -> {"url": u, "reason": r}
        self.seen = set()    # canon_str обработанных или в очереди
        self.queue = []      # [(url, parent_type)]
        self.skipped = {}    # canon_str -> {"url": u, "reason": r}
        self.external = {}   # canon_str -> url (внешние адреса, упомянутые в разметке)
        self.base_pages = set()  # canon_str страниц, где найден base-тег

    def enq(self, url, kind_hint=""):
        url = urllib.parse.urldefrag(url)[0]
        key = canon_str(canon(url))
        if key in self.seen:
            return
        p = urllib.parse.urlsplit(url)
        host = (p.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if host != HOST:
            if host:
                self.external[key] = url
                self.seen.add(key)
            return  # относительный адрес без хоста сюда не дойдёт
        self.seen.add(key)
        skip = filter_url(url)
        if skip:
            self.skipped[key] = {"url": url, "reason": skip}
            return
        pages = len(self.pages)
        res = len(self.resources)
        if kind_hint == "page" and pages >= MAX_PAGES:
            self.skipped[key] = {"url": url, "reason": "limit-pages"}
            return
        if res + pages >= MAX_RES + MAX_PAGES:
            self.skipped[key] = {"url": url, "reason": "limit-total"}
            return
        self.queue.append(url)

    def log(self, msg):
        print(msg, flush=True)

# ---------- обработка одного URL ----------
def process(url: str, st: State):
    status, ct, body, furl, err = fetch(url)
    key = canon_str(canon(url))
    if err or not body:
        st.failures[key] = {"url": url, "reason": err or "empty-body", "status": status}
        return
    # редирект: ключ финального адреса — основной, исходный — алиас
    fkey = canon_str(canon(furl))
    if fkey != key:
        st.skipped.setdefault(key, {"url": url, "reason": "redirect-to:" + fkey})
        if fkey in st.seen:
            return
        key = fkey
        url = furl
        st.seen.add(key)
    kind = classify(ct, url)
    if kind == "page":
        text, enc = decode_body(body, ct, True)
        m = BASE_TAG.search(text)
        base_url = url
        if m:
            base_href = re.search(r'href\s*=\s*("([^"]*)"|\'([^\']*)\')', m.group(0), re.I)
            if base_href:
                bh = base_href.group(2) if base_href.group(2) is not None else base_href.group(3)
                bh = htmllib.unescape(bh).strip()
                if bh:
                    b = urllib.parse.urljoin(url, bh)
                    if is_internal(b) or not urllib.parse.urlsplit(b).netloc:
                        base_url = b
                        st.base_pages.add(key)
        st.pages[key] = {"url": url, "base": base_url, "enc": enc, "ct": ct,
                         "status": status, "final_url": furl, "has_base": base_url != url}
        st.seen.add(key)
        # ссылки из разметки
        page_base = base_url
        for mm in ATTR_URL.finditer(text):
            val = mm.group(2) if mm.group(2) is not None else mm.group(4)
            for u, skip in iter_norm(val, page_base):
                if u:
                    st.enq(u, "page")
                elif skip == "dirty-path" or skip == "dirty-query":
                    st.skipped.setdefault(canon_str(canon(
                        urllib.parse.urljoin(page_base, val.strip()))),
                        {"url": val.strip(), "reason": skip})
        for mm in ATTR_SRCSET.finditer(text):
            val = mm.group(2) if mm.group(2) is not None else mm.group(4)
            for u, skip in iter_norm(val, page_base, srcset=True):
                if u:
                    st.enq(u, "res")
        for mm in re.finditer(r'\bstyle\s*=\s*"([^"]*)"', text, re.I):
            for u, skip in iter_norm_url_css(htmllib.unescape(mm.group(1)), page_base):
                if u:
                    st.enq(u, "res")
        for mm in re.finditer(r"<style\b[^>]*>(.*?)</style>", text, re.I | re.S):
            for u, skip in iter_norm_url_css(mm.group(1), page_base):
                if u:
                    st.enq(u, "res")
        with open(os.path.join(TMP_DIR, temp_name(key, "html")),
                  "w", encoding=enc, errors="replace", newline="") as f:
            f.write(text)
    elif kind in ("css", "xml", "resource"):
        d = {"url": url, "ct": ct, "status": status, "type": kind}
        if kind == "css":
            text, enc = decode_body(body, ct, False)
            d["enc"] = enc
            for mm in CSS_URL.finditer(text):
                for u, skip in iter_norm_url_css_entry(mm.group(2), url):
                    if u:
                        st.enq(u, "res")
            for mm in CSS_IMPORT.finditer(text):
                for u, skip in iter_norm_url_css_entry(mm.group(2), url):
                    if u:
                        st.enq(u, "res")
            with open(os.path.join(TMP_DIR, temp_name(key, "css")),
                      "w", encoding=enc, errors="replace", newline="") as f:
                f.write(text)
        elif kind == "xml":
            text = body.decode("utf-8", "replace")
            for mm in re.finditer(r"<loc>\s*([^<\s]+)\s*</loc>", text, re.I):
                st.enq(htmllib.unescape(mm.group(1)), "page")
            with open(os.path.join(TMP_DIR, temp_name(key, "xml")),
                      "w", encoding="utf-8", newline="") as f:
                f.write(text)
        else:
            with open(os.path.join(TMP_DIR, temp_name(key, "bin")), "wb") as f:
                f.write(body)
        st.resources[key] = d
        st.seen.add(key)

def iter_norm(val, base_url, srcset=False):
    """Генератор (url, skip) по значению атрибута (srcset — по элементам списка)."""
    val = htmllib.unescape(val or "")
    if srcset:
        for u0, _ in split_srcset(val):
            u, skip = normalize(u0, base_url)
            yield (u if (u and is_internal(u)) else None), (skip or ("external" if u and not is_internal(u) else skip))
    else:
        u, skip = normalize(val, base_url)
        if u and not is_internal(u):
            yield None, "external"
        else:
            yield u, skip

def iter_norm_url_css(val, base_url):
    """url() внутри inline-style / <style>."""
    for mm in CSS_URL.finditer(val):
        u, skip = normalize(mm.group(2), base_url)
        if u and not is_internal(u):
            yield None, "external"
        else:
            yield u, skip

def iter_norm_url_css_entry(val, base_url):
    u, skip = normalize(val.strip(), base_url)
    if u and not is_internal(u):
        yield None, "external"
    else:
        yield u, skip

EXT_BY_CT = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
    "image/webp": ".webp", "image/svg+xml": ".svg", "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico", "image/avif": ".avif",
    "font/woff": ".woff", "font/woff2": ".woff2", "font/ttf": ".ttf",
    "application/font-woff": ".woff", "application/x-font-ttf": ".ttf",
    "font/otf": ".otf", "application/vnd.ms-fontobject": ".eot",
    "application/json": ".json", "application/pdf": ".pdf",
    "text/plain": ".txt", "application/javascript": ".js",
    "text/javascript": ".js", "application/x-javascript": ".js",
}

def guess_ext(url, ct):
    p = urllib.parse.urlsplit(url)
    path = urllib.parse.unquote(p.path)
    ext = os.path.splitext(path)[1].lower()
    if ext and len(ext) <= 6:
        return ext
    ct = (ct or "").split(";")[0].strip().lower()
    return EXT_BY_CT.get(ct, ".bin")

# ---------- финальные пути ----------
BAD_CHARS = '<>:"|?*'
def sanitize(rel: str):
    for ch in BAD_CHARS:
        rel = rel.replace(ch, "-")
    return rel

def final_path(key_tuple, kind):
    host, path, query = key_tuple
    if path == "" or path == "/":
        path = "/"
    if kind == "page" or kind == "xml":
        if query:
            qhash = hashlib.md5(query.encode("utf-8")).hexdigest()[:8]
            d = path.strip("/")
            name = "index-%s.html" % qhash
            if not d:
                return name
            return urllib.parse.unquote(d) + "/" + name
        if path == "/":
            return "index.html"
        if path.endswith("/"):
            return urllib.parse.unquote(path).strip("/") + "/index.html"
        last = path.rsplit("/", 1)[-1]
        if "." in last and not path.endswith("/"):
            return urllib.parse.unquote(path).strip("/")
        return urllib.parse.unquote(path).strip("/") + "/index.html"
    # ресурс
    ppath = path
    name = urllib.parse.unquote(ppath).strip("/")
    if name == "":
        qhash = hashlib.md5((query or "root").encode("utf-8")).hexdigest()[:8]
        return "u-root-%s.bin" % qhash
    if query:
        qhash = hashlib.md5(query.encode("utf-8")).hexdigest()[:8]
        root, ext = os.path.splitext(name)
        name = root + "-" + qhash + ext
    return sanitize(name)

# ---------- главная ----------
def main():
    os.makedirs(TMP_DIR, exist_ok=True)
    st = State()
    st.log("== старт выгрузки %s ==" % SITE)
    st.enq(SITE + "/", "page")
    # служебные адреса
    st.enq(SITE + "/robots.txt", "res")
    st.enq(SITE + "/favicon.ico", "res")
    st.enq(SITE + "/sitemap_index.xml", "xml")
    st.enq(SITE + "/wp-sitemap.xml", "xml")

    waves = 0
    while st.queue and waves < 100000:
        batch = st.queue[:BATCH]
        st.queue = st.queue[BATCH:]
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            list(ex.map(lambda u: process(u, st), batch))
        waves += 1
        st.log("волна %d: пакет %d | страниц %d | ресурсов %d | ошибок %d | очередь %d"
               % (waves, len(batch), len(st.pages), len(st.resources),
                  len(st.failures), len(st.queue)))
        # периодическое сохранение состояния
        if waves % 20 == 0:
            save_state(st)
        time.sleep(PAUSE)
    save_state(st)
    st.log("== обход завершён: страниц %d, ресурсов %d, ошибок %d, пропущено %d, внешних %d =="
           % (len(st.pages), len(st.resources), len(st.failures),
              len(st.skipped), len(st.external)))
    finalize(st)

def save_state(st):
    data = {"pages": {k: {kk: vv for kk, vv in v.items() if kk != "url" or True}
                      for k, v in st.pages.items()},
            "resources": st.resources, "failures": st.failures,
            "skipped": st.skipped, "external": st.external,
            "base_pages": sorted(st.base_pages),
            "queue": st.queue, "seen": sorted(st.seen)}
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

# ---------- перенос в финальные пути и перезапись ----------
def finalize(st: State):
    st.log("== финализация: назначение путей ==")
    if os.path.exists(FINAL_DIR):
        st.log("Финальная папка %s уже существует — перенос пропускаю,"
               " только mapping." % FINAL_DIR)
    else:
        os.makedirs(FINAL_DIR, exist_ok=True)
    occupied = {}
    key2final = {}
    collisions = 0
    for key, d in st.pages.items():
        fp = final_path(key_parts(key), "page")
        if fp in occupied:
            fp = fp.replace(".html", "-%s.html" % hashlib.md5(key.encode("utf-8")).hexdigest()[:8])
            collisions += 1
        occupied[fp] = key
        key2final[key] = fp
    for key, d in st.resources.items():
        fp = final_path(key_parts(key), d.get("type", "resource"))
        if fp in occupied:
            root, ext = os.path.splitext(fp)
            fp = root + "-%s%s" % (hashlib.md5(key.encode("utf-8")).hexdigest()[:8], ext)
            collisions += 1
        occupied[fp] = key
        key2final[key] = fp
    st.log("коллизий путей: %d" % collisions)

    if os.path.exists(FINAL_DIR):
        st.log("Файлы уже разложены (повторный прогон) — перезапись разметки только для новых.")
    # копирование файлов
    copied = 0
    for key, fp in key2final.items():
        dst = os.path.join(FINAL_DIR, fp.replace("/", os.sep))
        if os.path.exists(dst):
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        src = os.path.join(TMP_DIR, temp_name(
            key,
            "html" if key in st.pages else
            ("css" if st.resources.get(key, {}).get("type") == "css" else
             ("xml" if st.resources.get(key, {}).get("type") == "xml" else "bin"))))
        if os.path.exists(src):
            shutil.copyfile(src, dst)
            copied += 1
        else:
            st.failures[key] = {"url": st.pages.get(key, st.resources.get(key, {})).get("url", "?"),
                                "reason": "no-temp-file"}
    st.log("скопировано файлов: %d" % copied)

    # перезапись ссылок в html и css
    st.log("== перезапись ссылок на относительные ==")
    broken_local = []
    rewritten = 0
    for key, d in st.pages.items():
        fp = key2final[key]
        dst = os.path.join(FINAL_DIR, fp.replace("/", os.sep))
        src = os.path.join(TMP_DIR, temp_name(key, "html"))
        if not os.path.exists(src):
            continue
        text, _ = decode_body(open(src, "rb").read(), d.get("ct", ""), True)
        newtext, n = rewrite_html(text, d, key2final, fp)
        rewritten += n
        enc = d.get("enc", "utf-8")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding=enc, errors="replace", newline="") as f:
            f.write(newtext)
    for key, d in st.resources.items():
        if d.get("type") != "css":
            continue
        fp = key2final[key]
        dst = os.path.join(FINAL_DIR, fp.replace("/", os.sep))
        src = os.path.join(TMP_DIR, temp_name(key, "css"))
        if not os.path.exists(src):
            continue
        text, _ = decode_body(open(src, "rb").read(), d.get("ct", ""), False)
        newtext, n = rewrite_css(text, d["url"], key2final, fp)
        rewritten += n
        enc = d.get("enc", "utf-8")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding=enc, errors="replace", newline="") as f:
            f.write(newtext)
    st.log("перезаписано ссылок: %d" % rewritten)

    # mapping и failures
    with open(os.path.join(PROJ, "TMP", "arhiv-catalog-mapping.json"), "w", encoding="utf-8") as f:
        json.dump({"pages": st.pages, "resources": st.resources,
                   "key2final": key2final, "skipped": st.skipped,
                   "external": st.external, "failures": st.failures,
                   "base_pages": sorted(st.base_pages)},
                  f, ensure_ascii=False, indent=1)
    st.log("== mapping сохранён ==")

def rel_path(target: str, page_final: str):
    """Относительный путь от файла страницы к целевому файлу, percent-кодированный."""
    return urllib.parse.quote(
        os.path.relpath(target.replace("/", os.sep),
                        os.path.dirname(page_final.replace("/", os.sep)) or "."
                        ).replace(os.sep, "/"),
        safe="/._-")

def rewrite_html(text, page_meta, key2final, page_final):
    """Переписывает href/src/srcset/style-url на относительные пути, снимает base."""
    count = 0
    base = page_meta.get("base", page_meta["url"])
    # 1) снять base-тег целиком
    text2, nb = BASE_TAG.subn("", text)
    count += nb
    # 2) атрибуты href/src/poster/data-*
    def repl_attr(pre, raw):
        nonlocal count
        val = htmllib.unescape(raw)
        u, skip = normalize(val, base)
        if u is None or not is_internal(u):
            return None
        key = canon_str(canon(u))
        target = key2final.get(key)
        if target is None:
            return None
        rel = rel_path(target, page_final)
        count += 1
        return '%s="%s"' % (pre, rel)
    def sub_attr(m):
        out = repl_attr(m.group(1), m.group(2))
        return out if out is not None else m.group(0)
    text2 = re.sub(
        r'\b(href|src|poster|data-src|data-lazy-src|data-original)\s*=\s*"([^"]*)"',
        sub_attr, text2)
    text2 = re.sub(
        r"\b(href|src|poster|data-src|data-lazy-src|data-original)\s*=\s*'([^']*)'",
        sub_attr, text2)
    # 3) srcset
    def repl_srcset(m):
        nonlocal count
        pre, val = m.group(1), m.group(2)
        val = htmllib.unescape(val)
        out = []
        changed = False
        for u0, item in split_srcset(val):
            u, skip = normalize(u0, base)
            if u is None or not is_internal(u):
                out.append(item)
                continue
            key = canon_str(canon(u))
            target = key2final.get(key)
            if target is None:
                out.append(item)
                continue
            rel = rel_path(target, page_final)
            parts = item.split()
            desc = " " + " ".join(parts[1:]) if len(parts) > 1 else ""
            out.append(rel + desc)
            changed = True
            count += 1
        if not changed:
            return m.group(0)
        return '%s="%s"' % (pre, ", ".join(out))
    text2 = re.sub(r'\b(srcset|data-srcset|imagesrcset)\s*=\s*"([^"]*)"', repl_srcset, text2)
    text2 = re.sub(r"\b(srcset|data-srcset|imagesrcset)\s*=\s*'([^']*)'", repl_srcset, text2)
    # 4) url() в inline-style и <style>
    def repl_cssurl(m):
        quote_ch, raw = m.group(1), m.group(2)
        u, skip = normalize(raw.strip(), base)
        if u is None or not is_internal(u):
            return m.group(0)
        key = canon_str(canon(u))
        target = key2final.get(key)
        if target is None:
            return m.group(0)
        rel = rel_path(target, page_final)
        count += 1
        return "url(%s%s%s)" % (quote_ch, rel, quote_ch)
    text2 = re.sub(r'url\(\s*([\'"]?)([^\'")]+)\1\s*\)', repl_cssurl, text2)
    return text2, count

def rewrite_css(text, css_url, key2final, css_final):
    count = 0
    def repl(m):
        nonlocal count
        quote_ch, raw = m.group(1), m.group(2)
        u, skip = normalize(raw.strip(), css_url)
        if u is None or not is_internal(u):
            return m.group(0)
        key = canon_str(canon(u))
        target = key2final.get(key)
        if target is None:
            return m.group(0)
        rel = urllib.parse.quote(
            os.path.relpath(target.replace("/", os.sep),
                            os.path.dirname(css_final.replace("/", os.sep)) or "."
                            ).replace(os.sep, "/"),
            safe="/._-")
        count += 1
        return "url(%s%s%s)" % (quote_ch, rel, quote_ch)
    text = re.sub(r'url\(\s*([\'"]?)([^\'")]+)\1\s*\)', repl, text)
    def repl_imp(m):
        nonlocal count
        quote_ch, raw = m.group(1), m.group(2)
        u, skip = normalize(raw.strip(), css_url)
        if u is None or not is_internal(u):
            return m.group(0)
        key = canon_str(canon(u))
        target = key2final.get(key)
        if target is None:
            return m.group(0)
        rel = urllib.parse.quote(
            os.path.relpath(target.replace("/", os.sep),
                            os.path.dirname(css_final.replace("/", os.sep)) or "."
                            ).replace(os.sep, "/"),
            safe="/._-")
        count += 1
        return "@import %s%s%s" % (quote_ch, rel, quote_ch)
    text = re.sub(r'@import\s+(?:url\(\s*)?([\'"])([^\'"]+)\1', repl_imp, text)
    return text, count

if __name__ == "__main__":
    main()
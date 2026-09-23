# -*- coding: utf-8 -*-
"""Сборка итоговых CSV и markdown-таблицы по данным обхода и проверок ссылок.

Вход: crawl/pages.json, crawl/targets.json.
Выход:
  inventar-adresov-prom-opora-2026-09-16.csv
  bitye-ssylki-prom-opora-2026-09-16.csv
  svodka-po-tipam.md (краткая markdown-сводка)
"""
import csv
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parent
DOMAIN = "prom-opora.ru"
CSV_ENC = "utf-8-sig"   # чтобы табличный процессор верно читал
DELIM = ";"

sys.stdout.reconfigure(encoding="utf-8")

SERVICE_PATHS = {"/search", "/korzina", "/404", "/service", "/service/cart-count"}
KIND_LABEL = {
    "link": "ссылка", "img": "картинка", "css": "стиль",
    "js": "скрипт", "iframe": "iframe",
}


def norm_path(url):
    p = urlsplit(url)
    path = p.path or "/"
    return path if path != "/" else "/"


def count_flat_product_links(url, pages):
    """Сколько ссылок ведёт на иные карточки каталога (/katalog/<x>/)."""
    rec = pages.get(url)
    if not rec:
        return 0
    own = norm_path(url).rstrip("/")
    n = 0
    for a in set(rec["links"]):
        p = urlsplit(a)
        if p.netloc != DOMAIN:
            continue
        pp = p.path.rstrip("/")
        seg = pp.split("/")
        if len(seg) >= 2 and seg[1] == "katalog" and pp != own and \
                not pp.startswith(own + "/"):
            n += 1
    return n


def classify(url, children_map, canonical, flat_links=None):
    """Тип страницы по адресу, потомству в sitemap и canonical."""
    path = norm_path(url).rstrip("/")
    if path == "":
        return "Главная"
    if path in SERVICE_PATHS:
        return "Служебная"
    seg = path.split("/")
    # /katalog/... — по наличию потомков в sitemap
    if seg[1] == "katalog":
        if len(seg) == 2:
            return "Каталог (корень)"
        has_children = bool(children_map.get(path))
        if len(seg) == 3:
            return "Раздел каталога" if has_children else "Карточка товара"
        # глубина 3+: страница-группа ведёт на карточки в корне каталога
        if has_children or (flat_links or 0) >= 3:
            return "Подраздел каталога"
        return "Требует решения"
    # корневые дубли разделов каталога (opory-...)
    if canonical and canonical.rstrip("/") not in (url.rstrip("/"),):
        return "Дубль (canonical на другой адрес)"
    if path in ("/opory-metallicheskie", "/opory-ramnye",
                "/opory-svetofornye", "/oporyi-zh-d-kontaktnoj-seti"):
        return "Посадочная страница раздела"
    if path in ("/o-kompanii", "/dostavka-oplata", "/politika-konfidenczialnosti",
                "/proizvodstvo", "/portfolio",
                "/izgotovlenie-metallokonstrukczij-na-zakaz",
                "/izgotovlenie-metallokonstrukczij-na-zakaz/antidronovaya-zashhita"):
        return "Информационная"
    return "Требует решения"


def build_children_map(paths):
    m = {}
    for p in paths:
        parts = p.rstrip("/").split("/")
        for i in range(2, len(parts)):
            prefix = "/".join(parts[:i])
            m.setdefault(prefix, set()).add(p)
    return m


def main():
    pages = json.loads((BASE / "crawl" / "pages.json").read_text(encoding="utf-8"))
    targets = json.loads((BASE / "crawl" / "targets.json").read_text(encoding="utf-8"))
    sitemap = [l.strip() for l in (BASE / "sitemap" / "main-urls.txt")
               .read_text(encoding="utf-8").splitlines() if l.strip()]

    children_map = build_children_map(norm_path(u) for u in sitemap)

    # --- перечень страниц ---
    inv_rows = []
    for url in sitemap:
        rec = pages.get(url)
        if rec is None:
            print(f"нет данных по {url}")
            continue
        meta = rec["meta"]
        title = rec["title"] or ""
        descr = meta.get("description", "")
        kw = meta.get("keywords", "")
        canon = meta.get("canonical", "")
        canon_self = ""
        if canon:
            canon_self = "нет" if canon.rstrip("/") != url.rstrip("/") else "да"
        typ = classify(url, children_map, canon,
                       count_flat_product_links(url, pages))
        redir = ""
        if rec["redirect_chain"]:
            last = rec["redirect_chain"][-1]
            redir = f"{len(rec['redirect_chain'])} редирект -> {last['to']}"
        h1 = rec["h1"][0] if rec["h1"] else ""
        inv_rows.append([
            url, rec["status"], redir, "sitemap", typ,
            title, descr, kw, canon, canon_self, h1, "",
        ])

    # адреса, найденные в обходе, но не в sitemap (обход = "spider")
    spider_extra = []
    for url, t in targets.items():
        if t["kind"] == "internal" and not t["in_sitemap"]:
            spider_extra.append((url, t))

    inv_path = BASE / "inventar-adresov-prom-opora-2026-09-16.csv"
    with inv_path.open("w", encoding=CSV_ENC, newline="") as f:
        w = csv.writer(f, delimiter=DELIM)
        w.writerow(["Адрес", "Код", "Редирект", "Источник", "Тип страницы",
                    "Title", "Description", "Keywords", "Canonical",
                    "Canonical на себя", "H1", "Комментарий"])
        w.writerows(inv_rows)

    # --- битые ссылки ---
    broken = []
    for url, t in targets.items():
        status = t["status"]
        code = int(status) if isinstance(status, int) else None
        is_bad = (code is not None and code >= 400) or \
                 (isinstance(status, str) and status != "не проверяется")
        if not is_bad:
            continue
        srcs = [s for s in t["sources"]][:5]
        kind = "/".join(sorted(KIND_LABEL.get(k, k) for k in t["kinds"]))
        scope = "внутренняя" if t["kind"] in ("internal", "asset") else "внешняя"
        if code == 404:
            reason = "404 (не существует)"
        elif code and 300 <= code < 400:
            reason = "перенаправление"
        elif code and code >= 500:
            reason = "ошибка сервера"
        elif code and 400 <= code < 500:
            reason = f"клиентская ошибка {code}"
        elif isinstance(status, str) and "InvalidURL" in status:
            reason = "дефект разметки: адрес разорван внутри атрибута"
        elif isinstance(status, str) and "URLError" in status:
            reason = "ошибка соединения (требует повторной проверки)"
        else:
            reason = str(status)
        broken.append([url, status if code else "", scope, kind,
                       "; ".join(srcs), reason, ""])

    broken_path = BASE / "bitye-ssylki-prom-opora-2026-09-16.csv"
    with broken_path.open("w", encoding=CSV_ENC, newline="") as f:
        w = csv.writer(f, delimiter=DELIM)
        w.writerow(["Адрес", "Код", "Внутр/внешн", "Тип ресурса",
                    "Найдено на страницах", "Причина", "Комментарий"])
        w.writerows(broken)

    # --- markdown-сводка по типам ---
    from collections import Counter
    cnt = Counter(r[4] for r in inv_rows)
    canon_mismatch = [r for r in inv_rows if r[9] == "нет"]
    lines = [
        "# Инвентаризация адресов prom-opora.ru — сводка",
        "",
        f"Всего страниц в sitemap: {len(inv_rows)}",
        "",
        "| Тип страницы | Число |",
        "|---|---|",
    ]
    for typ, n in cnt.most_common():
        lines.append(f"| {typ} | {n} |")
    lines += [
        "",
        f"Страниц с canonical не на себя: {len(canon_mismatch)}",
        "",
        f"Адресов вне sitemap, найденных в разметке: {len(spider_extra)}",
        "",
        f"Битых ссылок: {len(broken)}",
    ]
    (BASE / "svodka-po-tipam.md").write_text("\n".join(lines) + "\n",
                                             encoding="utf-8")

    print(f"перечень: {inv_path.name} ({len(inv_rows)} строк)")
    print(f"битые: {broken_path.name} ({len(broken)} строк)")
    print("сводка: svodka-po-tipam.md")
    print("типы:", dict(cnt))


if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
"""Сборка одностраничника kirov.prom-opora.ru из архивной копии prom-opora.ru.
Запуск: python build_landing.py  (из папки _build)
Источники: ../.. = корень проекта, ../site-backup-html = архив.
Результат: ../ = папка лендинга (index.html, inc, img, upload), goals.csv, goals.md
"""
import csv, io, os, re, shutil, sys, urllib.parse
import tinycss2
from bs4 import BeautifulSoup, Comment

sys.setrecursionlimit(100000)  # битый css имеет глубокую вложенность скобок

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SRC = os.path.join(ROOT, 'site-backup-html')
DST = os.path.join(ROOT, 'kirov.prom-opora.ru')
MAIN_HOST = 'https://prom-opora.ru'
SELF_HOST = 'https://kirov.prom-opora.ru'

# Маркеры блоков CSS, относящихся к корзине/магазину/чужим страницам
DROP_MARKERS = re.compile(
    r'woocommerce|\.cart|cart_|-cart|xoo-|wacp|ms3_|ms3-|ms3Config|checkout|yith|'
    r'wpc-|sisea|antidrone|\.order|shop_table|products?\b.*\.button|iziToast',
    re.I)
CSS_DROP_CLASS_RE = re.compile(r'woocommerce|cart|checkout|yith|wpc-|xoo|sisea|antidrone|ms3|order-|payment|shipping', re.I)
# поисковая форма в шапке оформлена правилами плагина yith — их сохраняем
KEEP_SEARCH_RE = re.compile(r'yith-ajaxsearch')
URL_RE = re.compile(r'url\((["\']?)([^)"\']+)\1\)')

# --- 1. mapping.txt: file -> url_path -------------------------------------
file2url = {}
with io.open(os.path.join(SRC, 'mapping.txt'), encoding='utf-8') as f:
    for line in f:
        line = line.rstrip('\n')
        if '\t' not in line:
            continue
        url, fpath = line.split('\t', 1)
        if 'quot' in url or fpath.endswith('.html') is False:
            continue
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc not in ('prom-opora.ru', 'www.prom-opora.ru'):
            continue
        file2url[fpath] = parsed.path
# обратная проверка: каждый файл страницы должен отображаться на свой URL
def url_for(fpath):
    if fpath in file2url:
        return MAIN_HOST + file2url[fpath]
    # запасной путь: снять .html
    return MAIN_HOST + '/' + fpath[:-5]

# --- 2. чтение исходной страницы ------------------------------------------
with io.open(os.path.join(SRC, 'index.html'), encoding='utf-8', errors='replace') as f:
    raw = f.read()
# дефект источника: битое экранирование кавычек в style слайдера
# style="background-image:url("path")" -> одинарные кавычки внутри
raw = re.sub(r'style="background-image:url\("([^"]+)"\)"',
             "style=\"background-image:url('\\1')\"", raw)
soup = BeautifulSoup(raw, 'html.parser')

# --- 3. чистка head ---------------------------------------------------------
def drop(selector):
    for el in soup.select(selector):
        el.decompose()

drop('script[src*="minishop3"]')
drop('script[src*="formit"]')
drop('link[href*="izitoast"]')
# метрика основного сайта: inline-скрипт с ym([номер счётчика]
for s in soup.find_all('script'):
    if not s.get('src') and 'ym([номер счётчика]' in (s.string or ''):
        s.decompose()
# callibri: preconnect, dns-prefetch, inline-скрипт
for el in list(soup.select('link[href*="callibri"]')):
    el.decompose()
for s in list(soup.find_all('script')):
    if not s.get('src') and 'callibri' in (s.string or ''):
        s.decompose()

# мета-канонический и og/twitter адреса -> поддомен
for sel, attr in [('link[rel="canonical"]', 'href'), ('link[rel="twitter:site"]', 'href')]:
    el = soup.select_one(sel)
    if el:
        el[attr] = SELF_HOST + '/'
for el in soup.select('meta[property="og:url"], meta[property="og:image"], meta[property="twitter:image"]'):
    val = el.get('content', '')
    if 'prom-opora.ru' in val:
        el['content'] = SELF_HOST + '/'
ogimg = soup.select_one('meta[property="og:image"]')
if ogimg and ogimg.get('content', '').rstrip('/') == SELF_HOST:
    ogimg['content'] = SELF_HOST + '/img/logo/logo.png'

# --- 4. чистка body: скрипты корзины и служебные inline -------------------
DROP_JS_PATTERNS = ('promOporaMetrica', 'ms3_action', 'ms3Config', 'FormIt', 'ms3_form', 'ms3', 'cart:updated')
for s in list(soup.find_all('script')):
    if s.get('src'):
        continue
    txt = s.string or ''
    if any(p in txt for p in DROP_JS_PATTERNS):
        s.decompose()
# пустой счётчик корзины в шапке
for sup in list(soup.select('.ms3-minicart-sup')):
    sup.decompose()
# пиксель Метрики (noscript)
for img in list(soup.select('img[src*="mc.yandex.ru/watch"]')):
    img.decompose()
for el in soup.find_all(attrs={'data-formit-success-message': True}):
    del el.attrs['data-formit-success-message']
for el in soup.find_all(attrs={'data-formit-validation-error-message': True}):
    del el.attrs['data-formit-validation-error-message']

# --- 5. формы: обработчик, honeypot, цель ---------------------------------
for form in soup.find_all('form'):
    if form.get('id') == 'yith-ajaxsearchform':
        form['action'] = MAIN_HOST + '/search'
        form['method'] = 'get'
        continue
    form['action'] = 'form-handler.php'
    form['method'] = 'post'
    form['data-goal'] = 'form_submit'
    # мёртвые атрибуты formit
    for k in list(form.attrs):
        if k.startswith('data-formit'):
            del form.attrs[k]
    hp = soup.new_tag('input')
    hp.attrs = {'type': 'text', 'name': 'website', 'class': 'hp-field', 'tabindex': '-1', 'autocomplete': 'off'}
    form.insert(0, hp)

# inline onclick со старым счётчиком — цели теперь ведёт скрипт по data-goal
for a in soup.find_all('a', attrs={'onclick': True}):
    if 'ym(' in a['onclick']:
        del a.attrs['onclick']
for el in soup.find_all(attrs={'data-formit-ajax-token': True}):
    del el.attrs['data-formit-ajax-token']
for el in soup.find_all(attrs={'data-formit-error': True}):
    del el.attrs['data-formit-error']

# --- 6. переписывание ссылок + цели ---------------------------------------
GOAL_EXTRA = {
    'tel:': 'go_tel',
    'mailto:': 'go_email',
    'https://wa.me/': 'go_whatsapp',
    'https://viber.click/': 'go_viber',
    'https://t.me/': 'go_telegram',
    'https://yandex.ru/maps/': 'go_yamaps',
}
goals = {}
url2goal = {}
used_names = {}

def goal_name(url):
    """имя цели по URL страницы основного сайта; одна цель на один адрес"""
    if url in url2goal:
        return url2goal[url]
    path = urllib.parse.urlparse(url).path.strip('/')
    seg = path.split('/')[-1] if path else 'home'
    seg = re.sub(r'[^0-9a-z-]+', '-', seg.lower()).strip('-')
    if seg.endswith('.html'):
        seg = seg[:-5]
    name = 'go_' + (seg or 'home')
    if name in used_names and used_names[name] != url:
        parent = path.split('/')[-2] if '/' in path else ''
        parent = re.sub(r'[^0-9a-z-]+', '-', parent.lower()).strip('-')
        cand = 'go_%s_%s' % (parent, seg)
        if cand in used_names and used_names[cand] != url:
            i = 2
            while '%s_%d' % (cand, i) in used_names and used_names['%s_%d' % (cand, i)] != url:
                i += 1
            cand = '%s_%d' % (cand, i)
        name = cand
    used_names[name] = url
    url2goal[url] = name
    return name

def process_link(a):
    href = a.get('href')
    if not href:
        return
    # якорные и относительные якоря не трогаем
    if href.startswith('#'):
        return
    # tel/mailto/мессенджеры/карты -> цель
    for pref, goal in GOAL_EXTRA.items():
        if href.startswith(pref):
            a['data-goal'] = goal
            return
    if href.startswith('http') and 'prom-opora.ru' not in href:
        return  # внешние прочие не трогаем
    if href.startswith(('index.html#', 'index.html')):
        anchor = href[10:] if href.startswith('index.html#') else ''
        a['href'] = ('/' if not anchor else '/#' + anchor)
        return
    if re.match(r'^[a-z0-9_/.-]+\.html(#.*)?$', href, re.I):
        fpath = href.split('#')[0]
        anchor = href.split('#')[1] if '#' in href else ''
        target = url_for(fpath)
        if anchor:
            target += '#' + anchor
        a['href'] = target
        if not a.get('data-goal'):
            a['data-goal'] = goal_name(target.split('#')[0])
    # прочие относительные (upload/...) не трогаем

for a in soup.find_all('a'):
    process_link(a)

# --- 7. чистка inline <style> в head --------------------------------------
def split_rules(css):
    """разбивает css на фрагменты верхнего уровня (правила/директивы)"""
    out, buf, depth, i = [], [], 0, 0
    while i < len(css):
        ch = css[i]
        buf.append(ch)
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth <= 0:
                out.append(''.join(buf).strip())
                buf, depth = [], 0
        i += 1
    if buf and ''.join(buf).strip():
        out.append(''.join(buf).strip())
    return out

def clean_css(css, base_dir='', seen=None):
    """Разбор через tinycss2 (устойчив к битой структуре), чистка корзинных
    правил, дедупликация, отбрасывание правил с мёртвыми url()."""
    if seen is None:
        seen = set()
    stats = {'dropped': 0}

    def rule_text(rule):
        body = tinycss2.serialize(rule.content or [])
        if rule.type == 'qualified-rule':
            return tinycss2.serialize(rule.prelude) + '{' + body + '}'
        return '@' + rule.lower_at_keyword + tinycss2.serialize(rule.prelude) + '{' + body + '}'

    def rule_dead_urls(text):
        urls = [m.group(2) for m in URL_RE.finditer(text)]
        if not urls:
            return False
        return not any(os.path.exists(_resolve_css_url(u, base_dir)) for u in urls)

    def walk(rules):
        out = []
        for rule in rules:
            if rule.type == 'error' or rule.type not in ('qualified-rule', 'at-rule'):
                continue
            if rule.type == 'qualified-rule':
                sel = tinycss2.serialize(rule.prelude)
                if not KEEP_SEARCH_RE.search(sel) and (CSS_DROP_CLASS_RE.search(sel) or DROP_MARKERS.search(sel)):
                    stats['dropped'] += 1
                    continue
                text = rule_text(rule)
                if rule_dead_urls(text) or text in seen:
                    stats['dropped'] += 1
                    continue
                seen.add(text)
                out.append(text)
            else:
                kw = rule.lower_at_keyword
                if kw == 'media':
                    inner = tinycss2.parse_rule_list(rule.content, skip_whitespace=True, skip_comments=True)
                    sub = walk(inner)
                    if sub:
                        out.append('@media' + tinycss2.serialize(rule.prelude) + '{' + ''.join(sub) + '}')
                    else:
                        stats['dropped'] += 1
                else:
                    text = rule_text(rule)
                    if (CSS_DROP_CLASS_RE.search(text) or DROP_MARKERS.search(text)
                            or rule_dead_urls(text) or text in seen):
                        stats['dropped'] += 1
                        continue
                    seen.add(text)
                    out.append(text)
        return out

    rules = tinycss2.parse_rule_list(css, skip_whitespace=True, skip_comments=True)
    out = walk(rules)
    return ''.join(out), stats['dropped']

def _resolve_css_url(u, base_dir):
    """относительный url() из css -> путь от корня архива"""
    p = u.strip().split('?')[0]
    if p.startswith(('data:', 'http', '#')):
        return p
    return os.path.normpath(os.path.join(SRC, base_dir, p))

for style in soup.find_all('style'):
    if style.string and len(style.string) > 5000:
        cleaned, _ = clean_css(style.string, '')
        style.string = cleaned

# --- 8. сборка вспомогательного скрипта (цели + подтверждение формы) ------
LANDING_JS = """
(function () {
  var YM_ID = 'YM_COUNTER_ID'; // замени на ID счётчика Метрики при подключении
  function fire(el) {
    var goal = el.getAttribute('data-goal');
    if (!goal) return;
    try { if (typeof ym !== 'undefined') ym(YM_ID, 'reachGoal', goal); } catch (e) {}
  }
  document.addEventListener('click', function (e) {
    var el = e.target.closest ? e.target.closest('[data-goal]') : null;
    if (el) fire(el);
  }, true);
  document.querySelectorAll('form[data-goal="form_submit"]').forEach(function (f) {
    f.addEventListener('submit', function () { fire(f); });
  });
  if (/[?&]form=ok/.test(location.search)) {
    var n = document.createElement('div');
    n.className = 'landing-toast';
    n.textContent = 'Заявка отправлена. Мы свяжемся с вами в ближайшее время.';
    document.body.appendChild(n);
    history.replaceState(null, '', location.pathname);
    setTimeout(function () { n.classList.add('landing-toast-hide'); }, 6000);
    setTimeout(function () { n.remove(); }, 7000);
  }
})();
"""
js_tag = soup.new_tag('script')
js_tag.string = LANDING_JS
soup.body.append(js_tag)
toast_css = soup.new_tag('style')
toast_css.string = (".landing-toast{position:fixed;left:50%;bottom:30px;transform:translateX(-50%);"
                    "background:#9d0d0d;color:#fff;padding:14px 22px;border-radius:6px;z-index:9999;"
                    "font-size:15px;box-shadow:0 4px 20px rgba(0,0,0,.3)}"
                    ".landing-toast-hide{opacity:0;transition:opacity 1s}.hp-field{position:absolute!important;"
                    "left:-9999px!important;width:1px!important;height:1px!important;opacity:0!important}")
soup.head.append(toast_css)

# --- 9. сохранение index.html ---------------------------------------------
html_out = str(soup)
with io.open(os.path.join(DST, 'index.html'), 'w', encoding='utf-8', newline='\n') as f:
    f.write(html_out)

# --- 10. сбор ресурсов ------------------------------------------------------
def collect_local_refs(soup):
    refs = set()
    for sel, attr in [('img', 'src'), ('img', 'data-src'), ('link[href]', 'href'),
                      ('script[src]', 'src'), ('[data-bg]', 'data-bg')]:
        for el in soup.select(sel):
            v = el.get(attr)
            if v and not v.startswith(('http', '#', 'tel:', 'mailto:', 'data:')):
                refs.add(v.split('#')[0])
    return refs

refs = collect_local_refs(soup)

URL_RE = re.compile(r'url\((["\']?)([^)"\']+)\1\)')

def css_urls(css_text, base_dir):
    """локальные пути из url() -> относительные от корня архива; только существующие"""
    out = []
    for m in URL_RE.finditer(css_text):
        p = m.group(2).strip()
        if p.startswith(('data:', 'http', '#')):
            continue
        norm = _resolve_css_url(p, base_dir)
        if not os.path.exists(norm) or not norm.startswith(SRC):
            continue  # мёртвая ссылка или путь вне архива
        rel = os.path.relpath(norm, SRC).replace('\\', '/')
        out.append(rel)
    return out

css_files = [r for r in refs if r.endswith('.css')]
for cf in css_files:
    src_path = os.path.join(SRC, cf.replace('/', os.sep))
    if not os.path.exists(src_path):
        continue
    base = os.path.dirname(cf)
    css = io.open(src_path, encoding='utf-8', errors='replace').read()
    if 'custom.css' in cf:
        css, dropped = clean_css(css, base)
        print('custom.css: удалено правил:', dropped)
    if 'fa.all.min.css' in cf:
        css = '\n'.join(r for r in split_rules(css) if 'ka-f.fontawesome' not in r)
        # CDN-шрифт FontAwesome заменяем локальным (кнопки закрытия модалок, Свернуть)
        css += ('\n@font-face{font-family:FontAwesome;font-display:swap;font-weight:400 900;'
                'src:url("../webfonts/fa-solid-900.woff2") format("woff2"),'
                'url("../webfonts/fa-solid-900.ttf") format("truetype")}\n'
                '.fa-solid{font-family:"Font Awesome 6 Free";font-weight:900}\n'
                '.fa-regular{font-family:"Font Awesome 6 Free";font-weight:400}\n')
    # пути шрифтов/картинок внутри css -> в список копирования
    for url_ref in css_urls(css, base):
        refs.add(url_ref)
    dst_path = os.path.join(DST, cf.replace('/', os.sep))
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with io.open(dst_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(css)

for ref in sorted(refs):
    if ref.endswith('.css'):
        continue  # css уже записаны очищенными выше
    src_path = os.path.join(SRC, ref.replace('/', os.sep))
    dst_path = os.path.join(DST, ref.replace('/', os.sep))
    if not os.path.exists(src_path):
        print('НЕТ ИСХОДНИКА:', ref)
        continue
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    shutil.copy2(src_path, dst_path)

print('скопировано ресурсов:', len(refs))

# --- 10. перечень целей ----------------------------------------------------
goal_rows = []
for a in soup.find_all('a', attrs={'data-goal': True}):
    goal_rows.append((a['data-goal'], a['href'], a.get_text(' ', strip=True)[:60]))
seen = set(); uniq = []
for g in goal_rows:
    if g[0] not in seen:
        seen.add(g[0]); uniq.append(g)
uniq.sort()
with io.open(os.path.join(DST, '_build', 'goals.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow(['Цель (идентификатор)', 'Куда ведёт', 'Текст ссылки (пример)'])
    w.writerows(uniq)
form_goals = [('form_submit', 'form-handler.php', 'Отправка любой формы заявки')]
with io.open(os.path.join(DST, '_build', 'goals.csv'), 'a', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter=';')
    w.writerows(form_goals)

print('index.html записан:', len(html_out), 'байт')
print('уникальных целей-ссылок:', len(uniq) + 1)
print('страница-источник:', os.path.getsize(os.path.join(SRC, 'index.html')), 'байт')
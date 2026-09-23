# -*- coding: utf-8 -*-
"""Конвертация растровых картинок лендинга в webp + переписывание ссылок.
Запуск: python convert_webp.py (из папки _build).
Оригиналы (jpeg) остаются на месте неиспользуемыми — удаление не выполняется.
"""
import io, os, re, sys
from PIL import Image

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DST = os.path.join(ROOT, 'kirov.prom-opora.ru')

MAX_WIDTH = 1600        # предел по ширине, крупнее уменьшаем
QUALITY = 80
# исключения: логотипы и иконки не конвертируем
SKIP = re.compile(r'logo|favicon|apple', re.I)

HTML = os.path.join(DST, 'index.html')
CSS_DIR = os.path.join(DST, 'inc', 'css')

html = io.open(HTML, encoding='utf-8').read()

# собираем локальные растровые ссылки из index.html
refs = set()
for m in re.finditer(r'(?:src|href|data-bg|data-src)="([^"]+\.(?:jpe?g|png))"', html, re.I):
    refs.add(m.group(1))

converted, skipped, saved = [], [], 0
for ref in sorted(refs):
    if SKIP.search(ref):
        skipped.append(ref)
        continue
    src_path = os.path.join(DST, ref.replace('/', os.sep))
    if not os.path.exists(src_path):
        print('нет файла:', ref)
        continue
    webp_path = os.path.splitext(src_path)[0] + '.webp'
    try:
        im = Image.open(src_path)
        im.load()
    except Exception as e:
        print('ошибка чтения', ref, e)
        continue
    if im.width > MAX_WIDTH:
        h = round(im.height * MAX_WIDTH / im.width)
        im = im.resize((MAX_WIDTH, h), Image.LANCZOS)
    if im.mode in ('RGBA', 'P', 'LA'):
        im = im.convert('RGBA')
        im.save(webp_path, 'WEBP', quality=QUALITY, method=6)
    else:
        im.convert('RGB').save(webp_path, 'WEBP', quality=QUALITY, method=6)
    old_size = os.path.getsize(src_path)
    new_size = os.path.getsize(webp_path)
    saved += old_size - new_size
    converted.append((ref, old_size // 1024, new_size // 1024))

    # переписываем ссылки: только для этого файла
    base = os.path.splitext(ref)[0]
    for pat in (ref, base + '.jpeg', base + '.jpg'):
        html = html.replace(pat, base + '.webp')

io.open(HTML, 'w', encoding='utf-8', newline='\n').write(html)

# url() внутри скопированных css (например, фоны в slider.css)
for fname in os.listdir(CSS_DIR):
    fpath = os.path.join(CSS_DIR, fname)
    css = io.open(fpath, encoding='utf-8').read()
    changed = False
    for m in re.finditer(r'url\((["\']?)([^)"\']+)\1\)', css):
        p = m.group(2)
        if not re.search(r'\.(jpe?g)(\?.*)?$', p, re.I):
            continue
        base = p.split('?')[0]
        abs_path = os.path.normpath(os.path.join(CSS_DIR, base))
        if os.path.exists(os.path.splitext(abs_path)[0] + '.webp'):
            css = css.replace(base, base.rsplit('.', 1)[0] + '.webp')
            changed = True
    if changed:
        io.open(fpath, 'w', encoding='utf-8', newline='\n').write(css)
        print('css обновлён:', fname)

print('---')
print('конвертировано:', len(converted))
for ref, old, new in sorted(converted, key=lambda x: -(x[1] - x[2]))[:15]:
    print('%6d KB -> %5d KB  %s' % (old, new, ref))
print('пропущено (логотипы/иконки):', len(skipped))
print('экономия суммарно: %.1f МБ' % (saved / 1e6))
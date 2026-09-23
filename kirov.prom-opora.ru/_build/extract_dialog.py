# -*- coding: utf-8 -*-
"""Извлечение диалога из журнала сессии (jsonl) в markdown.
Запуск: python extract_dialog.py <журнал.jsonl> <результат.md>
Пользовательские сообщения — дословно, ответы ассистента — дословно (текст),
вызовы инструментов — в сжатом виде (имя + краткое описание).
"""
import io, json, os, re, sys

SRC_JSONL, OUT_MD = sys.argv[1], sys.argv[2]

def clip(s, n=120):
    s = re.sub(r'\s+', ' ', s).strip()
    return s[:n] + ('…' if len(s) > n else '')

out = []
for line in io.open(SRC_JSONL, encoding='utf-8'):
    try:
        d = json.loads(line)
    except Exception:
        continue
    if d.get('type') not in ('user', 'assistant') or d.get('isSidechain'):
        continue
    ts = d.get('timestamp', '')[:16].replace('T', ' ')
    msg = d.get('message', {})
    content = msg.get('content')
    blocks = [{'type': 'text', 'text': content}] if isinstance(content, str) else content or []
    for b in blocks:
        bt = b.get('type')
        if bt == 'text':
            text = (b.get('text') or '').strip()
            if not text:
                continue
            # служебные вставки интерфейса не публикуем
            if text.startswith('<local-command') or '<system-reminder' in text[:60] \
                    or 'Caveat:' in text[:60] or 'command-name' in text[:60]:
                continue
            out.append((d['type'], ts, text))
        elif bt == 'tool_use':
            name = b.get('name', '?')
            inp = b.get('input', {})
            brief = inp.get('description') or inp.get('file_path') or inp.get('pattern') \
                or inp.get('command') or inp.get('prompt') or ''
            out.append(('tool', ts, '[%s] %s' % (name, clip(str(brief), 140))))

# заголовок
sid = os.path.basename(SRC_JSONL).split('.')[0]
out.insert(0, ('meta', '', ''))
lines = ['# Диалог сессии %s' % sid[:8], '']
cur_role = None
for role, ts, text in out:
    if role == 'meta':
        continue
    if role != cur_role:
        label = {'user': 'Пользователь', 'assistant': 'Claude'}.get(role)
        if label:
            lines.append('')
            lines.append('## %s' % label + ((' — %s' % ts) if ts else ''))
            lines.append('')
            cur_role = role
        if role == 'tool':
            lines.append('')
            lines.append('## Claude (инструменты)')
            lines.append('')
            cur_role = 'tool'
    if role == 'tool':
        lines.append('- %s' % text)
    else:
        lines.append(text)
        lines.append('')

io.open(OUT_MD, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
print('записано', OUT_MD, os.path.getsize(OUT_MD), 'байт, сообщений:', len(out))
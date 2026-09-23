# Инструкция разработчику: устранение недостатков prom-opora.ru

Дата: 2026-09-17. Основание: инвентаризация адресов от 2026-09-16
(docs/reports/report-inventarizaciya-adresov-prom-opora-2026-09-16.md и
docs/reports/rekomendacii-ustranenie-nedostatkov-2026-09-16.md). Перечни в этой
инструкции — полные, работать можно прямо по документу. Дополнительная проверка
webp-двойников выполнена повторно 2026-09-17 (живой сервер, HEAD-запросы).

Сокращения страниц (используются в таблицах):
- ИЗГ — /izgotovlenie-metallokonstrukczij-na-zakaz/
- АНТИДРОН — /izgotovlenie-metallokonstrukczij-na-zakaz/antidronovaya-zashhita/
- ПОРТ — /portfolio/
- ОКОМП — /o-kompanii/
- ЖД — /oporyi-zh-d-kontaktnoj-seti/
- ДОСТ — /dostavka-oplata/
- КАТ-КРОН — /katalog/kronshteyny-opor/kronshtejnyi-odnorozhkovyie/

## Сводка работ

| Блок | Работа | Приоритет | Объём |
|---|---|---|---|
| А | Убрать тег base на стейджинг в 2 карточках | критично | 2 страницы |
| Б | Заменить jpeg на webp в разметке | критично | 85 адресов |
| В | Исключить 404-адрес из sitemap.xml и поправить ссылку на него | критично | 1 адрес |
| Г | Восстановить утраченные картинки | желательно | 10 адресов |
| Д | Отремонтировать разорванную разметку | желательно | 14 мест |
| Е | Мессенджеры: заменить Viber, проверить t.me и wa.me | заметка | 3 ссылки |

Блоки независимы, порядок любой.

---

## Блок А. Тег base на стейджинг-домен — критично

На двух карточках товара в `<head>` стоит тег, увязавший страницу со стейджингом:

```html
<base href="https://new.prom-opora.ru/" />
```

| Страница | Ссылок на new.prom-opora.ru |
|---|---|
| /katalog/rmp-14/ | 96 |
| /katalog/zf-20-4-k300-1-5/ | 102 |

Из-за base все относительные ссылки, картинки и формы этих страниц уходят на
new.prom-opora.ru. Всего 198 ссылок на стейджинг (117 уникальных адресов) —
все только с этих двух страниц. Отдельных правок ссылок не требуется: достаточно
убрать base (или заменить href на https://prom-opora.ru/), и ссылки вернутся
на рабочий домен.

Действия:
1. Найти источник тега base (текст ресурса карточки или шаблон карточки) в CMS.
2. Удалить тег base либо исправить href на рабочий домен.
3. Сбросить/перегенерировать кэш страниц, убедиться по коду живой страницы,
   что тега больше нет.

---

## Блок Б. Замена jpeg на webp в разметке — критично

Суть: сайт переведён на webp, но разметка частично осталась со старыми
jpeg-адресами. Ниже 85 адресов, у каждого на сервере есть рабочий webp-двойник
с тем же именем (проверено 2026-09-17, код 200). Замена: в разметке CMS у битого
адреса сменить расширение .jpeg/.jpg на .webp — фактическое имя файла сохраняется.

Важно: адрес встречается в нескольких атрибутах одного тега (src, srcset,
data-lazy-src). Заменять все вхождения на странице, а не только первое.
Правка в источниках CMS, не rewrite-правило на сервере.

| № | Битый jpeg-адрес | Страницы |
|---|---|---|
| 1 | `/img/icons/grid-product-card-icon-01.jpeg` | ДОСТ, ОКОМП, ЖД |
| 2 | `/img/icons/grid-product-card-icon-02.jpeg` | ДОСТ, ОКОМП, ЖД |
| 3 | `/img/icons/grid-product-card-icon-03.jpeg` | ОКОМП, ЖД |
| 4 | `/upload/catalog-kronshtein-dlya-opor-03.jpeg` | ИЗГ |
| 5 | `/upload/catalog-kronshtein-dlya-opor-04.jpeg` | ИЗГ |
| 6 | `/upload/catalog-kronshtein-dlya-opor-06.jpeg` | ИЗГ |
| 7 | `/upload/catalog-kronshtein-view-01.jpeg` | ИЗГ |
| 8 | `/upload/catalog-kronshtein-view-02.jpeg` | ИЗГ |
| 9 | `/upload/catalog-kronshtein-view-03.jpeg` | ИЗГ |
| 10 | `/upload/catalog-kronshtein-view-04.jpeg` | ИЗГ |
| 11 | `/upload/catalog-kronshtein-view-05.jpeg` | ИЗГ |
| 12 | `/upload/catalog-kronshtein-view-07.jpeg` | ИЗГ |
| 13 | `/upload/catalog-nesilovie-opory-ogkf-01.jpeg` | ИЗГ |
| 14 | `/upload/catalog-nesilovie-opory-ogkf-03.jpeg` | ИЗГ |
| 15 | `/upload/catalog-nesilovie-opory-ogkf-04.jpeg` | ИЗГ |
| 16 | `/upload/catalog-nesilovie-opory-ogkf-05.jpeg` | ИЗГ |
| 17 | `/upload/catalog-nesilovie-opory-ogkf-06.jpeg` | ИЗГ |
| 18 | `/upload/catalog-prom-opora-ramnye-opory-01.jpeg` | ИЗГ |
| 19 | `/upload/catalog-prom-opora-ramnye-opory-02.jpeg` | ИЗГ |
| 20 | `/upload/catalog-prom-opora-ramnye-opory-03.jpeg` | ИЗГ |
| 21 | `/upload/catalog-prom-opora-ramnye-opory-04.jpeg` | ИЗГ |
| 22 | `/upload/catalog-prom-opora-ramnye-opory-05.jpeg` | ИЗГ |
| 23 | `/upload/catalog-prom-opora-ramnye-opory-06.jpeg` | ИЗГ |
| 24 | `/upload/catalog-prom-opora-ramnye-opory-07.jpeg` | ИЗГ |
| 25 | `/upload/catalog-trybchatye-nesilovie-opory-otf-nf-02.jpeg` | ИЗГ |
| 26 | `/upload/catalog-trybchatye-nesilovie-opory-otf-nf-03.jpeg` | ИЗГ |
| 27 | `/upload/catalog-trybchatye-nesilovie-opory-otf-nf-04.jpeg` | ИЗГ |
| 28 | `/upload/catalog-trybchatye-nesilovie-opory-otf-nf-05.jpeg` | ИЗГ |
| 29 | `/upload/catalog-trybchatye-nesilovie-opory-otf-nf-06.jpeg` | ИЗГ |
| 30 | `/upload/catalog-trybchatye-nesilovie-opory-otf-nf-07.jpeg` | ИЗГ |
| 31 | `/upload/catalog-trybchatye-nesilovie-opory-otf-nf-08.jpeg` | ИЗГ |
| 32 | `/upload/catalog-trybchatye-nesilovie-opory-otf-nf-09.jpeg` | ИЗГ |
| 33 | `/upload/catalog-trybchatye-silovye-01.jpeg` | ИЗГ |
| 34 | `/upload/catalog-trybchatye-silovye-02.jpeg` | ИЗГ |
| 35 | `/upload/catalog-trybchatye-silovye-03.jpeg` | ИЗГ |
| 36 | `/upload/catalog-trybchatye-silovye-04.jpeg` | ИЗГ |
| 37 | `/upload/catalog-trybchatye-silovye-05.jpeg` | ИЗГ |
| 38 | `/upload/catalog-trybchatye-silovye-06.jpeg` | ИЗГ |
| 39 | `/upload/catalog/prom-opora-catalog-ogkf-nfg.jpeg` | ОКОМП |
| 40 | `/upload/catalog/prom-opora-catalog-ogs-sfg.jpeg` | ОКОМП |
| 41 | `/upload/lp/metall-type-img-bw-01.jpeg` | ИЗГ |
| 42 | `/upload/lp/metall-type-img-bw-02.jpeg` | ИЗГ |
| 43 | `/upload/lp/metall-type-img-bw-03.jpeg` | ИЗГ |
| 44 | `/upload/lp/opora-kont-seti-img-001-2.jpeg` | ЖД |
| 45 | `/upload/lp/opora-kont-seti-img-001-3.jpeg` | ЖД |
| 46 | `/upload/lp/opora-kont-seti-img-001-4.jpeg` | ЖД |
| 47 | `/upload/product-vint-svai.jpeg` | ИЗГ |
| 48 | `/upload/prom-opora-catalog-fyndament-010.jpeg` | ИЗГ |
| 49 | `/upload/prom-opora-catalog-fyndament-011.jpeg` | ИЗГ |
| 50 | `/upload/prom-opora-catalog-fyndament-012.jpeg` | ИЗГ |
| 51 | `/upload/prom-opora-catalog-fyndament-013.jpeg` | ИЗГ |
| 52 | `/upload/prom-opora-catalog-fyndament-014.jpeg` | ИЗГ |
| 53 | `/upload/prom-opora-catalog-fyndament-015.jpeg` | ИЗГ |
| 54 | `/upload/prom-opora-catalog-fyndament-04.jpeg` | ИЗГ |
| 55 | `/upload/prom-opora-catalog-fyndament-05.jpeg` | ИЗГ |
| 56 | `/upload/prom-opora-catalog-fyndament-06.jpeg` | ИЗГ |
| 57 | `/upload/prom-opora-catalog-fyndament-07.jpeg` | ИЗГ |
| 58 | `/upload/prom-opora-catalog-fyndament-08.jpeg` | ИЗГ |
| 59 | `/upload/prom-opora-catalog-fyndament-09.jpeg` | ИЗГ |
| 60 | `/upload/prom-opora-catalog-park-02-1.jpeg` | ИЗГ |
| 61 | `/upload/prom-opora-catalog-park-02-2.jpeg` | ИЗГ |
| 62 | `/upload/prom-opora-catalog-park-02-3.jpeg` | ИЗГ |
| 63 | `/upload/prom-opora-catalog-park-02-4.jpeg` | ИЗГ |
| 64 | `/upload/prom-opora-catalog-park-04-1.jpeg` | ИЗГ |
| 65 | `/upload/prom-opora-catalog-park-06-1.jpeg` | ИЗГ |
| 66 | `/upload/prom-opora-catalog-park-08-1.jpeg` | ИЗГ |
| 67 | `/upload/prom-opora-catalog-park-08-2.jpeg` | ИЗГ |
| 68 | `/upload/prom-opora-catalog-park-09-1.jpeg` | ИЗГ |
| 69 | `/upload/prom-opora-catalog-svetofor-01.jpeg` | ИЗГ |
| 70 | `/upload/prom-opora-catalog-svetofor-02.jpeg` | ИЗГ |
| 71 | `/upload/prom-opora-catalog-svetofor-03.jpeg` | ИЗГ |
| 72 | `/upload/works-03-001.jpeg` | ИЗГ |
| 73 | `/upload/works-03-002.jpeg` | ИЗГ |
| 74 | `/upload/works-03-003.jpeg` | ИЗГ |
| 75 | `/upload/works/works-01-001.jpeg` | ПОРТ |
| 76 | `/upload/works/works-01-002.jpeg` | ПОРТ |
| 77 | `/upload/works/works-01-003.jpeg` | ПОРТ |
| 78 | `/upload/works/works-01-004.jpeg` | ПОРТ |
| 79 | `/upload/works/works-02-001.jpeg` | ПОРТ |
| 80 | `/upload/works/works-02-002.jpeg` | ПОРТ |
| 81 | `/upload/works/works-04-002.jpeg` | ПОРТ |
| 82 | `/upload/works/works-04-003.jpeg` | ПОРТ |
| 83 | `/upload/works/works-04-004.jpeg` | ПОРТ |
| 84 | `/upload/works/works-05-003.jpeg` | ПОРТ |
| 85 | `/upload/works/works-07-003.jpeg` | ПОРТ |

Распределение по страницам (файл на нескольких страницах считается на каждой):
ИЗГ — 66, ПОРТ — 11,
ЖД — 6, ОКОМП — 5, ДОСТ — 2.
Один файл может встречаться на нескольких страницах (иконки grid-product-card-*):
замена делается один раз в источнике.

---

## Блок В. 404-адрес в sitemap.xml и битая ссылка на него — критично

Адрес /katalog/kronshtejn-1k1-0-5-0-5-f2-czink-xolodnyij/ включён в sitemap.xml,
на сервере отдаёт 404. Единственная страница карты с не-200.

Дополнительно: на страницу раздела КАТ-КРОН (/katalog/kronshteyny-opor/
kronshtejnyi-odnorozhkovyie/) есть ссылка на этот адрес — тоже ведёт в 404.

Действия:
1. Если карточка нужна — восстановить ресурс в CMS; адрес вернётся в карту при
   следующем обновлении sitemap.
2. Если карточка не нужна — убрать адрес из sitemap.xml и найти источник
   генерации карты, чтобы адрес не вернулся; на странице КАТ-КРОН удалить или
   заменить ссылку на него (аналоги соседних моделей 1К1-... живы).
3. 301-редирект не обязателен (страница была товаром).

---

## Блок Г. Восстановление утраченных картинок — желательно

10 адресов, где нет ни jpeg, ни webp (файлы утрачены). Материал для
восстановления — архивная копия site-backup-html; пути в архиве отличаются
от битых адресов, это учтено в таблице. Два варианта на выбор:
восстановить файл по битому адресу (тогда разметку править не надо) либо
поправить разметку на фактический существующий файл.

| № | Битый адрес | Страницы | В архиве site-backup-html |
|---|---|---|---|
| 1 | `/upload/catalog/prom-opora-catalog-parkovye-opory.jpeg` | ОКОМП | **нет** — заменить актуальной картинкой раздела |
| 2 | `/upload/catalog/prom-opora-catalog-svetofor-gran-01.jpeg` | ИЗГ | site-backup-html/upload/works/prom-opora-catalog-svetofor-gran-01.jpeg |
| 3 | `/upload/catalog/prom-opora-catalog-svetofor-gran-02.jpeg` | ИЗГ | site-backup-html/upload/works/prom-opora-catalog-svetofor-gran-02.jpeg |
| 4 | `/upload/catalog/prom-opora-catalog-svetofor-gran-03.jpeg` | ИЗГ | site-backup-html/upload/works/prom-opora-catalog-svetofor-gran-03.jpeg |
| 5 | `/upload/catalog/prom-opora-catalog-svetofor-gran-04.jpeg` | ИЗГ | site-backup-html/upload/works/prom-opora-catalog-svetofor-gran-04.jpeg |
| 6 | `/upload/catalog/prom-opora-catalog-svetofor-gran-05.jpeg` | ИЗГ | site-backup-html/upload/works/prom-opora-catalog-svetofor-gran-05.jpeg |
| 7 | `/upload/catalog/prom-opora-catalog-svetofor-gran-06.jpeg` | ИЗГ | site-backup-html/upload/works/prom-opora-catalog-svetofor-gran-06.jpeg |
| 8 | `/wp-content/uploads/catalog-prom-opora-rmg-1.jpg` | ОКОМП | site-backup-html/upload/catalog-prom-opora-rmg-1.webp |
| 9 | `/wp-content/uploads/prom-opora-catalog-omgdz-1.jpg` | ОКОМП | site-backup-html/upload/catalog/prom-opora-catalog-omgdz-1.jpeg (+ .webp) |
| 10 | `/wp-content/uploads/prom-opora-catalog-svetofor-gran.jpg` | ОКОМП | site-backup-html/upload/catalog/prom-opora-catalog-svetofor-gran.jpeg (+ .webp) |

Примечание к № 1 (parkovye-opory): файла нет и в архиве. Варианты: заменить в
разметке ОКОМП на существующую картинку парковых опор (например из живого
каталога) или подобрать новую. Остальные 9 есть в архиве — восстановить из
site-backup-html с сверкой целостности (файл открывается, размер совпадает).

---

## Блок Д. Ремонт разорванной разметки — желательно

### Д.1. Портфолио (/portfolio/) — 10 мест

Дефект: в блоке `<noscript>` у тега `<img>` не закрыта кавычка атрибута src —
после .jpg идёт пробел и следующий атрибут width:

```html
<!-- как сейчас (дефект) -->
<img decoding="async" itemprop="url contentUrl" src="/upload/works/works-02-003.jpg width="800" ...>
<!-- как должно быть -->
<img decoding="async" itemprop="url contentUrl" src="/upload/works/works-02-003.jpg" width="800" ...>
```

Затронутые файлы картинок (добавить закрывающую кавычку после .jpg):

| № | Файл |
|---|---|
| 1 | `works-02-003.jpg` |
| 2 | `works-04-001.jpg` |
| 3 | `works-04-005.jpg` |
| 4 | `works-05-001.jpg` |
| 5 | `works-05-002.jpg` |
| 6 | `works-06-001.jpg` |
| 7 | `works-06-002.jpg` |
| 8 | `works-07-001.jpg` |
| 9 | `works-07-002.jpg` |
| 10 | `works-07-004.jpg` |

Примечание: в парном `<picture>` webp-srcset корректен, браузеры грузят webp,
поэтому визуально страницы в порядке — дефект виден в сырой разметке и для
скриптов/без-JS клиентов. Ремонтируется вместе с источником ресурса в CMS.

### Д.2. Страница ИЗГ — 4 адреса

Дефект одного вида: внутри атрибута src адрес разорван переносом строки,
из него потерян фрагмент имени каталога (w в wp-content, u в uploads):

```html
<!-- как сейчас (дефект, внутри noscript) -->
<img width="800" height="800" ... src="/

                p-content/uploads/catalog-prom-opora-rmg.jpg" alt="...">
```

Рабочие файлы (проверено на сервере 2026-09-17, код 200):

| № | Разорванный адрес в разметке | Рабочий файл |
|---|---|---|
| 1 | p-content/uploads/catalog-prom-opora-rmg.jpg | /upload/catalog/catalog-prom-opora-rmg.jpg |
| 2 | p-content/uploads/catalog-prom-opora-rmp.jpg | /upload/catalog/catalog-prom-opora-rmp.jpg |
| 3 | p-content/uploads/catalog-prom-opora-rmt.jpg | /upload/catalog/catalog-prom-opora-rmt.jpg |
| 4 | wp-content/ ploads/prom-opora-catalog-ogs-sfg.jpg | /upload/catalog/prom-opora-catalog-ogs-sfg.webp |

Действие: восстановить синтаксис атрибута и указать рабочий адрес из таблицы
(пути /upload/catalog/..., не wp-content/uploads — по этому пути файлов нет).
Для № 4 рабочим файлом сразу указан webp — jpeg-версии на сервере нет.

---

## Блок Е. Мессенджеры — заметка

| Ссылка | Состояние | Действие |
|---|---|---|
| https://viber.click/7XXXXXXXXXX | 404 (проверено) | проверить актуальный номер Viber, заменить |
| https://t.me/7XXXXXXXXXX | замеру не поддалась | открыть в браузере, убедиться, что чат открывается |
| https://wa.me/7XXXXXXXXXX | замеру не поддалась | открыть в браузере, убедиться, что чат открывается |

Ссылки стоят на страницах: Главная, /404/, ДОСТ, ИЗГ, АНТИДРОН.

---

## Приёмка после правок

Скрипты инвентаризации перезапускаемые (inventarizaciya-prom-opora-2026-09-16/):
02_crawl.py и 03_check_links.py прогнать повторно, новый bitye-ssylki...csv
покажет остаток. Критерии приёмки:

- 0 битых внутренних ссылок и картинок;
- тег base только на https://prom-opora.ru/, ссылок на new.prom-opora.ru нет;
- sitemap.xml без 404-адресов;
- страницы ИЗГ, ПОРТ, ОКОМП, ЖД, ДОСТ открываются без битых картинок.

Что не входит в эту инструкцию (решение владельца): заполнение meta keywords
(рекомендация — массово не заполнять, осознанно оставить пустыми).

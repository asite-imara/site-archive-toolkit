# Отчёт: этап 1 сборки moskva.prom-opora.ru — чистая разметка

Дата: 2026-09-17. План: docs/reports/plan-moskva-kopiya-sayta-2026-09-17.md.
Скрипт: TMP/10_stage1_chistaya_razmetka.py (перезапускаемый — сборка пересоздаётся
с нуля). Журнал правок: sborka-moskva-prom-opora-2026-09-17/inventory/
zhurnal-pravok-etap-1.csv. Архив site-backup-html не изменялся.

## Что сделано

1. Рабочая копия собрана в `sborka-moskva-prom-opora-2026-09-17/site/`:
   - 458 html-страниц (из 459 в архиве; исключена техническая заглушка
     service/cart-count.html — 11 байт, URL /service/cart-count);
   - каталоги ресурсов img/ (3,7 МБ), inc/ (3,3 МБ), upload/ (24 МБ);
   - robots.txt и sitemap.xml (черновые — адреса старого домена, перерабатываются
     перед выкладкой);
   - НЕ копированы движковые каталоги: assets/ (miniShop3, formit), themes/,
     plugins/, service/.
2. Блок Б — 85 битых jpeg заменены на webp-двойники (файлы-двойники есть в
   архиве, проверено скриптом при запуске). Затронуто 5 страниц:
   ИЗГ — 201 замена, ПОРТ — 29, ЖД — 21, ОКОМП — 15, ДОСТ — 6
   (один адрес сидит в нескольких атрибутах: src, srcset, data-lazy-src).
3. Блок Г — 10 утраченных картинок заменены заглушками
   (/upload/zaglushki/img-01…img-10-800px.webp, 10 файлов скопированы из
   archive-2026-09-17_22-59-13/archive/). Затронуты 2 страницы:
   - izgotovlenie-metallokonstrukczij-na-zakaz.html — 30 замен (6 слайдов × 5
     вхождений: srcset webp × 2, img src, data-lazy-src, noscript);
   - o-kompanii.html — 4 замены (noscript: parkovye-opory, rmg-1, omgdz-1,
     svetofor-gran.jpg).
   Видимые слоты на «О компании» не тронуты (по решению владельца заглушки —
   только для его контроля).
4. Блок Д.1 — portfolio.html: закрыта незакрытая кавычка атрибута src у
   noscript-изображений — 12 мест, 10 файлов (works-05-001 и works-06-001
   встречались дважды; в инструкции числилось 10 мест — фактически 12).
5. Блок Д.2 — izgotovlenie-metallokonstrukczij-na-zakaz.html: восстановлены
   разорванные переносы адреса — 6 мест (в инструкции 4 адреса, но rmp и rmt
   встречались дважды): rmg/rmp/rmt → /upload/catalog/catalog-prom-opora-rmX.jpg,
   ogs-sfg → /upload/catalog/prom-opora-catalog-ogs-sfg.webp.
6. Приёмка (автоматическая, по всей сборке):
   - base href — 0 вхождений;
   - ни один из 95 правленых адресов (85 блока Б + 10 блока Г, включая
     webp-двойники) не остался в разметке — 0;
   - дефектные фрагменты Д.1 и Д.2 — 0.

## Выяснено попутно (для этапа 5, CSS)

- inc/css/theme-child.css подключает 5 файлов Montserrat (../fonts/…), в
  inc/fonts/ есть только 3 из 5 (нет montserrat-67146b73.woff2 и
  montserrat-0748de38.woff2) — видимо, битые и на живом сайте; проверить при
  ревизии шрифтов на этапе 5.
- В theme-child.css остаётся @font-face от WooCommerce (../../../plugins/…)
  — уйдёт при чистке движка на этапе 2/5.
- custom.css ссылается на внешние ресурсы (ka-f.fontawesome.com CDN,
  kenwheeler.github.io slick, wp-rocket youtube.png) — ревизия на этапе 5.

## Создано / изменено

- sborka-moskva-prom-opora-2026-09-17/site/ — рабочая сборка (458 страниц + ресурсы)
- sborka-moskva-prom-opora-2026-09-17/site/upload/zaglushki/ — 10 заглушек
- sborka-moskva-prom-opora-2026-09-17/inventory/zhurnal-pravok-etap-1.csv
- TMP/10_stage1_chistaya_razmetka.py
- docs/reports/report-etap-1-sborka-moskva-2026-09-17.md

## Что дальше (по плану)

- Этап 2 — устранение признаков движка (классы woocommerce-/ms3_/yith,
  пути wp-content, мета-теги). Могут выполняться поверх текущей сборки.
- Этап 3 — скрипты: удалить движковые подключения из разметки (в сборке их уже
  нет физически — assets/ не копировался), написать filter.js, cart.js,
  search.js, prices.js и PHP-обработчик заказа.
- Замечание: sitemap.xml и robots.txt в сборке — от prom-opora.ru, будут
  переработаны под moskva.prom-opora.ru ближе к выкладке (этап 7).
# Отчёт: этап 2 сборки moskva.prom-opora.ru — устранение признаков движка

Дата: 2026-09-17. План: docs/reports/plan-moskva-kopiya-sayta-2026-09-17.md.
Скрипт: TMP/21_stage2_chistka_dvizhka.py (поверх сборки этапа 1; конвейер
этап 1 → этап 2 перезапускается целиком). Инвентаризация токенов:
TMP/20_stage2_inventarizaciya_tokenov.py. Журнал: inventory/zhurnal-pravok-etap-2.csv
(7504 записи). Архив не трогался.

## Что сделано

1. Удалены из всех 458 страниц:
   - inline-скрипты движка (по 458 каждый): ms3Config, обработчик submit форм
     ms3_order_form, слушатель ms3:cart:updated, fetch service/cart-count/,
     Object.assign(FormIt…), скрипт целей promOporaMetrica, старый счётчик
     Метрики [номер счётчика] (script + noscript);
   - теги движковых файлов: 17 скриптов miniShop3 (7786 тегов-вхождений),
     formit.js, catalog-filter.js (34 раздела), стили iziToast (916);
   - атрибуты data-formit-ajax-token (2291);
   - из body class удалён токен theme-yootheme.
2. Единые переименования (согласованно в html, css, js):
   woocommerce → shop (53 426), yith → shop (30 369), ms3 → shop (7 372),
   formit → shopform (11 461, включая data-атрибуты уже удалённые и
   form.formit-loading в css), WooCommerce-шрифт → shop, qwordpress → qspinner,
   мёртвые переменные/селекторы ядра WordPress (--wp- → --wpx-, .wp- → .wpx-),
   ключ иконки wordpress → wpress в uikit-icons.min.js.
   Проверка: классы в разметке и селекторы в CSS совпадают
   (shop-Price-amount, shop_form, shop-loop-product__title,
   shop-ajaxsearchform-wide и др.).
3. Пути и адреса:
   - wp-content/uploads → /upload/ (121 замена в html, 1 в css);
   - 3 admin-ajax-адреса webp-конвертера на «Производстве» заменены на
     локальные webp (svetofor-04/05/06.webp);
   - 1833 абсолютных ссылки https://prom-opora.ru переведены на корневые
     относительные (canonical/og:url сейчас относительные — абсолютные адреса
     moskva.prom-opora.ru проставляются на этапе 7);
   - WooCommerce @font-face удалён из theme-child.css (3 блока, ссылались на
     отсутствующие шрифты plugins/woocommerce).
4. Сохранено для следующих этапов: inventory/etap-2/
   promOporaMetrica-ssylka-dlya-etapov-3-6.js — текст скрипта целей
   (lid_form_cart и др.), понадобится на этапах 3 и 6.

## Приёмка

grep по всей сборке (html, css, js): wp-, woocommerce, modx, minishop, formit,
yith, ms3, wordpress, theme-yootheme — 0 вхождений. Повторный прогон
инвентаризации токенов подтверждает 0.

## Отмечено для следующих этапов

- fa.all.min.css и slider.css подключены на некоторых страницах дважды
  (дубли тегов) — убрать на этапе 5.
- Мёртвые правила CSS от движка (shop-MyAccount-*, shop-wcbm-badge, shop_table,
  shop_message и прочие без вхождений в разметке) — вычистка на этапе 5.
- /upload/wprocket/youtube.png в custom.css — файла в сборке нет (не было и в
  архиве); правило rll-youtube-player, вероятно, не используется — ревизия
  на этапе 5.
- Скрытое поле shop_action со значением cart/add в формах — уйдёт вместе с
  переработкой форм на этапе 3.
- JSON-LD и og-разметка теперь с относительными адресами — приведение к
  абсолютным moskva.prom-opora.ru на этапе 7.

## Файлы

- sborka-moskva-prom-opora-2026-09-17/site/ — обновлённая сборка
- sborka-moskva-prom-opora-2026-09-17/inventory/zhurnal-pravok-etap-2.csv
- sborka-moskva-prom-opora-2026-09-17/inventory/etap-2/promOporaMetrica-ssylka-dlya-etapov-3-6.js
- TMP/20_stage2_inventarizaciya_tokenov.py, TMP/21_stage2_chistka_dvizhka.py
- docs/reports/report-etap-2-sborka-moskva-2026-09-17.md

## Что дальше

Этап 3 — скрипты: filter.js (клиентский фильтр из JSON-индекса характеристик),
cart.js (localStorage + оформление письмом), search.js (поиск по JSON-индексу),
prices.js + prices.json, PHP-обработчик заказа по схеме kirov.
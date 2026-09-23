# Отчёт: этап 0 сборки moskva.prom-opora.ru — подготовка и инвентаризация

Дата: 2026-09-17. План: docs/reports/plan-moskva-kopiya-sayta-2026-09-17.md.
Статус этапа: выполнен. Архив site-backup-html не изменялся (только чтение).

## Что сделано

1. Создана рабочая папка сборки `sborka-moskva-prom-opora-2026-09-17/`
   (подпапка `inventory/` — результаты инвентаризации; в последующих этапах
   рядом появится подпапка с самой сборкой сайта).
2. Скрипт инвентаризации: `TMP/00_stage0_inventarizaciya.py`
   (перезапускаемый, только чтение архива; Python stdlib).
3. Вспомогательные проверки: `TMP/00a_test_price_id.py` (извлечение id и цены),
   `TMP/00b_test_card_structure.py` (структура карточки),
   `TMP/00c_test_filter_markup.py` (разметка фильтра).

## Файлы инвентаризации (sborka-moskva-prom-opora-2026-09-17/inventory/)

| Файл | Содержимое |
|---|---|
| pages-index.csv | 459 страниц: путь, URL, тип шаблона, title, H1, description, body class, скрипты/стили/картинки, классы движка |
| scripts-po-tipam.csv | скрипты × типы страниц (сколько страниц каждого типа подключают) |
| styles-po-tipam.csv | стили × типы страниц |
| images-unikalnye.csv | 2617 уникальных ссылок на картинки, по скольким страницам и типам |
| classes-dvizhka-po-tipam.csv | 57 уникальных классов движка (woocommerce/wp/ms3/yith) по типам |
| svodka-etap-0.txt | краткая сводка |

## Карта шаблонов (459 страниц)

| Тип | Страниц | Как опознаны |
|---|---|---|
| kartochka-tovara | 411 | body class `single-product` |
| razdel-kataloga | 34 | body class `tax-product_cat` или маркер `catalog-filter` |
| info-stranica | 10 | остальное: dostavka, o-kompanii, politika, portfolio, proizvodstvo, service, izgotovlenie, oporyi-zh-d, antidronovaya-zashhita, service/cart-count |
| korzina | 1 | korzina.html |
| poisk | 1 | search.html |
| glavnaya | 1 | index.html |
| 404 | 1 | 404.html |

Итого 459, совпадает с числом страниц архива. Суммарный объём HTML: 59,7 МБ.

## Ключевые находки

- Скриптовый набор одинаков на всех страницах: uikit.min.js, uikit-icons.min.js,
  theme.js, custom.js + 21 файл движка (miniShop3 × 19, iziToast, formit.js).
  Движковые скрипты уходят на этапе 3, остаются 4.
- Стили на всех страницах: theme-child.css (496 КБ), custom.css (1,5 МБ),
  iziToast.min.css; fa.all.min.css и slider.css — на карточках, разделах и части
  инфо-страниц. Двигковый iziToast.min.css заменяется своей версией (нужен новым
  формам) либо выкидывается.
- catalog-filter.js подключён на всех 34 разделах каталога. Форма фильтра в
  разметке раздела серверная (cf-form, cf-block, cf-chip, cf-range, cf-toggle),
  варианты чекбоксов (cf[option_tu][], cf[option_full_height][],
  cf[option_top_size][] и др.) отрендерены сервером — данные для клиентского
  filter.js есть, но атрибуты товаров в карточках раздела отсутствуют
  (в li.product нет data-атрибутов). Вывод: JSON-индекс атрибутов для фильтра
  собирается на этапе 3 из таблиц характеристик карточек товаров
  (product-characteristics-table на страницах карточек), связка
  раздел → товары → id восстанавливается по перечню карточек на странице раздела.
- Извлечение цен проверено: у каждой карточки есть скрытое поле
  `<input type="hidden" name="id" value="180">` и блок цены
  `<span class="woocommerce-Price-amount amount">1837.5 <span ...>₽</span></span>`.
  prices.json (этап 4) собирается надёжно: ключ — id, значение — цена.
- Старый счётчик Метрики [номер счётчика] присутствует на 458 страницах (изображение
  watch/[номер счётчика] в noscript). На этапе 6 заменяется на [номер счётчика] (код уже в
  CLAUDE.md).
- Страница `service/cart-count.html` — техническая заглушка (11 байт,
  `{"count":0}`, без title), URL /service/cart-count: с неё читалось число
  товаров в мини-корзине. В сборку не включается; mini-корзину обслуживает cart.js.
- `service.html` — единственная содержательная страница без H1 (решить при
  этапе 1: добавить или оставить).
- base href="https://new.prom-opora.ru/" в архивных копиях не встречается
  (0 из 459) — на этапе 1 только контроль.
- Картинки wp-content: как `<img>` встречаются только на 2 инфо-страницах
  (izgotovlenie — 1, o-kompanii — 3); на остальных 122 страницах это теги
  `<video src="/wp-content/uploads/...">` и прочие упоминания в разметке.
  Замена на /upload/ (этап 2) покрывает все 124 страницы.
- Топ-картинки по вхождению: ../upload/prom-opora-catalog-ogkf-nfg.webp
  (1660 вхождений — плейсхолдер карточек), логотипы (logo.png, logo-inverse.svg,
  logo-dialog.png, logo-footer.png — 838/419), сертификаты cert-2024.jpg и
  cert-eaes.jpg (419). Всё это входит в «шапку/подвал» общего слоя CSS.

## Решения этапа

- Классификация по body class и имени файла; страницы без явного маркера —
  info-stranica. 34 раздела каталога включают 8 верхних (katalog.html +
  7 категорий) и 26 подразделов.
- Путь `izgotovlenie-metallokonstrukczij-na-zakaz/antidronovaya-zashhita.html`
  отнесён к info-stranica (содержательная страница, а не карточка товара).

## Что дальше (по плану)

- Этап 1 (чистая разметка) — ждёт проверки картинок блока Г владельцем.
- Этап 2–3 могут идти без внешних зависимостей.
- Счётчик Метрики для Москвы получен ([номер счётчика]); перечень целей JavaScript-
  событий — до этапа 6.
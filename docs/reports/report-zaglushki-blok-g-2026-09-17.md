# Отчёт: замена 10 утраченных картинок заглушками (блок Г)

Дата: 2026-09-17. Задача: сборка moskva.prom-opora.ru, этап 1.
Решение владельца: наименования файлов на сайте и в папке изображений клиента
не совпадают, точный состав недостающего выявить сложно; вместо восстановления
10 утраченных картинок на их места ставятся 10 картинок-заглушек — по заглушкам
на сайте будет видно, какие именно изображения пропали.

## Исходные данные

- Заглушки: `archive-2026-09-17_22-59-13/archive/img-01-800px.webp` …
  `img-10-800px.webp` (10 файлов, webp, 800px).
- Перечень утраченных: блок Г инструкции разработчику
  (docs/reports/instrukciya-razrabotchiku-nedostatki-prom-opora-2026-09-17.md).
- Конфигурация замен: `sborka-moskva-prom-opora-2026-09-17/zaglushki-mapping.json`
  (собрана скриптом `TMP/01c_build_zaglushki_mapping.py`, перезапускаемым).

## Где стоят утраченные адреса (проверка по разметке архива)

Утраченные адреса встречаются только на двух страницах. На странице «О компании»
они сидят в запасной разметке `<noscript>` (видимые картинки блоков — другие
файлы, они работают). На странице «Изготовление металлоконструкций на заказ»
битые адреса — это сами видимые слайды фотогалереи (6 слайдов, ни jpeg, ни webp).

## Таблица установки заглушек

Заглушки размещаются в сборке по адресу `/upload/zaglushki/<имя>.webp`
(копируются из `archive-2026-09-17_22-59-13/archive/` при сборке, этап 1).
Битый адрес и его webp-двойник в разметке заменяются на заглушку.

| № | Заглушка | Утраченный адрес | Страница | Место в разметке | Вхождений |
|---|---|---|---|---|---|
| 1 | img-01-800px.webp | /upload/catalog/prom-opora-catalog-parkovye-opory.jpeg | О компании (o-kompanii.html) | noscript img (видимая картинка блока — home-catalog-parkovye.jpeg, работает) | 1 |
| 2 | img-02-800px.webp | /upload/catalog/prom-opora-catalog-svetofor-gran-01.jpeg | Изготовление на заказ (izgotovlenie-metallokonstrukczij-na-zakaz.html) | слайд 1 галереи: source srcset webp 768w/800w + img src + data-lazy-src + noscript | 5 |
| 3 | img-03-800px.webp | /upload/catalog/prom-opora-catalog-svetofor-gran-02.jpeg | Изготовление на заказ | слайд 2 галереи, те же 5 мест | 5 |
| 4 | img-04-800px.webp | /upload/catalog/prom-opora-catalog-svetofor-gran-03.jpeg | Изготовление на заказ | слайд 3 галереи, те же 5 мест | 5 |
| 5 | img-05-800px.webp | /upload/catalog/prom-opora-catalog-svetofor-gran-04.jpeg | Изготовление на заказ | слайд 4 галереи, те же 5 мест | 5 |
| 6 | img-06-800px.webp | /upload/catalog/prom-opora-catalog-svetofor-gran-05.jpeg | Изготовление на заказ | слайд 5 галереи, те же 5 мест | 5 |
| 7 | img-07-800px.webp | /upload/catalog/prom-opora-catalog-svetofor-gran-06.jpeg | Изготовление на заказ | слайд 6 галереи, те же 5 мест | 5 |
| 8 | img-08-800px.webp | /wp-content/uploads/catalog-prom-opora-rmg-1.jpg | О компании | noscript img (видимая — catalog-prom-opora-rmg.jpg, работает) | 1 |
| 9 | img-09-800px.webp | /wp-content/uploads/prom-opora-catalog-omgdz-1.jpg | О компании | noscript img (видимая — prom-opora-catalog-omgdz-1.jpeg, работает) | 1 |
| 10 | img-10-800px.webp | /wp-content/uploads/prom-opora-catalog-svetofor-gran.jpg | О компании | noscript img (видимая — prom-opora-catalog-svetofor-gran.jpeg, работает) | 1 |

Итого: 2 страницы (o-kompanii.html, izgotovlenie-metallokonstrukczij-na-zakaz.html),
28 замен адресов в разметке (6 × 5 на «Изготовлении» + 4 × 1 на «О компании»).

## Нюанс, требующий внимания

- 6 заглушек (№ 2–7) будут видны посетителям: это видимая фотогалерея на
  «Изготовлении» — файлы отсутствуют полностью (и jpeg, и webp).
- 4 заглушки (№ 1, 8, 9, 10) на «О компании» стоят только в `<noscript>`-запасе
  и обычным посетителям не видны — видимые картинки тех же блоков работают.
  Для визуального контроля недостающих файлов со стороны клиента эти четыре
  места на страницу не «выйдут». Если задача — наглядно показать клиенту
  пропавшие картинки, можно дополнительно поставить эти 4 заглушки и в видимые
  слоты (сейчас там работающие файлы home-catalog-parkovye.jpeg,
  catalog-prom-opora-rmg.jpg, prom-opora-catalog-omgdz-1.jpeg,
  prom-opora-catalog-svetofor-gran.jpeg). Решение за владельцем; по умолчанию
  заменяются только битые адреса.

## Фактическая установка

Произойдёт на этапе 1 (перенос страниц в сборку и правка разметки) — сейчас
собрана и проверена конфигурация; в архиве и на живом сайте ничего не менялось.
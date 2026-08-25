"""Сайт вокруг виджета: реестр страниц, шаблон и разметка для поиска.

Имя файла не `site.py` намеренно: так называется модуль стандартной библиотеки,
который Python загружает ещё до нашего кода — свой `site.py` его не перебивает,
и `import site` молча отдаёт чужой модуль.

Зачем отдельный модуль. Виджет (`index.html` + `app.js`) — это ИНСТРУМЕНТ, он живёт
в `/app/` и для поиска невидим: содержимое iframe не индексируется. Ключи снимают
СТРАНИЦЫ, и это разные сущности — у страницы есть заголовок-запрос, текст и мета,
у виджета их нет вовсе.

Как разложено и почему именно так:
  · МЕТАДАННЫЕ страницы (slug, h1, title, description, родитель, параметры виджета)
    живут здесь, в коде — их пишет Клод, они выверяются по канону и меняются редко;
  · ТЕКСТ страницы живёт файлом в `pages/<имя>.html` — его пишет АВТОР руками.
    Канон Site Builders запрещает писать текст страниц ИИ прямо и дважды, поэтому
    прозы в этом файле нет и не будет: только каркас вокруг неё.
  · СВЕДЕНИЯ О ПРОЕКТЕ (название, адрес, почта, соцсети) — один словарь `PROJECT`,
    из которого разливаются подвал, «Контакты», «О проекте» и разметка Organization.
    Один факт — один дом: правка в одном месте меняет все четыре.

Черновик. У страницы есть флаг `draft`. Черновик не отдаётся публично (404), не
попадает в карту сайта и не появляется в подвале. Причина не гигиена, а индексация:
полупустая страница, единожды попавшая в индекс, тратит бюджет обхода и тянет вниз
весь сайт. Пока автор не написал текст — страница черновик.
"""

from __future__ import annotations

import html
import json
import os
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES_DIR = os.path.join(HERE, "pages")

# Адрес сайта приходит окружением, а не вшивается в код: домен куплен позже сервера,
# прод переезжает, а canonical и <loc> в карте обязаны указывать на настоящий адрес.
# Брать из заголовка Host нельзя — подставится чужой.
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8784").rstrip("/")

# ─── сведения о проекте ─────────────────────────────────────────────────────
# Канон ШАГа 4 требует в подвале ПЯТЬ элементов: название · полный адрес с индексом ·
# email на своём домене · минимум одна зарубежная соцсеть · ссылки на ключевые
# страницы. «Поисковики смотрят на футер, когда решают, сколько траста выдать».
# Заполнено 2026-08-25 решениями автора. Что здесь стоит и почему:
#
# email — канон требует ящик на СВОЁМ домене и не советует личное имя
#   (`info@` / `support@` / `hey@`). Пока стоит рабочий ящик автора на его же
#   домене `fanarlabs.com`: почта на `logozvuk.com` ещё не заведена, а пустой
#   футер стоит дороже, чем неидеальное имя ящика. Заменить на `info@logozvuk.com`,
#   когда почта появится, — правка в одну строку, она разойдётся по подвалу,
#   «Контактам», «О проекте» и разметке Organization.
#
# address — ПРОПУЩЕН СОЗНАТЕЛЬНО (решение автора 08-25). Канон просит полный
#   адрес с индексом, потому что «поисковики смотрят на футер, когда решают,
#   сколько траста выдать проекту», то есть это технический фактор, а не
#   юридическое требование: мы ничего не продаём и юрлицом не являемся. Канон
#   же советует, если своего адреса нет, взять адрес апартаментов, где бывал, —
#   мы этого не делаем: у русскоязычного сервиса подвал читают люди, а не только
#   роботы, и выдуманный адрес — это ложь ради фактора ранжирования.
#   Код к пустой строке готов: подвал и JSON-LD её просто не печатают.
#
# social — Телеграм-группа автора. Канон просит ЗАРУБЕЖНУЮ площадку (Twitter,
#   Facebook, LinkedIn), а Телеграм ставит «под звёздочкой» — но это совет под
#   зарубежный рынок, а наш рынок русскоязычный, и логопеды живут именно здесь.
#   ⚠ Хвост: группа называется «AI помощник логопеда — группа тестирования» —
#   это имя ДРУГОГО продукта автора. Для подвала Логозвука её стоит либо
#   переименовать, либо завести канал проекта.
PROJECT: Dict[str, str] = {
    "name": "Логозвук",
    "domain": "logozvuk.com",
    "email": "igor@fanarlabs.com",
    "address": "",
    "social": "https://t.me/logo_konspekt",
}

# ─── счётчики ───────────────────────────────────────────────────────────────
# Канон ШАГа 6 требует четыре аналитики: Search Console, Google Analytics,
# Яндекс.Вебмастер, Яндекс.Метрика. Две последние — про поведение, и именно они
# отвечают на вопрос автора «приходят ли новые и возвращаются ли старые».
# Вебмастер и Search Console счётчика на странице не требуют — они
# подтверждаются файлом или мета-тегом, поэтому здесь их нет.
#
# Номера приходят ОКРУЖЕНИЕМ, а не лежат в коде: счётчик — учётная запись
# автора, и в публичном репозитории ему не место. Нет переменной — нет и кода
# на странице: пустой сайт не должен грузить чужие скрипты.
#
# ⚠ Вебвизор (запись действий) намеренно НЕ включён: он пишет, что человек
# делал на странице, а для вопроса «новые или вернувшиеся» этого не нужно.
# Понадобится — включается в кабинете Метрики, без правки кода.
# Номер счётчика Метрики не секрет: он виден в коде любой страницы, где стоит.
# Поэтому он живёт прямо здесь, а не в переменной кабинета — иначе перенос сайта
# на другой хостинг тихо терял бы статистику. Переменной его всё равно можно
# перебить: удобно, когда сайт поднимают копией для проверки.
METRIKA_ID = os.environ.get("METRIKA_ID", "111927540").strip()
GA_ID = os.environ.get("GA_ID", "").strip()


def analytics(in_frame_guard: bool = False) -> str:
    """Код счётчиков. Пусто, если номера не заданы.

    `in_frame_guard` — для ВИДЖЕТА. Виджет живёт в iframe страницы сайта, и без
    этой оговорки один заход считался бы дважды: страницей и рамкой внутри неё.
    Поэтому в рамке счётчик молчит, а на прямом заходе на /app/ работает.

    ⚠ 08-25: сначала оговорка делалась через `document.write` со строкой кода —
    и в левом верхнем углу виджета вылезли символы `');}`. Причина въедливая:
    браузер обрывает `<script>` на ПЕРВОМ же `</script>`, даже если тот стоит
    внутри строки в кавычках. Поэтому теперь оборачивается сам код, а не текст
    кода, и никаких строк со скриптами внутри строк здесь больше нет.
    """
    if not (METRIKA_ID or GA_ID):
        return ""

    js: List[str] = []
    if METRIKA_ID:
        js.append(
            "(function(m,e,t,r,i,k,a){m[i]=m[i]||function(){"
            "(m[i].a=m[i].a||[]).push(arguments)};m[i].l=1*new Date();"
            "for(var j=0;j<e.scripts.length;j++){if(e.scripts[j].src===r){return;}}"
            "k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,"
            "a.parentNode.insertBefore(k,a)})"
            '(window,document,"script","https://mc.yandex.ru/metrika/tag.js","ym");'
            f'ym({METRIKA_ID},"init",{{clickmap:true,trackLinks:true,'
            "accurateTrackBounce:true});")
    if GA_ID:
        js.append(
            "window.dataLayer=window.dataLayer||[];"
            "function gtag(){dataLayer.push(arguments);}gtag('js',new Date());"
            f"gtag('config','{GA_ID}');")

    code = "".join(js)
    if in_frame_guard:
        code = "if(window.top===window.self){" + code + "}"

    out = ""
    if GA_ID:
        # Загрузчик GA — отдельным тегом; в рамке он не нужен, но и не вредит:
        # без вызова `config` ничего не отправляется.
        out += (f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}">'
                "</script>\n")
    out += "<script>" + code + "</script>\n"
    if METRIKA_ID and not in_frame_guard:
        # Картинка для тех, у кого выключен JS. В рамке она не ставится: там
        # заход уже посчитан страницей.
        out += (f'<noscript><div><img src="https://mc.yandex.ru/watch/{METRIKA_ID}" '
                'style="position:absolute;left:-9999px" alt=""></div></noscript>\n')
    return out


# ─── реестр страниц ─────────────────────────────────────────────────────────
# Карта собрана по канону ШАГов 3-4-7: главная → категории → вложенные страницы.
# Звук — КАТЕГОРИЯ, а не тег: лист бывает либо на Р, либо на Л, категории
# взаимоисключающи и отражаются в адресе, теги — нет. Тегов на старте нет вовсе,
# канон это прямо разрешает.
#
# Вторая звуковая категория (Л · Ш · С) сюда НЕ добавляется, пока нет методики:
# движок между Р, Л, Ш и С различий не даёт, а канон запрещает дублирование
# подстановкой буквы. Различие обязана нести методика звука, а не заменённая буква.

Page = Dict[str, Any]

PAGES: Tuple[Page, ...] = (
    {
        "slug": "",
        "file": "glavnaya.html",
        "h1": "Автоматизация звука",
        "title": "Автоматизация звука — печатный материал под ребёнка | Логозвук",
        "description": "Соберите лист на автоматизацию звука под конкретного ребёнка: "
                       "слова с ещё не поставленными звуками уходят сами. "
                       "Печать сразу, без установки.",
        "parent": None,
        "widget": "?embed=1",
        "draft": False,
    },
    {
        "slug": "avtomatizaciya-zvuka-r",
        "file": "zvuk-r.html",
        "h1": "Автоматизация звука Р",
        "title": "Автоматизация звука Р у ребёнка — Логозвук",
        "description": "Автоматизация звука Р: отметьте, каких звуков у ребёнка ещё нет, "
                       "и получите чистый речевой материал на лист. "
                       "Готово за минуту, печатать сразу.",
        "parent": None,
        "widget": "?sound=r&material=list&embed=1",
        "draft": False,
    },
    {
        "slug": "avtomatizaciya-zvuka-r/doma",
        "file": "zvuk-r-doma.html",
        "h1": "Домашнее задание логопеда на звук Р",
        "title": "Домашнее задание логопеда на звук Р — Логозвук",
        "description": "Домашнее задание на звук Р: тот же лист, но с подсказками для "
                       "родителя — что показать и в каком порядке вести ребёнка.",
        "parent": "avtomatizaciya-zvuka-r",
        "widget": "?sound=r&material=list&audience=doma&embed=1",
        "draft": True,
    },
    {
        "slug": "profil-rebenka",
        "file": "profil-rebenka.html",
        "h1": "Как убрать из речевого материала непоставленные звуки",
        "title": "Непоставленные звуки в материале на автоматизацию — Логозвук",
        "description": "Пока ш и ж не поставлены, слова с ними мешают. Показываем на "
                       "замере, сколько слов уходит из листа при разных профилях ребёнка.",
        # Родителя нет намеренно: страница сквозная. Появится категория Л — она
        # сошлётся сюда, а не перепишет то же самое своими словами (это и была бы
        # запрещённая каноном подстановка буквы).
        "parent": None,
        "widget": None,
        "draft": False,
    },
    {
        "slug": "docs",
        "file": "docs.html",
        "h1": "Как устроены наши материалы",
        "title": "Как устроены материалы — автоматизация звука",
        "description": "Из каких блоков собран каждый материал и откуда взято каждое "
                       "слово. Короткие страницы для тех, кто хочет проверить, чем печатает.",
        "parent": None,
        "widget": None,
        "draft": True,
    },
    # Слаги доков намеренно совпадают со слагами материалов в адресе виджета
    # (list · slogovaya-dorozhka · labirint): одна карта имён на сайт и на инструмент.
    {
        "slug": "docs/list",
        "file": "docs-list.html",
        "h1": "Как собран лист автоматизации",
        "title": "Как собран лист автоматизации — Логозвук",
        "description": "Лист автоматизации состоит из семи блоков — от разминки до "
                       "чистоговорки. Разбираем каждый: что в нём стоит и почему именно там.",
        "parent": "docs",
        "widget": None,
        "draft": True,
    },
    {
        "slug": "docs/slogovaya-dorozhka",
        "file": "docs-dorozhka.html",
        "h1": "Как собрана слоговая дорожка",
        "title": "Как собрана слоговая дорожка — Логозвук",
        "description": "Слоговая дорожка: ребёнок ведёт палец по тропе и проговаривает "
                       "слоги. Показываем, как она собрана и чем отличается от листа.",
        "parent": "docs",
        "widget": None,
        "draft": True,
    },
    {
        "slug": "docs/labirint",
        "file": "docs-labirint.html",
        "h1": "Как собран лабиринт",
        "title": "Как собран лабиринт — Логозвук",
        "description": "Лабиринт на автоматизацию звука: девять картинок, один проход. "
                       "Откуда берутся слова и почему не любая позиция звука доступна.",
        "parent": "docs",
        "widget": None,
        "draft": True,
    },
    {
        "slug": "docs/kakie-zvuki",
        "file": "docs-zvuki.html",
        "h1": "Какие звуки генератор собирает сейчас",
        "title": "Какие звуки генератор собирает сейчас — Логозвук",
        "description": "Какие звуки генератор собирает сейчас, каких нет и почему. "
                       "Честная карта: где материала хватает на все ступени, а где формат ограничен.",
        "parent": "docs",
        "widget": None,
        "draft": True,
    },
    # ── ОСЬ «КЕМ ПРИМЕНЯЕТСЯ» (канон ШАГ 4) ────────────────────────────
    # Заведена 08-23. Канон просит 3-4 оси нарезки, у нас была одна («на чём» —
    # звук) и та одним экземпляром. Эта ось свободна и, в отличие от звуковой,
    # НЕ упирается в ненаписанную методику звука: разница между логопедом ДОУ и
    # родителем настоящая, а не подстановка буквы. У эталона annotatepdf эта ось —
    # три страницы и самый длинный текст на сайте.
    {
        "slug": "dlya-kogo",
        "file": "dlya-kogo.html",
        "h1": "Кому нужен этот лист",
        "title": "Кому нужен лист на автоматизацию звука — Логозвук",
        "description": "Один и тот же лист выглядит по-разному у логопеда детского сада, "
                       "у частного логопеда и у родителя. Показываем, чем именно.",
        "parent": None,
        # Виджета у ХАБА нет намеренно: у эталона категория виджета не несёт,
        # только листья (проверено в исходнике articlesummarizer.app 08-23).
        "widget": None,
        "draft": True,
    },
    {
        "slug": "dlya-kogo/logoped-dou",
        "file": "dlya-kogo-logoped-dou.html",
        "h1": "Логопеду детского сада",
        "title": "Материал на автоматизацию звука логопеду ДОУ — Логозвук",
        "description": "В циклограмме логопеда ДОУ стоит «Изготовление пособий» — час "
                       "каждый день. Лист под конкретного ребёнка собирается за минуту.",
        "parent": "dlya-kogo",
        "widget": "?sound=r&material=list&embed=1",
        "draft": True,
    },
    {
        "slug": "dlya-kogo/chastnyy-logoped",
        "file": "dlya-kogo-chastnyy.html",
        "h1": "Частному логопеду",
        "title": "Речевой материал частному логопеду — Логозвук",
        "description": "Разные дети в один день, десять минут между занятиями и свой "
                       "принтер. Лист собирается под профиль ребёнка и печатается сразу.",
        "parent": "dlya-kogo",
        "widget": "?sound=r&material=list&embed=1",
        "draft": True,
    },
    {
        "slug": "dlya-kogo/roditel",
        "file": "dlya-kogo-roditel.html",
        "h1": "Родителю",
        "title": "Домашнее задание логопеда — как заниматься дома | Логозвук",
        "description": "Лист даёт логопед, а ведёт занятие родитель. На домашнем листе "
                       "есть подсказки, как делать каждое упражнение, и место для отметок.",
        "parent": "dlya-kogo",
        # Режим В АДРЕСЕ по-настоящему: человек пришёл за домашним заданием —
        # виджет открывается сразу домашним листом, а не листом на занятие.
        "widget": "?sound=r&material=list&audience=doma&embed=1",
        "draft": True,
    },
    # ── ОСЬ «КОНКУРЕНТЫ» (канон ШАГ 4) ─────────────────────────────────
    # Сквозная, как profil-rebenka: родителя нет, сошлются и звуковые страницы,
    # и «для кого». Здесь живёт ров — единственное, чего бумага не умеет.
    {
        "slug": "chem-otlichaetsya-ot-kartoteki",
        "file": "chem-otlichaetsya.html",
        "h1": "Чем это отличается от готовой картотеки",
        "title": "Генератор листов или готовая картотека — Логозвук",
        "description": "У бумажного альбома материал один на всех детей. Показываем на "
                       "замере, что меняется, когда лист собирается под профиль ребёнка.",
        "parent": None,
        "widget": None,
        "draft": False,
    },
    {
        "slug": "o-proekte",
        "file": "o-proekte.html",
        "h1": "О проекте",
        "title": "О проекте — автоматизация звука",
        "description": "Кто и зачем сделал сервис для автоматизации звука, что уже "
                       "работает, а чего ещё нет. Пишем честно, без обещаний, которых лист не выполняет.",
        "parent": None,
        "widget": None,
        "draft": False,
    },
    {
        "slug": "kontakty",
        "file": "kontakty.html",
        "h1": "Контакты",
        "title": "Контакты — автоматизация звука",
        "description": "Почта, форма обратной связи и реквизиты проекта. Пишите, если "
                       "лист напечатался не так, как ждали, или нужен звук, которого пока нет.",
        "parent": None,
        "widget": None,
        "draft": False,
    },
)

BY_SLUG: Dict[str, Page] = {p["slug"]: p for p in PAGES}


def url_of(slug: str) -> str:
    """Канонический адрес страницы. Форма ОДНА: со слешем на конце.

    Два вида одного адреса — самая дорогая грабля чужого опыта: сайт начинает
    ссылаться сам на свой дубль, и консоль засоряется непроиндексированными
    страницами. Поэтому вид ровно один, а второй отдаёт один 301 (не цепочку).
    """
    return f"{SITE_URL}/" if not slug else f"{SITE_URL}/{slug}/"


def live_pages() -> List[Page]:
    """Страницы, которые реально отдаются: черновиков здесь нет."""
    return [p for p in PAGES if not p.get("draft")]


def breadcrumbs(page: Page) -> List[Page]:
    """Цепочка от главной до страницы. Нужна и разметке, и человеку."""
    chain: List[Page] = []
    cur: Optional[Page] = page
    while cur is not None:
        chain.append(cur)
        parent = cur.get("parent")
        cur = BY_SLUG.get(parent) if parent is not None else None
    if page["slug"] and BY_SLUG.get("") not in chain:
        chain.append(BY_SLUG[""])
    chain.reverse()
    return chain


def children(slug: str) -> List[Page]:
    return [p for p in live_pages() if p.get("parent") == slug]


def _children_block(page: Page) -> str:
    """Ссылки на вложенные страницы — обязательная часть страницы-категории.

    Канон Site Builders (ШАГ 7) даёт прямую проверку структуры: «убрал последний
    слаг из адреса — должен попасть на страницу категории, и там должны быть
    ссылки на все вложенные страницы. Не попал — структура нарушена». Там же:
    «ссылки на вложенные страницы нужно проследить руками — сами они не появятся».

    Руками мы их не проставляем намеренно: список берётся из реестра, поэтому
    не может разойтись с ним. Забыть страницу здесь физически нельзя — а руками
    забыть можно, и это ровно та ошибка, которую канон и описывает.

    Нет детей — пусто, никакой коробки. Заголовка нет: у категории уже есть h1,
    второй заголовок над списком из трёх ссылок был бы лишним словом на экране.
    """
    kids = children(page["slug"])
    if not kids:
        return ""
    e = html.escape
    items = "\n".join(
        f'    <li><a href="{url_of(k["slug"])}">{e(k["h1"])}</a> '
        f'<span class="kid-what">{e(k["description"].split(".")[0])}.</span></li>'
        for k in kids
    )
    return f'  <ul class="kids">\n{items}\n  </ul>'


# ─── разметка для поиска ────────────────────────────────────────────────────

def _jsonld(page: Page) -> str:
    """JSON-LD: WebSite + WebPage + Organization + BreadcrumbList.

    Разметка ставится ТОЛЬКО на страницах сайта. У виджета её нет намеренно:
    приложение, встроенное через iframe, не должно нести собственную разметку —
    она продублирует разметку страницы.
    """
    graph: List[Dict[str, Any]] = [
        {
            "@type": "WebSite",
            "@id": f"{SITE_URL}/#website",
            "url": f"{SITE_URL}/",
            "name": PROJECT["name"],
            "inLanguage": "ru-RU",
        },
        {
            "@type": "WebPage",
            "@id": url_of(page["slug"]) + "#webpage",
            "url": url_of(page["slug"]),
            "name": page["title"],
            "description": page["description"],
            "isPartOf": {"@id": f"{SITE_URL}/#website"},
            "inLanguage": "ru-RU",
        },
    ]

    org: Dict[str, Any] = {
        "@type": "Organization",
        "@id": f"{SITE_URL}/#org",
        "name": PROJECT["name"],
        "url": f"{SITE_URL}/",
    }
    if PROJECT["email"]:
        org["email"] = PROJECT["email"]
    # sameAs ставится только если ссылка ЕСТЬ и видимой ссылкой на странице тоже:
    # одной разметки мало, без живой ссылки сигнал слишком слабый.
    if PROJECT["social"]:
        org["sameAs"] = [PROJECT["social"]]
    graph.append(org)

    chain = breadcrumbs(page)
    if len(chain) > 1:
        graph.append({
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1,
                 "name": p["h1"], "item": url_of(p["slug"])}
                for i, p in enumerate(chain)
            ],
        })

    return json.dumps({"@context": "https://schema.org", "@graph": graph},
                      ensure_ascii=False, indent=1)


def _footer(page: Page) -> str:
    """Подвал — сквозной, из одного словаря `PROJECT`."""
    e = html.escape
    bits: List[str] = [f'<span class="f-name">{e(PROJECT["name"])}</span>']
    if PROJECT["address"]:
        bits.append(f'<span class="f-addr">{e(PROJECT["address"])}</span>')
    if PROJECT["email"]:
        bits.append(f'<a href="mailto:{e(PROJECT["email"])}">{e(PROJECT["email"])}</a>')
    if PROJECT["social"]:
        bits.append(f'<a href="{e(PROJECT["social"])}" rel="me">{e(PROJECT["social"])}</a>')

    links = [p for p in live_pages() if p["slug"] in ("kontakty", "o-proekte", "docs")]
    nav = " · ".join(
        f'<a href="{url_of(p["slug"])}">{e(p["h1"])}</a>' for p in links
    )
    return (
        '<footer class="site-foot">\n'
        f'  <div class="f-org">{" · ".join(bits)}</div>\n'
        + (f'  <nav class="f-nav">{nav}</nav>\n' if nav else "")
        + "</footer>"
    )


def _crumbs(page: Page) -> str:
    chain = breadcrumbs(page)
    if len(chain) < 2:
        return ""
    e = html.escape
    parts = [f'<a href="{url_of(p["slug"])}">{e(p["h1"])}</a>' for p in chain[:-1]]
    parts.append(f'<span>{e(chain[-1]["h1"])}</span>')
    return '<nav class="crumbs">' + " → ".join(parts) + "</nav>"


def _widget(page: Page) -> str:
    """Виджет — fullwidth, ПЕРВЫМ экраном, шапки сайта над ним нет.

    Канон: «нам нужно на сайте забрать весь фокус на сам сервис»; виджет не в
    первом экране или за кнопкой «перейти к сервису» стоит 10-30 % трафика.
    Встраивается со своего же origin, поэтому ни X-Frame-Options, ни CSP чинить
    не надо — сервер их не ставит вовсе.
    """
    if not page.get("widget"):
        return ""
    return (
        '<div class="widget-box">\n'
        f'  <iframe class="widget" src="/app/{page["widget"]}" '
        'title="Генератор листов на автоматизацию звука" loading="eager"></iframe>\n'
        "</div>"
    )


def _body(page: Page) -> str:
    """Тело страницы — файл, который пишет автор. Нет файла → пусто, не ошибка."""
    path = os.path.join(PAGES_DIR, page["file"])
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def render(page: Page) -> bytes:
    """Собрать страницу целиком.

    Правила головы, из которых нельзя выйти:
      · h1 на странице РОВНО ОДИН — два h1 канон называет злом прямо;
      · title НЕ РАВЕН h1 (у внутренних — h1 плюс имя сайта через тире);
      · description есть у каждой и уникален;
      · canonical указывает на СЕБЯ и на конечный адрес, а не на тот, что редиректит;
      · og:url совпадает с canonical.
    """
    e = html.escape
    url = url_of(page["slug"])
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ru-RU">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{e(page['title'])}</title>\n"
        f'<meta name="description" content="{e(page["description"])}">\n'
        f'<link rel="canonical" href="{url}">\n'
        f'<meta property="og:type" content="website">\n'
        f'<meta property="og:site_name" content="{e(PROJECT["name"])}">\n'
        f'<meta property="og:title" content="{e(page["title"])}">\n'
        f'<meta property="og:description" content="{e(page["description"])}">\n'
        f'<meta property="og:url" content="{url}">\n'
        f'<meta property="og:locale" content="ru_RU">\n'
        # Картинка предпросмотра. Без неё Телеграм и соцсети показывают голую
        # ссылку — поймано 08-25, когда автор попробовал запостить в группу.
        # Адрес ОБЯЗАТЕЛЬНО полный: относительный путь эти боты не разворачивают.
        # 1200×630 — размер, который они ждут; на картинке настоящий лист, а не
        # нарисованный макет, — тот же закон, что и для иллюстраций страниц.
        f'<meta property="og:image" content="{SITE_URL}/img/og.png">\n'
        '<meta property="og:image:width" content="1200">\n'
        '<meta property="og:image:height" content="630">\n'
        f'<meta property="og:image:alt" content="Лист на автоматизацию звука — '
        f'{e(PROJECT["name"])}">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
        f'<meta name="twitter:image" content="{SITE_URL}/img/og.png">\n'
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">\n'
        '<link rel="stylesheet" href="/site.css">\n'
        f'<script type="application/ld+json">{_jsonld(page)}</script>\n'
        f"{analytics()}"
        "</head>\n"
        "<body>\n"
        f"{_widget(page)}\n"
        '<main class="site">\n'
        f"{_crumbs(page)}\n"
        f"<h1>{e(page['h1'])}</h1>\n"
        f"{_body(page)}\n"
        f"{_children_block(page)}\n"
        "</main>\n"
        f"{_footer(page)}\n"
        "</body>\n"
        "</html>\n"
    ).encode("utf-8")


def render_404() -> bytes:
    """Человеческая страница, а не голый текст «not found».

    Отдаётся с кодом 404 и с noindex: страница-ошибка не должна попасть в индекс
    и тратить бюджет обхода.
    """
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ru-RU">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="robots" content="noindex">\n'
        "<title>Страница не найдена</title>\n"
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">\n'
        '<link rel="stylesheet" href="/site.css">\n'
        "</head>\n"
        '<body>\n<main class="site">\n'
        "<h1>Такой страницы нет</h1>\n"
        f'<p>Вернуться на <a href="{SITE_URL}/">главную</a> '
        'или сразу <a href="/app/">собрать лист</a>.</p>\n'
        "</main>\n</body>\n</html>\n"
    ).encode("utf-8")


def robots_txt() -> bytes:
    """robots.txt.

    Канон про него почти молчит (за 425 сообщений чата сборки он не упомянут ни
    разу), поэтому пишем сами и внимательно. Закрываем то, что не является
    страницей: ответы движка и банк картинок — они тратят бюджет обхода и в
    выдаче не нужны. Сам виджет `/app/` НЕ закрываем: он не индексируется как
    страница (iframe), но робот должен видеть, что он существует и работает.
    """
    return (
        "User-agent: *\n"
        "Disallow: /api/\n"
        "Disallow: /geroi/\n"
        "\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    ).encode("utf-8")


def sitemap_xml() -> bytes:
    """Карта сайта: только живые публичные страницы, только <loc>.

    Черновиков здесь нет по построению. Адрес в карте обязан совпадать с
    canonical и отдавать 200, а не 301 — иначе карта сама себе противоречит.
    """
    urls = "\n".join(
        f"  <url><loc>{url_of(p['slug'])}</loc></url>" for p in live_pages()
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n"
        "</urlset>\n"
    ).encode("utf-8")

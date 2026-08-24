/* Флоу: звук → слог → лист. Профиль ребёнка спрашивается ПОСЛЕ первого листа
   и пересчитывает материал на глазах — это и есть ров.
   Ни имени ребёнка, ни возраста, ни диагноза, ни «листа №N» здесь нет. */

'use strict';

const S = {
  cfg: null,
  sound: null,
  typ: null,
  profile: new Set(),
  sheetNo: 1,
  tab: 'sheet',
  position: 'initial',
  syllable: '',    // слог, который РЕАЛЬНО на текущем листе
  prev: null,      // прошлые числа рва — чтобы подсветить, что изменилось
  // Куда лист. Молчащий дефолт — занятие; домашний берётся кнопкой (08-18):
  // элемент управления имеет цену, из двух названных остаётся одно название.
  audience: 'lesson',
  // Картинки лабиринта: молчащий дефолт — ЦВЕТ (решение автора 08-18: цветной
  // лист логопеду ближе), а ч/б берётся кнопкой — он же нужен тем, у кого
  // принтер без цвета. Набор слов от кнопки не меняется, только рисунки.
  colour: true,
  game: 'one_many',   // умолчание — «Один — много» (решение автора 08-10)
  games: null,     // какие игры живы на ТЕКУЩЕМ листе — приходит с листом
  scene: null,     // null = умолчание по персонажу, '' = логопед выбрал «без фона»
  sceneUsed: null, // какой фон реально встал на лист — приходит с материалом
  // Умолчание — «только звук»: это ПЕРВАЯ ступень приёма, изолированный звук
  // отрабатывается ДО слога (решение автора 08-24; порядок канонический).
  propisiMode: 'isolated',
  vowel: null,     // гласная слога звуковой дорожки; null = движок берёт первую
  theme: null,     // тема листа «сочини рассказ»; null = движок берёт самую полную
  storyMode: 'retell', // рассказы: пересказ готового текста | сочини сам
  textId: null,    // выбранный текст пересказа; null = первый чистый
  edited: false,   // логопед правил лист руками — сказать, когда правки сбросятся
};

// Материалы, у которых пересборка реально меняет выдачу. Лабиринта нет намеренно:
// на узких пулах seed даёт не другой набор, а перестановку тех же слов (проверено
// на [с] в начале: seed 0 и 1 — те же восемь слов), а кнопка, которая выглядит
// рабочей и ничего не меняет, — та же ложь, что погашенная кнопка без причины.
// Материалы, у которых есть что красить.
const COLOURABLE = new Set(['maze', 'sheet', 'track', 'propisi']);

// Материалы, у которых профиль ребёнка ЧТО-ТО МЕНЯЕТ. С 08-23 сюда входит и
// слоговая дорожка: слов она не печатает, но второй согласный стечения берётся
// из отобранных слов, и профиль решает, какие стечения законны. Ров (числа про
// объём банка) у неё по-прежнему свой — он считается отдельно, по USES_WORDS.
const USES_PROFILE = new Set(['sheet', 'maze', 'phrases', 'story', 'track']);

// Материалы, СОБРАННЫЕ ИЗ СЛОВ, — только у них профиль ребёнка что-то меняет.
// Признак именно такой, а не «есть слог»: у словосочетаний слога нет вовсе, и
// проверка по слогу прятала чипы там, где профиль работает (найдено 08-22).
// У дорожки и прописей слов нет: слог по построению чист (звук + гласная).
const USES_WORDS = new Set(['sheet', 'maze', 'phrases', 'story']);

// Кубик включён у лабиринта с 08-23. Прежде он был выключен «потому что на
// узких пулах seed даёт перестановку тех же слов» — и это объяснение оказалось
// неверным: seed не участвовал в отборе ВООБЩЕ (перемешивание гасила сортировка,
// где последним ключом стояло само слово), а пулы не узкие — у [с] в начале
// 63 слова на 8 клеток. Разобрано и исправлено в maze.py.
// ⚠ 2026-08-24. `propisi` отсюда снят: на звуковой дорожке кубик не менял
// НИЧЕГО. Гласную он крутил раньше — теперь она выбирается кнопками; линии
// заданы лестницей Поповой и не перебираются; слов на этом листе нет вовсе.
// Кнопка, которая выглядит рабочей и ничего не делает, — та же ложь, что
// погашенная кнопка без причины (закон 12, поймано автором).
const REROLLABLE = new Set(['sheet', 'track', 'phrases', 'story', 'maze']);


/* ── адрес страницы говорит, с чем открыть виджет ──────────
   На сайте виджет стоит в iframe внутри страницы, и страница обязана уметь
   сказать, ЧТО показать: /?sound=l&material=labirint&embed=1. Виджет для
   поиска невидим (содержимое iframe не индексируется) — ключи снимает
   страница, а параметр только доносит её тему до листа.

   Правило одно: неизвестное значение молча падает в умолчание, а не в ошибку.
   По этому адресу придут робот и случайная ссылка, и пустой экран вместо листа
   был бы той же ложью, что погашенная кнопка без причины (закон 12).

   Мягкость внутри пишется апострофом, в адресе так нельзя — берём хвост «j».
   Витринных материалов (4-й лишний · зашумлённые · обводка) в карте нет
   намеренно: адрес не имеет права открывать то, чего движок не соберёт. */
const SOUND_SLUG = {
  r: 'р', rj: "р'", l: 'л', lj: "л'", s: 'с', sj: "с'",
  z: 'з', zj: "з'", sh: 'ш', zh: 'ж', shch: 'щ',
};
const MATERIAL_SLUG = {
  list: 'sheet',
  'slogovaya-dorozhka': 'track',
  'zvukovaya-dorozhka': 'propisi',
  slovosochetaniya: 'phrases',
  labirint: 'maze',
  rasskaz: 'story',
};

// Адресат листа. Движок и экран домашний лист умеют давно — не хватало только
// адреса, а без него страница «домашнее задание» открывала бы лист для занятия,
// то есть обещала бы то, чего не покажет (закон 12).
const AUDIENCE_SLUG = { doma: 'home', zanyatie: 'lesson' };

const URLQ = new URLSearchParams(location.search);

// Fullwidth по канону: виджет от края до края в начале страницы, шапка сайта
// спрятана. Класс вешаем СРАЗУ при разборе скрипта, а не в boot(): boot ждёт
// ответа сервера, и за это время шапка успела бы мигнуть.
if (URLQ.get('embed') === '1') document.body.classList.add('embed');


const $ = (id) => document.getElementById(id);

/* Слог, который сейчас выбран, — подписью для человека («КЛА»). */
function curSyllable() {
  if (S.syllable) return S.syllable.toUpperCase();
  const t = ((S.cfg && S.cfg.syllables[S.sound]) || [])
    .find((x) => x.typ === S.typ);
  return t ? t.syllable : '';
}

/* Русское склонение числительных: «21 слово», а не «21 слов». */
function plural(n, one, few, many) {
  const a = Math.abs(n) % 100, b = a % 10;
  if (a > 10 && a < 20) return many;
  if (b > 1 && b < 5) return few;
  if (b === 1) return one;
  return many;
}

const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
};

/* ── человеческие подписи фонем ──────────────────────────── */

const SOFT = { "л'": 'Ль', "р'": 'Рь', "с'": 'Сь', "з'": 'Зь',
               "к'": 'Кь', "г'": 'Гь', "х'": 'Хь' };

function phLabel(key) {
  return SOFT[key] || key.toUpperCase();
}

function listLabels(keys) {
  return keys.map(phLabel).join(', ');
}

/* ── загрузка ────────────────────────────────────────────── */

async function boot() {
  S.cfg = await (await fetch('/api/config')).json();
  renderSounds();
  bindActions();
  // Решение автора 08-19: лист приходит СОБРАННЫМ. Экрана выбора звука перед
  // листом нет и промежуточного экрана «что делаем» нет — логопед видит бумагу,
  // а не следующий вопрос. Звук и материал остаются переключателями рядом с листом
  // (вкладки сверху и крошки), а на сайте звук вдобавок задаётся адресом страницы.
  openDefault();
}

// Звук по умолчанию — [р]: самая большая картотека (168 слов) и самый частый
// запрос ниши. Материал по умолчанию — лист автоматизации: единственный, кто
// проходит ступени внутри себя, то есть закрывает занятие целиком.
function openDefault() {
  const have = (S.cfg.sounds || []).map((s) => s.key);
  // Адрес сильнее умолчания, но только если он называет то, что у нас есть.
  const asked = SOUND_SLUG[(URLQ.get('sound') || '').toLowerCase()];
  S.sound = have.includes(asked) ? asked : (have.includes('р') ? 'р' : have[0]);
  S.tab = MATERIAL_SLUG[(URLQ.get('material') || '').toLowerCase()] || 'sheet';
  S.audience = AUDIENCE_SLUG[(URLQ.get('audience') || '').toLowerCase()] || 'lesson';
  // Цвет — свойство материала, ровно как при переключении вкладки (pickMaterial):
  // лабиринту он нужен для узнавания картинки, листу и дорожкам нет.
  S.colour = (S.tab === 'maze');
  S.typ = firstTypFor(S.tab);
  const t = (S.cfg.syllables[S.sound] || []).find((x) => x.typ === S.typ);
  S.syllable = t ? t.syllable : '';
  S.sheetNo = 1;
  show('result');
  renderChips();
  renderAudience();
  renderTabs();
  load();
}

async function post(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return r.json();
}

/* ── шаг 1: звук ─────────────────────────────────────────── */

function renderSounds() {
  // ЗВУК — закладки книги в вертикальном ряду. Прежде звук выбирался на
  // отдельном экране, а с листа туда вела серая крошка «звук Р». Слова автора
  // 08-22: «непонятно, если я на листе Л, а решил перейти на Р — как мне это
  // сделать? интуитивно ничто не подсказывает, что нужно нажать на „звук Л“».
  // Закладка решает это тем, что она всегда на виду и всегда одна нажатие.
  const rail = $('rail');
  if (!rail) return;
  rail.innerHTML = '';
  S.cfg.sounds.forEach((s) => {
    const b = el('button', 'rail-btn', s.label);
    b.title = `${s.stats.dict_total} ${plural(s.stats.dict_total, 'слово', 'слова', 'слов')} в картотеке`;
    b.classList.toggle('is-on', s.key === S.sound);
    // Смена звука пересобирает материал целиком — той же дверью, что вкладка.
    b.onclick = () => { S.sound = s.key; pickMaterial({ tab: S.tab }); };
    rail.appendChild(b);
  });
}

/* ── шаг 2: слог ─────────────────────────────────────────── */

/* Подписи движка длинны для кнопки; режем только повтор, канонный термин
   «стечение» остаётся — своих синонимов не выдумываем. */
const SHORT_LABEL = {
  cluster_onset: 'стечение перед гласной',
  cluster_coda: 'стечение после гласной',
};

/* Слог на кнопке читался как «выбрали гласную А» — потому что во всех типах
   стоит одна и та же А (РА · АР · АРА). Правка автора 08-18: показывать РОЛЬ,
   а не букву. Целевой звук — заглавный и крупный, всё вокруг него (гласные и
   соседние согласные в стечениях) — строчное и мелкое: «Ра», «аР», «аРа»,
   «кРа». Так на кнопке видно МЕСТО звука, а гласная явно служебная. */
function syllableGlyph(syl, soundLabel) {
  const box = el('span', 'syl-str');
  const target = (soundLabel || '')[0] || '';       // «Рь» → «Р»: мягкость несёт гласная
  const at = target ? syl.toUpperCase().indexOf(target.toUpperCase()) : -1;
  const put = (text, cls) => { if (text) box.appendChild(el('span', cls, text)); };
  if (at < 0) { put(syl.toUpperCase(), 'tgt'); return box; }
  put(syl.slice(0, at).toLowerCase(), 'side');
  put(syl.slice(at, at + target.length).toUpperCase(), 'tgt');
  put(syl.slice(at + target.length).toLowerCase(), 'side');
  return box;
}

/* Материалы, у которых слог свой, — их имена для подписи под кнопкой. */
const MATERIAL_TITLE = { track: 'слоговая дорожка', propisi: 'звуковая дорожка' };

/* Умеет ли материал ТЕКУЩИЙ слог. Правду про это знает движок
   (logoped_slovar/capabilities.py) и присылает её вместе с конфигом. */
function materialOk(tab, typ) {
  if (tab !== 'track' && tab !== 'propisi') return true;
  // На ступени «только звук» слога на бумаге нет вовсе — запрет ни при чём.
  if (tab === 'propisi' && S.propisiMode === 'isolated') return true;
  const t = (S.cfg.syllables[S.sound] || []).find((x) => x.typ === typ);
  const m = t && t.materials && t.materials[tab];
  return !m || m.ok;
}

/* Сколько типов слога РЕАЛЬНО живы у текущего материала. Считается ровно тем
   же способом, каким renderSylPick решает, гасить ли кнопку, — иначе счётчик и
   ряд разойдутся, и карточка спрячется там, где выбор есть. */
function sylChoices() {
  return (S.cfg.syllables[S.sound] || []).filter((t) => {
    const m = (t.materials || {})[S.tab];
    return m ? m.ok : t.available;
  });
}

function materialWhy(tab, typ) {
  const t = (S.cfg.syllables[S.sound] || []).find((x) => x.typ === typ);
  const m = t && t.materials && t.materials[tab];
  return (m && m.why) || '';
}

function soundLabel() {
  const s = (S.cfg.sounds || []).find((x) => x.key === S.sound);
  return s ? s.label : '';
}


/* Кнопки типа слога — теперь настройка материала в панели, а не отдельный шаг
   (08-18). Логика прежняя: подпись «Ра · аР · аРа», ряд остальных гласных,
   предупреждение о бедном слоге и погашенная кнопка с причиной. */
function renderSylPick() {
  const box = $('syl-pick');
  if (!box) return;
  box.innerHTML = '';
  const list = (S.cfg.syllables[S.sound] || []);
  list.forEach((t) => {
    const mats = t.materials || {};
    const mine = mats[S.tab] || { ok: t.available, why: '' };
    const b = el('button', 'seg-btn' + (t.typ === S.typ ? ' is-on' : ''));
    b.appendChild(syllableGlyph(t.syllable, soundLabel()));
    b.title = SHORT_LABEL[t.typ] || t.label;
    if (!mine.ok) {
      b.disabled = true;
      b.classList.add('is-off');
      b.title = mine.why || b.title;
    } else if (t.thin) {
      b.classList.add('is-thin');
    }
    b.onclick = () => {
      if (!mine.ok || t.typ === S.typ) return;
      S.typ = t.typ;
      S.syllable = t.syllable;
      S.sheetNo = 1;
      S.games = null;
      renderSylPick();
      renderTabs();
      load();
    };
    box.appendChild(b);
  });
  const cur = list.find((x) => x.typ === S.typ) || {};
  const kind = SHORT_LABEL[cur.typ] || cur.label || '';
  const thin = cur.thin
    // Число канона приходит с сервера полем need: на стечениях канон 7, а не 12,
    // и вшитая двенадцатка печатала логопеду неправду («3 из 12» вместо «3 из 7»).
    ? ' Слов в картотеке мало: ' + cur.words + ' из ' + (cur.need || 12)
      + ' канонных — лист выйдет бедным.'
    : '';
  // Подписи под рядом больше нет (решение автора 08-22): название типа
  // повторяло то, что кнопка показывает глифом, и уехало в ховер самой кнопки.
  // Осталось только предупреждение о бедной картотеке — оно не про устройство
  // кнопки, а про то, каким выйдет лист, и молчать о нём нельзя.
  //
  // ⚠ 2026-08-23. Причина у ПОГАШЕННОГО слога жила только в ховере (`b.title`).
  // У лабиринта и у игр та же причина выведена строкой на экран, и логопед её
  // видит; у слогов — нет, и погашенная кнопка молчала. Это ровно закон 12:
  // «погашенная кнопка без объяснения — та же ложь, только тише». С ховера
  // причина не читается вовсе на телефоне, где ховера не существует.
  const off = list.filter((t) => {
    const m = (t.materials || {})[S.tab];
    return m ? !m.ok : !t.available;
  });
  // Причины ПОГАШЕННЫХ кнопок — одной строкой и без повторов. У слоговой
  // дорожки два стечения гаснут по ОДНОЙ причине, и разница между текстами
  // только в слоге внутри кавычек: печатать оба — значит дважды сказать одно.
  // Сравниваем тексты, вырезав кавычечную вставку, и оставляем первый.
  const seen = new Set();
  const offSaid = [];
  off.forEach((t) => {
    const why = materialWhy(S.tab, t.typ);
    if (!why) return;
    const key = why.replace(/«[^»]*»/g, '«»');
    if (seen.has(key)) return;
    seen.add(key);
    offSaid.push(why);
  });
  const warnThin = $('syl-thin');
  if (warnThin) {
    const said = [thin.trim(), ...offSaid].filter(Boolean).join(' ');
    warnThin.textContent = said;
    warnThin.hidden = !said;
  }
}


function soundLabel() {
  const s = (S.cfg.sounds || []).find((x) => x.key === S.sound);
  return s ? s.label : '';
}


function show(step) {
  // Экран остался ОДИН — лист. Функция сохранена, чтобы не переписывать
  // полсотни вызовов, и чтобы возврат экранов был дешёвым, если понадобится.
  const r = $('step-result');
  if (r) r.hidden = false;
  if (step) fitFrame();
}

/* ⚠ Крошки сняты целиком 08-22: материал назван вкладкой, звук — закладкой,
   тип слога — кнопками в панели. Повторять всё это четвёртый раз строкой в
   углу незачем. */

/* ── шаг 2: ступень и материал ────────────────────────────── */

/* ⚠ Массив STAGES снят 08-22 вместе с экраном «Что делаем?»: он описывал
   ступени автоматизации и карточки материалов для того экрана, а материал
   теперь выбирается полосой вкладок. Ступени как ЗНАНИЕ никуда не делись —
   они живут в каноне и в `research/`, а не в разметке экрана. */

/* Первый тип слога, на котором материал собирается: логопед выбрал МАТЕРИАЛ,
   а слог у него настраивается потом — значит стартовый слог берём рабочий. */
function firstTypFor(tab) {
  const list = (S.cfg.syllables[S.sound] || []);
  const t = list.find((x) => {
    const m = x.materials && x.materials[tab];
    return m ? m.ok : x.available;
  });
  return (t || list[0] || {}).typ || 'direct';
}

/* Выбранный рассказ и выбранная тема — свойство ЗВУКА И ПРОФИЛЯ, а не сессии:
   их список приходит ВМЕСТЕ с материалом, потому что зависит от того, какие
   звуки у этого ребёнка не поставлены. Сменился звук или профиль — прошлый
   выбор относился к прошлому ребёнку, и просить его у движка нельзя: рассказа
   «r-01» на [Л] не существует (id рассказов по звукам не пересекаются вовсе),
   а темы «музыка» на [Л] нет. Прежде выбор переживал смену звука, лист упирался
   в отказ «текста „r-02“ для этого профиля нет», и выхода из отказа не было:
   на экране стояли кнопки текстов ПРОШЛОГО звука, нажатие на любую снова просило
   чужой текст, и лечило только обновление страницы (поймано автором 08-23).
   Природа та же, что у фона: он тоже относится к герою звука и сбрасывается при
   смене — только его список известен заранее, и чистит его renderScenePick. */
function forgetPicks() {
  S.textId = null; S.textUsed = null; S.textOptions = [];
  S.theme = null;  S.themeUsed = null; S.themes = [];
}

function pickMaterial(it) {
  if (it.soon) { S.tab = it.tab; show('result'); renderTabs(); showSoon(it.tab); return; }
  S.tab = it.tab;
  if (it.mode) S.propisiMode = it.mode;
  if (it.storyMode) S.storyMode = it.storyMode;
  S.typ = firstTypFor(it.tab);
  const t = (S.cfg.syllables[S.sound] || []).find((x) => x.typ === S.typ);
  S.syllable = t ? t.syllable : '';
  S.sheetNo = 1;
  // Цвет — свойство материала: лабиринту он нужен для узнавания картинки,
  // листу и дорожкам нет (печать на обычном принтере). Поэтому при смене
  // материала умолчание возвращается, а не тянется из прошлого выбора.
  S.colour = (it.tab === 'maze');
  // S.profile НЕ чистим: профиль ребёнка — часть задачи, а не настройка листа.
  // Прежде он стирался на каждом переключении материала, и ров продукта
  // (фильтр по непоставленным звукам) сбрасывался незаметно для логопеда.
  S.prev = null;
  S.games = null;
  forgetPicks();
  $('ask').hidden = true;        // профиль спрашиваем после первого материала
  $('warn').hidden = true;
  $('moat').innerHTML = '';
  show('result');
  renderChips();
  renderAudience();
  renderTabs();
  load();
}


/* ── шаг 3: материал ─────────────────────────────────────── */

/* Витрина: материалы, которых ещё нет. Текст — чего именно ждёт материал;
   врать «скоро» нельзя, поэтому здесь стоит настоящая причина. */
const SOON = {
  'soon-odd': {
    title: '4-й лишний',
    what: 'Девять картинок, три со звуком и одна лишняя: ребёнок находит чужую и называет остальные.',
    waits: 'Банк своих картинок готов с 08-18 — осталось построить сам материал.',
  },
  'soon-noise': {
    title: 'Зашумлённые картинки',
    what: 'Предмет, перечёркнутый линиями: ребёнок узнаёт его и называет, звук повторяется на каждом узнавании.',
    waits: 'Тот же банк картинок готов — осталось построить сам материал.',
  },
  'soon-trace': {
    title: 'Обводка',
    what: 'Контур предмета, который ребёнок обводит, произнося звук, — по канону Борисовой обводка несёт речевой материал, а не мелкую моторику.',
    waits: 'Банк картинок готов; линия со слогом уже работает — она на ступени «Слоги».',
  },
};

/* Заголовок группы без содержимого читается как поломка: на витрине все
   настройки скрыты, и «ЭТОТ ЛИСТ» висел над пустотой (08-18). */
function syncGroupTitle() {
  // Заголовков групп на экране больше нет (08-22 снят «Этот лист», 08-23 —
  // «Почему так»). Функция оставлена пустой намеренно: её зовут из нескольких
  // мест, и выкорчёвывать вызовы ради двух строк — правка, добавляющая работу,
  // а не убирающая её.
}


function renderTabs() {
  document.querySelectorAll('.tab').forEach((b) => {
    b.classList.toggle('is-on', b.dataset.tab === S.tab);
    // Витрина видна всегда: она говорит не про слог, а про весь замысел.
    if (b.dataset.soon) { b.hidden = false; return; }
    // Материала на этом слоге нет — вкладки нет. Сначала она была серой с
    // объяснением, но автор 08-10: «раз её нет, не надо и показывать» —
    // погашенная вкладка заставляет разбираться там, где разбираться не в чем.
    b.hidden = !materialOk(b.dataset.tab, S.typ);
  });
  // На витринной вкладке настраивать нечего: материала ещё нет.
  const soon = !!SOON[S.tab];
  $('tab-extra').hidden = soon || (S.tab !== 'maze');
  if (S.tab !== 'maze') $('maze-limits').hidden = true;
  // Цвет есть там, где есть что красить: картинки лабиринта и герой звука.
  // Умолчания РАЗНЫЕ и это не прихоть: картинке лабиринта цвет нужен для
  // узнавания (борщ в ч/б назовут супом), а герою — нет, зато лист печатают
  // на обычном принтере, где цветная заливка садится серым.
  // Ряд «как печатать» показывается, если в нём есть хоть одна живая кнопка.
  const canColour = COLOURABLE.has(S.tab);
  const canAudience = (S.tab === 'sheet');
  $('colour-btn').hidden = !canColour;
  $('audience-btn').hidden = !canAudience;
  $('print-as').hidden = soon || !(canColour || canAudience);
  // Тип слога — только у материалов, которые его получают (см. сигнатуры
  // движка: sheet.typ · track.syl_type · propisi.syl_type). У лабиринта своя
  // ось (позиция), у словосочетаний и рассказов оси нет вовсе.
  //
  // ⚠ 2026-08-23. Мало «материал слог получает» — нужно, чтобы выбор БЫЛ.
  // У звуковой дорожки тип слога один (`PROPISI_TYPES = ("direct",)`), и
  // карточка показывала ряд из пяти кнопок, где живая одна. Это не выбор, а
  // его видимость: ровно то, что запрещает закон 13 («элемент управления имеет
  // цену»), и заодно четыре объяснения подряд под рядом — стена текста вместо
  // экрана. Считаем ПО ДАННЫМ, а не по списку вкладок: доступен один тип —
  // карточки нет вовсе, вместе со всеми объяснениями.
  const usesSyllable = ((S.tab === 'sheet') || (S.tab === 'track')
    || (S.tab === 'propisi' && S.propisiMode !== 'isolated'))
    && sylChoices().length > 1;
  $('syl-card').hidden = soon || !usesSyllable;
  if (usesSyllable && !soon) renderSylPick();
  renderSounds();   // закладка активного звука обновляется вместе со всем
  renderColour();
  if (S.tab === 'maze') renderPositions();
  $('reroll').hidden = !REROLLABLE.has(S.tab);
  // Профиль ребёнка меняет лист, лабиринт И СЛОВОСОЧЕТАНИЯ, но не дорожку и не
  // прописи: там нет слов, а слог по построению чист (целевой звук + гласная).
  // ⚠ Словосочетания были исключены ошибочно: профиль уходил на сервер и менял
  // все пары, а карточка чипов была спрятана — настройка не погашена, её просто
  // не было, а действие было. Худший случай закона 12: логопед менял материал,
  // не видя, чем (найдено разбором 08-22).
  $('ask').hidden = soon || !USES_PROFILE.has(S.tab);
  // «Домой / на занятие» — свойство ЛИСТА: шапка-документ и подвал взрослому
  // есть только у него. У дорожки и лабиринта их нет, переключать нечего.
  // Сама кнопка живёт в ряду «как печатать», её видимость выставлена выше.
  // Ступень «только звук / звук + слог» есть лишь у звуковой дорожки.
  $('stage-step').hidden = (S.tab !== 'propisi');
  $('scene-card').hidden = (S.tab !== 'track');
  $('story-mode-card').hidden = (S.tab !== 'story');
  // Списки тем и текстов приходят С МАТЕРИАЛОМ, поэтому карточка стоит только
  // когда список описывает то, что сейчас на экране. Иначе между нажатием и
  // ответом логопед видел бы пустую коробку с подписью «на этом звуке пока
  // один текст» — фразой про звук, который уже сменился.
  $('theme-card').hidden = !(S.tab === 'story' && S.storyMode === 'compose'
                             && (S.themes || []).length);
  $('text-card').hidden = !(S.tab === 'story' && S.storyMode === 'retell'
                            && (S.textOptions || []).length);
  $('game-card').hidden = (S.tab !== 'sheet');
  // Ров есть только там, где ему есть что сказать ЧИСЛОМ. На дорожках он
  // пересказывал очевидное — «30 кружков и такие-то гласные», — что логопед и
  // так видит на бумаге (слово автора 08-23: «вообще лишний блок»). Материалы
  // из слов — другое дело: там ров говорит про ОБЪЁМ БАНКА, а этого на листе
  // не видно.
  $('moat-box').hidden = soon || !USES_WORDS.has(S.tab);
  if (S.tab === 'sheet') renderGamePick();
  if (S.tab === 'track') renderScenePick();
  if (S.tab === 'story') { renderStoryMode(); renderThemePick(); renderTextPick(); }
  if (S.tab === 'propisi') { renderPropisiMode(); renderVowelPick(); }
  // Заголовок рва называет ТОТ материал, который сейчас на экране: «этот лист»
  // на прописях было бы неправдой — там не лист, а дорожки.
  $('moat-summary').textContent = {
    sheet:   'Из чего собран этот лист',
    phrases: 'Из чего собраны эти словосочетания',
    maze:    'Из чего собран этот лабиринт',
    story:   'Из чего собран этот рассказ',
  }[S.tab] || 'Из чего это собрано';
  syncGroupTitle();
}
function renderColour() {
  // Одно имя и одна логика галочки на всех материалах. Прежде кнопка
  // переворачивала И название («Без цвета» ↔ «Цветной герой»), И смысл галочки
  // (на лабиринте is-on означало ОТСУТСТВИЕ цвета) — её приходилось перечитывать
  // при каждой смене вкладки. Разные УМОЛЧАНИЯ по материалам остаются: лабиринту
  // цвет нужен для узнавания картинки, листу нет (pickMaterial).
  $('colour-btn').classList.toggle('is-on', S.colour);
  $('colour-btn').lastChild.textContent = 'Цветной лист';
}


function renderAudience() {
  // Подпись снята 08-22: кнопка самоочевидна, а два состояния читаются
  // залипанием — этого хватает (закон 13).
  $('audience-btn').classList.toggle('is-on', S.audience === 'home');
}

/* Живая игра или нет — свойство КОНКРЕТНОГО листа: игры собираются из его же
   слов. Поэтому кнопки рисуются по ответу листа (`res.games`), а не по конфигу.
   Раньше все три кнопки были активны всегда: на листе, где выбранная игра не
   набирает четырёх примеров, движок молча откатывался к другой, логопед жал
   «Назови ласково» и видел прежнюю игру без единого слова объяснения (08-10). */
function renderGamePick() {
  const box = $('game-pick');
  const state = S.games;
  const items = (state && state.items) || (S.cfg.games || [])
    .map((g) => ({ key: g.key, label: g.label, ready: true, why: '' }));
  box.innerHTML = '';
  items.forEach((g) => {
    const b = el('button', 'seg-btn', g.label);
    b.dataset.game = g.key;
    if (!g.ready) {
      // Не прячем: логопед должен видеть, что игра есть в замысле, но на
      // ЭТОМ листе не собирается — и почему. Молчаливое отсутствие врёт.
      b.disabled = true;
      b.title = g.why || '';
      b.classList.add('is-off');
    } else {
      b.addEventListener('click', () => {
        if (S.game === g.key) return;
        S.game = g.key;
        load();
      });
    }
    box.appendChild(b);
  });
  // Горит та игра, которая РЕАЛЬНО напечатана на листе, а не та, которую
  // выбрали: если движок отдал другую, кнопка обязана это показать.
  const on = (state && state.printed) || S.game;
  box.querySelectorAll('.seg-btn').forEach((b) => {
    b.classList.toggle('is-on', b.dataset.game === on);
  });

  const off = items.filter((g) => !g.ready);
  let hint = off.map((g) => '«' + g.label + '» на этом листе не собирается: '
                            + g.why + '.').join(' ');
  if (state && state.dropped) hint = state.dropped;
  else if (state && state.fallback) {
    const lab = (items.find((g) => g.key === state.printed) || {}).label || '';
    hint = 'На листе стоит «' + lab + '»: выбранная игра на его словах не '
         + 'набралась. ' + hint;
  }
  $('game-hint').textContent = hint;
}


/* Фон — контекст ГЕРОЯ, а не общий список: у комарика лес и пруд, у мотора
   дорога и город (08-10). Поэтому кнопки перестраиваются при смене звука, а
   выбранный фон чужого героя сбрасывается — он относился к прошлому герою. */
function sceneList() {
  return (S.cfg.scenes_by_sound && S.cfg.scenes_by_sound[S.sound])
    || S.cfg.scenes || [];
}

/* Темы листа «сочини рассказ». Список приходит С ЛИСТОМ: он зависит от
   профиля ребёнка, и показывать тему, в которой после чистки не осталось
   шести слов, нельзя — кнопка обещала бы то, чего материал не сделает. */
function renderStoryMode() {
  $('story-mode-btn').classList.toggle('is-on', S.storyMode === 'compose');
}

/* Тексты пересказа — только чистые для профиля; список приходит с листом. */
function renderTextPick() {
  const box = $('text-pick');
  box.innerHTML = '';
  const list = S.textOptions || [];
  list.forEach((o) => {
    const b = el('button', 'seg-btn', o.title);
    b.classList.toggle('is-on', o.id === S.textUsed);
    b.addEventListener('click', () => {
      if (o.id === S.textUsed) return;
      S.textId = o.id;
      load();
    });
    box.appendChild(b);
  });
  $('text-hint').textContent = list.length > 1
    ? 'Все тексты проверены: в них нет звуков, которые у ребёнка не получаются.'
    : 'На этом звуке пока один текст.';
}

function renderThemePick() {
  const box = $('theme-pick');
  box.innerHTML = '';
  const list = S.themes || [];
  list.forEach((t) => {
    const b = el('button', 'seg-btn', t);
    b.classList.toggle('is-on', t === S.themeUsed);
    b.addEventListener('click', () => {
      if (t === S.themeUsed) return;
      S.theme = t;
      load();
    });
    box.appendChild(b);
  });
  $('theme-hint').textContent = list.length > 1
    ? 'Слова одной темы — ребёнку есть за что зацепить историю.'
    : 'На этом звуке набирается одна тема: в остальных меньше шести чистых слов.';
}

function renderScenePick() {
  const box = $('scene-pick');
  const list = sceneList();
  if (S.scene !== null && !list.some((sc) => sc.key === S.scene)) S.scene = null;
  box.innerHTML = '';
  list.forEach((sc) => {
    const b = el('button', 'seg-btn', sc.label);
    b.dataset.scene = sc.key;
    b.addEventListener('click', () => {
      if (S.scene === sc.key) return;
      S.scene = sc.key;
      renderScenePick();
      load();
    });
    box.appendChild(b);
  });
  // Горит тот фон, который РЕАЛЬНО на листе. Пока логопед не выбирал, лист
  // печатается с умолчанием героя — и раньше при этом не горело ничего:
  // фон на бумаге есть, а какой именно, экран не говорил.
  const on = (S.scene !== null) ? S.scene : S.sceneUsed;
  box.querySelectorAll('.seg-btn').forEach((b) => {
    b.classList.toggle('is-on', on != null && b.dataset.scene === on);
  });
  // Подписи под кнопками фона нет намеренно: смена фона видна на листе сразу,
  // и объяснять очевидное — только занимать внимание (слово автора 08-10).
  $('scene-hint').textContent = '';
}


/* Гласная слога звуковой дорожки. Ряд приходит С ЛИСТОМ: у мягкой цели он свой
   («я ё ю и е»), у твёрдой свой («а о у ы э»), и держать его вторым списком в
   интерфейсе значило бы дать ему разойтись с движком.
   Показывается ТОЛЬКО когда включён слог: без слога гласной на бумаге нет. */
function renderVowelPick() {
  const box = $('vowel-pick');
  if (!box) return;
  const list = (S.tab === 'propisi' && S.propisiMode === 'syllable')
    ? (S.vowelOptions || []) : [];
  box.hidden = !list.length;
  box.innerHTML = '';
  list.forEach((v) => {
    const b = el('button', 'seg-btn', v.toUpperCase());
    b.classList.toggle('is-on', v === S.vowelUsed);
    b.addEventListener('click', () => {
      if (v === S.vowelUsed) return;
      S.vowel = v;
      load();
    });
    box.appendChild(b);
  });
}

function renderPropisiMode() {
  // Кнопка называет то, что ВКЛЮЧАЕТ: отжата — звук, нажата — слог.
  $('propisi-mode-btn').classList.toggle('is-on', S.propisiMode === 'syllable');
}

function positionList() {
  return (S.cfg.positions_by_sound && S.cfg.positions_by_sound[S.sound])
    || S.cfg.positions.map((p) => ({ key: p.key, label: p.label, ok: true, why: '' }));
}

/* Звук сменили, а выбранная позиция у нового звука не бывает — берём первую,
   которая бывает. Это не подмена выбора: выбор относился к прошлому звуку. */
function ensurePosition() {
  const list = positionList();
  if (list.some((p) => p.key === S.position && p.ok)) return;
  const first = list.find((p) => p.ok);
  if (first) S.position = first.key;
}

function renderPositions() {
  const box = $('positions');
  box.innerHTML = '';
  ensurePosition();
  // Позиции у каждого звука свои: у звонких слова на [З] в конце нет в языке,
  // у [Сь] и [Щ] не набирается девяти картинок. Кнопка, которая этого не
  // знает, обещает лабиринт и получает отказ (08-10, та же болезнь, что у
  // слогов и игр).
  const list = positionList();
  list.forEach((p) => {
    const b = el('button', 'pos' + (p.key === S.position ? ' is-on' : ''), p.label);
    if (!p.ok) {
      b.disabled = true;
      b.classList.add('is-off');
      b.title = p.why || '';
    } else {
      b.onclick = () => { S.position = p.key; renderPositions(); load(); };
    }
    box.appendChild(b);
  });
  const off = list.filter((p) => !p.ok);
  $('maze-limits').textContent = off.map((p) => '«' + p.label + '»: ' + p.why).join(' ');
  $('maze-limits').hidden = !off.length;
}

/* Каждому запросу — свой номер. Отвечает медленный сервер или логопед быстро
   щёлкает чипы — на экран попадает только ПОСЛЕДНИЙ запрошенный материал,
   а запросы не теряются. Раньше здесь стоял флаг busy, который просто ронял
   второй клик: чип горел, а лист оставался от прошлого профиля. */
let TICKET = 0;

/* Витрина: материала нет — движок не зовём, показываем, чего он ждёт. */
function showSoon(key) {
  const s = SOON[key];
  const box = $('stage-msg');
  box.innerHTML = '';
  $('stage').classList.remove('is-busy');
  $('stage').classList.add('is-msg');
  $('frame').style.visibility = 'hidden';
  if ($('save')) $('save').disabled = true;
  const wrap = el('div', 'engine-error calm');
  wrap.appendChild(el('h3', null, `${s.title} — готовится`));
  wrap.appendChild(el('p', null, s.what));
  wrap.appendChild(el('p', 'why', s.waits));
  box.appendChild(wrap);
  box.hidden = false;
  renderTabs();
}

async function load() {
  if (SOON[S.tab]) { showSoon(S.tab); return; }
  const my = ++TICKET;
  $('stage').classList.add('is-busy');
  if ($('save')) $('save').disabled = true;          // пока летит — печатать нечего

  const profile = [...S.profile];
  let res;
  try {
    if (S.tab === 'track') {
      // Дорожка Ольги: слоги по тропе. Слов нет — профиль на неё не влияет,
      // слог по построению чист (целевой звук + гласная).
      res = await post('/api/track',
        { sound: S.sound, typ: S.typ, seed: S.sheetNo - 1, colour: S.colour,
          profile: [...profile],
          ...(S.scene === null ? {} : { scene: S.scene }) });
    } else if (S.tab === 'story' && S.storyMode === 'retell') {
      // Пересказ готового текста. Профиль работает: отдаются только тексты,
      // чистые для ЭТОГО ребёнка.
      res = await post('/api/rasskaz',
        { sound: S.sound, profile: [...profile],
          ...(S.textId ? { text: S.textId } : {}) });
    } else if (S.tab === 'story') {
      // «Сочини рассказ» — лист взрослому. Слога нет, тема есть; профиль
      // работает: опорные слова обязаны быть чисты для ЭТОГО ребёнка.
      res = await post('/api/story',
        { sound: S.sound, profile: [...profile],
          ...(S.theme ? { theme: S.theme } : {}), seed: S.sheetNo - 1 });
    } else if (S.tab === 'propisi') {
      // Прописи: линия + слог. Слов тоже нет — профиль не влияет.
      res = await post('/api/propisi',
        { sound: S.sound, typ: S.typ, mode: S.propisiMode, seed: S.sheetNo - 1,
          colour: S.colour, ...(S.vowel ? { vowel: S.vowel } : {}) });
    } else if (S.tab === 'phrases') {
      // Здесь профиль работает на ОБЕ части пары: и на существительное,
      // и на прилагательное. Тип слога на словосочетания не влияет.
      res = await post('/api/phrases',
        { sound: S.sound, profile: profile, seed: S.sheetNo - 1 });
    } else if (S.tab === 'maze') {
      ensurePosition();
      res = await post('/api/maze',
        { sound: S.sound, position: S.position, profile: profile,
          seed: S.sheetNo - 1, colour: S.colour });
    } else {
      res = await post('/api/sheet',
        { sound: S.sound, typ: S.typ, profile: profile, sheet_no: S.sheetNo,
          audience: S.audience, game: S.game, colour: S.colour });
    }
  } catch (e) {
    if (my !== TICKET) return;
    $('stage').classList.remove('is-busy');
    showError({ kind: 'network',
                message: 'Не отвечает генератор. Проверьте, что сервер запущен, ' +
                         'и повторите — настройки сохранились.' });
    return;
  }

  if (my !== TICKET) return;           // ответ устарел, его обогнали
  $('stage').classList.remove('is-busy');

  if (!res.ok) { showError(res); return; }

  $('stage-msg').hidden = true;
  $('stage').classList.remove('is-msg');
  $('frame').style.visibility = 'visible';
  if (res.syllable) S.syllable = res.syllable;
  // Состояние игр приходит вместе с листом — это его свойство, а не настройка.
  // Выбор логопеда подтягиваем к напечатанному: иначе на кнопке остаётся игра,
  // которой на бумаге нет, и повторное нажатие по ней не делает ничего.
  if (S.tab === 'sheet') {
    S.games = res.games || null;
    if (res.games && res.games.printed) S.game = res.games.printed;
  }
  if (S.tab === 'track' && res.stats) S.sceneUsed = res.stats.scene;
  if (S.tab === 'propisi' && res.stats) {
    S.vowelOptions = res.stats.vowels || [];
    S.vowelUsed = res.stats.vowel || '';
  }
  // Пределы дорожки со стечениями — это ДАННЫЕ, а не жанр: законна ли рамка,
  // решает профиль ребёнка. Конфиг считается один раз и на пустом профиле,
  // поэтому кнопки горели все пять, что бы логопед ни отметил. Спрашиваем
  // отдельной дешёвой ручкой и правим конфиг на месте — закон 12 требует
  // объявлять пределы ЗАРАНЕЕ, а не отказом после нажатия.
  if (S.tab === 'track') refreshTrackTypes(profile);
  if (S.tab === 'story' && res.stats && res.stats.kind === 'story') {
    S.themes = res.stats.themes || [];
    S.themeUsed = res.stats.theme;
  }
  if (S.tab === 'story' && res.stats && res.stats.kind === 'rasskaz') {
    S.textOptions = res.stats.options || [];
    S.textUsed = res.stats.text;
  }
  // Карточки настроек и ров прячет экран отказа — материал собрался, вернуть.
  // Но ров возвращаем только тем, у кого он есть: на дорожках его нет вовсе,
  // и безусловное `false` здесь показывало бы пустую коробку (renderTabs ниже
  // выставит правду, но кадр между ними логопед бы увидел).
  $('moat-box').hidden = !USES_WORDS.has(S.tab);
  renderTabs();
  writeFrame(res.html);
  renderMoat(res.stats);
  renderWarnings(res.warnings);   // она же решает, можно ли печатать
  // Вопрос о профиле — только ПОСЛЕ первого материала и только там, где он
  // на что-то влияет. На дорожке и в прописях слов нет, убирать нечего.
  $('ask').hidden = !USES_PROFILE.has(S.tab);
}

/* Что дорожка умеет ДЛЯ ЭТОГО ребёнка. Ответ кладётся прямо в S.cfg, откуда
   его берут и ряд кнопок, и строка причин, — один дом у правды о пределах. */
async function refreshTrackTypes(profile) {
  let r;
  try {
    r = await post('/api/track_types',
      { sound: S.sound, profile: [...profile] });
  } catch (e) { return; }
  if (!r || !r.ok || !r.types) return;
  const list = S.cfg.syllables[S.sound] || [];
  let changed = false;
  list.forEach((t) => {
    const got = r.types[t.typ];
    if (!got || !t.materials || !t.materials.track) return;
    if (t.materials.track.ok !== got.ok) changed = true;
    t.materials.track.ok = got.ok;
    t.materials.track.why = got.why;
  });
  // Перерисовываем только когда правда изменилась: лишний кадр на каждом листе
  // не нужен, а мигание ряда кнопок логопед заметит.
  if (changed) renderSylPick();
}

function showError(res) {
  const box = $('stage-msg');
  box.innerHTML = '';
  const THING = { maze: 'лабиринт', track: 'слоговая дорожка',
                  propisi: 'звуковая дорожка',
                  phrases: 'словосочетания' }[S.tab] || 'лист';
  const VIN = { лабиринт: 'лабиринт', 'слоговая дорожка': 'слоговую дорожку',
                'звуковая дорожка': 'звуковую дорожку', лист: 'лист' }[THING];
  const title = { internal: `Не удалось собрать ${VIN}`,
                  network: 'Нет связи с генератором' }[res.kind]
                || `Такой ${THING} не собирается`;
  $('stage').classList.add('is-msg');
  const wrap = el('div', 'engine-error' + (res.kind === 'unsupported' ? ' calm' : ''));
  wrap.appendChild(el('h3', null,
    res.kind === 'unsupported'
      ? `${THING[0].toUpperCase()}${THING.slice(1)} на слоге ${curSyllable()} не делается`
      : title));
  // Текст уже переведён на человеческий на сервере — показываем как есть.
  wrap.appendChild(el('p', 'way-out', res.message));
  // Отказ по устройству материала — не тупик: рядом стоят слоги, на которых
  // этот материал собирается, и логопед переходит к ним одним нажатием.
  if (res.kind === 'unsupported' && (res.options || []).length) {
    wrap.appendChild(el('p', 'engine-said', 'Этот материал собирается так:'));
    const row = el('div', 'options');
    res.options.forEach((o) => {
      const b = el('button', 'seg-btn', o.syllable);
      b.title = o.label;
      b.addEventListener('click', () => {
        S.typ = o.typ;
        S.syllable = o.syllable;
        renderTabs();
        load();
      });
      row.appendChild(b);
    });
    wrap.appendChild(row);
  }
  if (res.kind === 'engine') {
    wrap.appendChild(el('p', 'engine-said', S.tab === 'maze'
      ? 'Смените позицию звука кнопками сверху или снимите один звук справа.'
      : 'Снимите один звук справа или возьмите другой слог. Подмешивать слова ' +
        'с трудными для ребёнка звуками генератор не станет.'));
  }
  box.appendChild(wrap);
  box.hidden = false;

  // Всё, что относилось к ПРОШЛОМУ листу, обязано уйти вместе с ним:
  // иначе на экране отказа остаются чужие числа рва и живая кнопка
  // «всё равно распечатать», которая печатает невидимый прошлый лист.
  // Настройки несобранного материала — из той же породы: выбирать фон у
  // дорожки, которой нет, логопеду нечего.
  $('moat-box').hidden = true;
  $('scene-card').hidden = true;
  $('game-card').hidden = true;
  $('text-card').hidden = true;
  $('theme-card').hidden = true;
  $('frame').style.visibility = 'hidden';
  $('frame').srcdoc = '';
  if ($('save')) $('save').disabled = true;
  $('warn').hidden = true;
  $('warn').innerHTML = '';
  $('moat').innerHTML = '';
}

/* ── лист в рамке ────────────────────────────────────────── */

function writeFrame(html) {
  // srcdoc, а не document.write: так рамка остаётся нормальным документом
  // (её видно в скриншотах и она корректно уходит в печать).
  const f = $('frame');
  // Правки логопеда живут до следующей ПЕРЕСБОРКИ листа. Сказать об этом
  // обязаны: молча стирать чужую работу — та же болезнь, что чинили 08-23,
  // только с другой стороны. Кубик рядом и есть «собрать заново», то есть
  // отмена правок уже существует и отдельной кнопки не требует.
  // Лист собран заново — прежние правки растворились вместе с документом.
  // Строки об этом на экране НЕТ по слову автора 08-24: экран настроек несёт
  // только необходимое, а кубик и есть «собрать заново» — логопед нажал его сам.
  S.edited = false;
  LAST_RANGE = null;
  f.onload = () => { makeEditable(f); editHint(f.contentDocument);
                     fitFrame(); setTimeout(fitFrame, 120); };
  f.srcdoc = html;
}

/* Лист правится ПРЯМО НА МЕСТЕ, без кнопки «режим правки».
   Зачем. Слово автора 08-24: «лист может быть на 95% хороший, и 5% будут всё
   портить». Логопед, который не может поправить эти 5%, не напечатает лист
   вовсе — проще собрать своё. Ставим ударение, убираем лишнее слово, вписываем
   своё — прямо в бумаге, которую видим.
   Почему без кнопки: печать идёт из ЭТОГО документа (`f.contentWindow.print()`),
   значит правка уходит в печать даром, а кубик рядом уже означает «собрать
   заново». Переключатель режима был бы третьей сущностью там, где хватает нуля
   (локальный закон 4). */
function makeEditable(f) {
  const d = f.contentDocument;
  if (!d || !d.body) return;
  d.body.contentEditable = 'true';
  d.body.spellcheck = false;
  // Курсор-текст только там, где текст: на пустом поле листа он сбивал бы с толку.
  const style = d.createElement('style');
  style.textContent = `
    body { caret-color: #2F6B4F; }
    [contenteditable] :focus { outline: 1px dashed #2F6B4F; outline-offset: 2px; }
    @media print { [contenteditable] :focus { outline: none !important; } }
  `;
  d.head.appendChild(style);
  d.addEventListener('input', () => { markEdited(d); }, { once: false });

  // Кнопка ударения появляется ТОЛЬКО когда курсор реально стоит в листе — это
  // и есть сигнал «с листом работают». Пока логопед смотрит, её нет: на экране
  // настроек лишних кнопок и слов быть не должно (закон 13, слово автора 08-24).
  //
  // ⚠ Кнопка не работала мышью, хотя работала в пробе кодом. Причин две сразу:
  // нажатие уводило фокус из рамки, и выделение внутри неё пропадало ДО того,
  // как срабатывал onclick. Поэтому последний курсор запоминаем на каждое
  // движение, а у самой кнопки гасим mousedown — фокус из листа не уходит вовсе.
  d.addEventListener('selectionchange', () => {
    const sel = d.getSelection();
    if (sel && sel.rangeCount && d.body.contains(sel.anchorNode)) {
      LAST_RANGE = sel.getRangeAt(0).cloneRange();
      showAccent(d, LAST_RANGE);
    } else {
      hideAccent(d);
    }
  });
  // ⚠ 2026-08-24. Плашка не уходила с листа после нажатия (поймал автор).
  // Причина: `selectionchange` живёт ВНУТРИ рамки, и когда логопед кликал
  // мимо — по панели или по вкладке, — курсор в рамке никуда не девался,
  // событие не приходило, и плашка висела. Ловим уход фокуса из самой рамки
  // и клик по родительской странице: снаружи листа плашке делать нечего.
  f.contentWindow.addEventListener('blur', () => hideAccent(d));
  if (!ACCENT_OUTSIDE) {
    ACCENT_OUTSIDE = true;
    document.addEventListener('mousedown', () => {
      const fr = $('frame');
      const dd = fr && fr.contentDocument;
      if (dd) hideAccent(dd);
    });
  }
}

/* Кнопка ударения живёт ВНУТРИ листа, у самого курсора.
   Слово автора 08-24: «ударение точно не должно располагаться на этой линии» —
   то есть не в ряду с печатью и кубиком. Там оно и правда чужое: печать и кубик
   про весь лист, а ударение — про одну букву под курсором. Он же назвал верное
   место раньше: «логичнее было бы где-то внутри листа рядом с курсором», и
   опасение «навязчиво висеть» снимается тем, что кнопки нет, пока нет курсора.
   Печати она не мешает: `@media print` её убирает. */
/* Намёк, что лист правится — ОДИН раз за сессию и без единого слова на экране
   настроек. Слово автора: «можно как-то бы намекнуть впервые пользователю, что
   можно редактировать — но ненавязчиво». Поэтому плашка живёт внутри листа,
   уходит от первого же прикосновения и больше не возвращается: узнал — забыли.
   В печать не идёт (`@media print`). */
let HINT_SHOWN = false;

function editHint(d) {
  if (HINT_SHOWN) return;
  HINT_SHOWN = true;
  const st = d.createElement('style');
  st.textContent = `
    #edit-hint { position: fixed; right: 10px; bottom: 10px; z-index: 8;
      font: 500 12px/1 -apple-system, system-ui, sans-serif;
      padding: 7px 11px; border-radius: 999px;
      background: rgba(35,35,31,.82); color: #fff;
      opacity: 0; transition: opacity .5s; pointer-events: none; }
    #edit-hint.on { opacity: 1; }
    @media print { #edit-hint { display: none !important; } }
  `;
  d.head.appendChild(st);
  const h = d.createElement('div');
  h.id = 'edit-hint';
  h.textContent = 'Текст на листе можно править';
  d.body.appendChild(h);
  const gone = () => { h.classList.remove('on'); setTimeout(() => h.remove(), 600); };
  setTimeout(() => h.classList.add('on'), 400);
  setTimeout(gone, 6000);
  d.addEventListener('mousedown', gone, { once: true });
}

function accentChip(d) {
  let c = d.getElementById('acc-chip');
  if (c) return c;
  const st = d.createElement('style');
  st.textContent = `
    #acc-chip { position: absolute; z-index: 9; transform: translate(-50%, -100%);
      font: 600 13px/1 -apple-system, system-ui, sans-serif;
      padding: 5px 9px; border: 1px solid #C9C0B4; border-radius: 7px;
      background: #fff; color: #23231F; cursor: pointer;
      box-shadow: 0 2px 6px rgba(0,0,0,.12); user-select: none; }
    #acc-chip:hover { border-color: #2F6B4F; color: #2F6B4F; }
    @media print { #acc-chip { display: none !important; } }
  `;
  d.head.appendChild(st);
  c = d.createElement('button');
  c.id = 'acc-chip';
  c.type = 'button';
  c.textContent = 'ударе\u0301ние';
  c.title = 'Поставьте курсор сразу после ударной гласной';
  // Гасим mousedown: иначе курсор в листе пропадёт раньше, чем сработает нажатие.
  c.addEventListener('mousedown', (e) => e.preventDefault());
  c.addEventListener('click', putAccent);
  d.body.appendChild(c);
  return c;
}

function showAccent(d, range) {
  const r = range.getBoundingClientRect();
  // Схлопнутый курсор в пустом узле даёт нулевой прямоугольник — берём слово.
  const box = (r.width || r.height) ? r
    : (range.startContainer.parentElement || d.body).getBoundingClientRect();
  const c = accentChip(d);
  c.style.left = (box.left + box.width / 2 + d.documentElement.scrollLeft) + 'px';
  c.style.top = (box.top - 6 + d.documentElement.scrollTop) + 'px';
  c.hidden = false;
}

function hideAccent(d) {
  const c = d.getElementById('acc-chip');
  if (c) c.hidden = true;
}

// Слушатель «клик мимо листа» вешается на родительскую страницу один раз:
// рамка перерисовывается на каждый лист, а документ живёт всю сессию.
let ACCENT_OUTSIDE = false;

// Где стоял курсор в листе в последний раз: нажатие на кнопку в панели — это
// клик ВНЕ рамки, и родное выделение к моменту обработчика уже не годится.
let LAST_RANGE = null;

/* Правка руками ЛОМАЕТ ОБЕЩАНИЕ ЛИСТА, и молчать об этом нельзя.
   Подвал рассказа говорит дословно: «Слова подобраны так, чтобы в них не было
   звуков, которые у ребёнка сейчас не получаются» (`rasskaz.py`). Как только
   логопед вписал своё слово, генератор за него не отвечает — а обещание
   остаётся напечатанным. Это ровно тот класс лжи, на котором 08-23 попались
   17 текстов из 31: материал утверждал больше, чем движок проверил.
   Поэтому первая же правка дописывает в подвал оговорку, и она уходит в печать
   вместе с листом. Один раз — повторно не добавляем. */
function markEdited(d) {
  if (S.edited) return;
  S.edited = true;
  const foot = d.querySelector('.foot');
  if (!foot) return;
  const note = d.createElement('div');
  note.className = 'hand-edit';
  note.style.cssText = 'margin-top:4px;font-style:italic';
  note.textContent = 'Лист правлен вручную: изменённое генератор не проверял.';
  foot.appendChild(note);
}

/* Ударение — комбинируемый акут U+0301: он «садится» на предыдущую букву,
   поэтому просто вставляется после неё. Работаем по ЗАПОМНЕННОМУ курсору. */
function putAccent() {
  const d = $('frame').contentDocument;
  if (!d || !LAST_RANGE) return;
  const r = LAST_RANGE.cloneRange();
  // ⚠ 2026-08-24. Здесь стояло `r.deleteContents()`, и при ВЫДЕЛЕННОМ фрагменте
  // ударение съедало выделенное слово целиком (поймал автор). Ударение ничего
  // не заменяет — оно ставится НА букву; поэтому выделение просто схлопываем
  // к его концу, к последней букве, над которой знак и должен встать.
  if (!r.collapsed) r.collapse(false);
  const node = d.createTextNode('\u0301');
  r.insertNode(node);
  r.setStartAfter(node);
  r.collapse(true);
  const sel = d.getSelection();
  sel.removeAllRanges();
  sel.addRange(r);
  LAST_RANGE = r.cloneRange();
  markEdited(d);
}

function fitFrame() {
  const f = $('frame');
  const d = f.contentDocument;
  if (!d || !d.documentElement) return;

  const stage = $('stage');
  const paper = document.querySelector('.paper');
  const wrap = document.querySelector('.result');
  // Отступы берём из стилей, а не зашитым числом: они разные на разных
  // ширинах, и на 1000px лист вылезал за колонку и обрезался.
  const cs = getComputedStyle(stage);
  const pad = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
  const padY = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);

  const h = Math.max(d.documentElement.scrollHeight, d.body ? d.body.scrollHeight : 0);
  if (!h) return;
  f.style.height = h + 'px';

  // ЛИСТ ЦЕЛИКОМ, БЕЗ ПРОКРУТКИ — решение автора 08-22: «не хочу, чтобы лист
  // уходил под скролл; по умолчанию лист должен занимать центральное и
  // максимально оптимизированное пространство, и относительно него строится
  // весь интерфейс».
  //
  // Поэтому масштаб считается по ДВУМ пределам сразу, а не по одной ширине:
  //   · сколько высоты осталось до низа окна;
  //   · сколько ширины мы согласны отдать листу (остальное — панели).
  // Раньше k считался только из ширины колонки, и лист высотой A4 неизбежно
  // уходил вниз за экран.
  //
  // Ширину листу считаем от ОКНА, а не от его собственной колонки: колонка
  // теперь подстраивается под лист, и брать её ширину значило бы гоняться за
  // собственным хвостом.
  const top = stage.getBoundingClientRect().top;
  // Высоту берём до самого низа окна: верхней полосы больше нет, отступы сняты,
  // и каждый оставшийся пиксель — это размер листа.
  const availH = window.innerHeight - top - 4 - padY;
  // Ширину даёт САМА колонка: она средняя из трёх и уже посчитана раскладкой
  // (закладки слева фиксированы, панель справа ограничена сверху). Гоняться за
  // собственным хвостом больше не приходится.
  const col = paper ? paper.parentElement : null;
  const availW = (col ? col.clientWidth : window.innerWidth) - pad;

  if (availH <= 0 || availW <= 0) return;

  const k = Math.min(1, availW / 794, availH / h);
  const sc = $('scaler');
  sc.style.transformOrigin = 'top left';
  sc.style.transform = `scale(${k})`;
  sc.style.marginLeft = '0px';
  stage.style.height = (h * k + padY) + 'px';
  // Ширина листа — ровно по бумаге; лишнее место в колонке раскладка отдаёт
  // отступам слева и справа, центрируя лист.
  if (paper) paper.style.width = (794 * k + pad) + 'px';
}

window.addEventListener('resize', fitFrame);

/* Ширина колонки меняется не только от resize окна: от зума, от появления
   полосы прокрутки, от переключения вкладок. Следим за самой колонкой —
   так лист не может остаться обрезанным. */
if (window.ResizeObserver) {
  new ResizeObserver(() => fitFrame()).observe(document.documentElement);
}

/* ── ров: пересчёт на глазах ─────────────────────────────── */



function renderMoat(st) {
  const box = $('moat');
  box.innerHTML = '';
  const label = S.cfg.sounds.find((x) => x.key === S.sound).label;

  if (st.kind === 'maze') { renderMazeMoat(box, st, label); return; }
  if (st.kind === 'rasskaz') {
    box.appendChild(el('h2', null, 'Рассказ для пересказа'));
    const p = el('p', 'hint',
      `«${st.title}»: ${st.sentences} ${plural(st.sentences, 'предложение', 'предложения', 'предложений')}, ` +
      `${st.words} ${plural(st.words, 'слово', 'слова', 'слов')}, ` +
      `со звуком [${label}] — ${Math.round(st.share * 100)} % слов.`);
    p.style.margin = '0 0 10px';
    box.appendChild(p);
    box.appendChild(el('p', 'hint',
      'Текст проверен движком: в нём нет звуков, которые у ребёнка не ' +
      'получаются. Плотность звука выше обычной речи — так и задумано ' +
      '(Волкова, Шаховская): это материал ступени закрепления.'));
    S.prev = null;
    return;
  }
  if (st.kind === 'story') {
    box.appendChild(el('h2', null, 'Сочини рассказ'));
    const p = el('p', 'hint',
      `Тема «${st.theme}»: ${st.n_sets} набора по 3-4 слова на звук [${label}]. ` +
      'Все чисты для этого ребёнка.');
    p.style.margin = '0 0 10px';
    box.appendChild(p);
    box.appendChild(el('p', 'hint',
      'Три-четыре слова в наборе и три вопроса в плане — числа не наши: ' +
      'так их задают Глухов и Пеньевская. Готового текста нет намеренно: ' +
      'рассказ сочиняет ребёнок, а движок ручается за чистоту только своих ' +
      'слов, не связного текста.'));
    S.prev = null;
    return;
  }
  if (st.kind === 'phrases') {
    box.appendChild(el('h2', null, 'Словосочетания'));
    const p = el('p', 'hint',
      `${st.n} пар «прилагательное + существительное» на звук [${label}]. ` +
      'Ступень между словом и фразой: звук надо удержать в двух словах подряд.');
    p.style.margin = '0 0 10px';
    box.appendChild(p);
    box.appendChild(el('p', 'hint',
      'Тип задания и его объём — Спивак Е.Н. (ГНОМ): пункт «Повтори ' +
      'словосочетания» стоит во всех десяти разделах пособия, 9–12 пар. ' +
      'Речевой материал наш: и прилагательное, и существительное прошли ' +
      'фильтр по профилю ребёнка.'));
    box.appendChild(el('p', 'hint',
      'Сочетаемость («деревянный стул» можно, «деревянный суп» нельзя) взята ' +
      'из выверенной руками таблицы, а не из правила по категории: правило ' +
      'здесь врёт.'));
    return;
  }
  if (st.kind === 'propisi') {
    box.appendChild(el('h2', null, 'Звуковая дорожка'));
    const iso = st.mode === 'isolated';
    const p = el('p', 'hint',
      (iso ? 'только звук' : `слог ${st.syllable.toUpperCase()}`) +
      ` · ${st.rows} дорожки: ` + st.tasks.join(' → '));
    p.style.margin = '0 0 10px';
    box.appendChild(p);
    // Текст обязан описывать ТО, что нарисовано: линия задаёт задачу голосу
    // (✅ Попова 2022), а не длину выдоха.
    box.appendChild(el('p', 'hint',
      (iso
        ? 'Гласной в конце нет: ребёнок ведёт по линии и тянет один звук. '
        : 'Слог на всех трёх дорожках ОДИН. ') +
      'Меняется задача голосу, и её задаёт форма линии: ровная — тянуть ' +
      'слитно, с подъёмами — вести голос выше и ниже, прерывистая — ' +
      'произносить отрывисто.'));
    S.prev = null;
    return;
  }
  if (st.kind === 'track') {
    box.appendChild(el('h2', null, 'Слоговая дорожка'));
    const p = el('p', 'hint',
      `${st.cells} кружков · ${st.type_label} · гласные ` +
      st.vowels.map((v) => v.toUpperCase()).join(' · '));
    p.style.margin = '0 0 10px';
    box.appendChild(p);
    // Пояснение «ребёнок ведёт пальцем по тропе…» снято 08-23 по слову автора:
    // то же самое напечатано НА САМОМ ЛИСТЕ инструкцией взрослому, и панель
    // повторяла его вторым домом.
    S.prev = null;
    return;
  }

  box.appendChild(el('h2', null, 'Из чего собран этот лист'));

  const t = el('table', 'ledger');
  const rows = [];

  const row = (cls, name, why, num, key) => {
    const tr = el('tr', cls);
    const td = el('td');
    td.append(name);
    if (why) td.appendChild(el('span', 'why', why));
    tr.appendChild(td);
    tr.appendChild(el('td', 'n', num));
    if (key && S.prev && S.prev[key] !== undefined && S.prev[key] !== st[key]) {
      tr.classList.add('flash');
    }
    rows.push(tr);
    return tr;
  };

  row('', `Картотека [${label}]`, null, st.dict_total, 'dict_total');

  // из объяснения убираем и цель, и её мягкую пару: [р'] отсеян не потому,
  // что «путается с [р]», а потому что это другой звук — врать нельзя
  const mixed = st.base_banned.filter((p) => p !== S.sound && p !== S.sound + "'");
  if (st.base_removed > 0) {
    row('cut', 'Убрали сразу',
        `в этих словах ${listLabels(mixed)} — их с [${label}] путают`,
        '−' + st.base_removed, 'base_removed');
  } else {
    row('muted', 'Убирать сразу нечего',
        `картотека [${label}] с самого начала собрана без ${listLabels(mixed)}`,
        '0', 'base_removed');
  }

  row('sum', 'Подходит для листа', null, st.base_clean, 'base_clean');

  if (S.profile.size) {
    row('cut', 'Не получаются у ребёнка',
        listLabels([...S.profile]) + ' — слова с ними убраны',
        '−' + st.profile_removed, 'profile_removed');
    row('final', 'Осталось ребёнку', null, st.left, 'left');
  }

  row('muted', 'На этот лист попало', null, st.on_sheet, 'on_sheet');

  rows.forEach((r) => t.appendChild(r));
  box.appendChild(t);

  if (!S.profile.size) {
    const p = el('p', 'hint',
      '');
    p.style.margin = '10px 0 0';
    box.appendChild(p);
  }

  S.prev = Object.assign({}, st);
}

/* У дорожки своя арифметика: она отбирает слова по ПОЗИЦИИ звука и по тому,
   можно ли слово нарисовать. Показывать здесь числа словаря листа — врать:
   они не менялись бы при смене позиции, хотя слова в клетках меняются целиком. */
function renderMazeMoat(box, st, label) {
  box.appendChild(el('h2', null, 'Из чего собрана эта дорожка'));
  const t = el('table', 'ledger');
  const rows = [];
  const row = (cls, name, why, num, key) => {
    const tr = el('tr', cls);
    const td = el('td');
    td.append(name);
    if (why) td.appendChild(el('span', 'why', why));
    tr.appendChild(td);
    tr.appendChild(el('td', 'n', num));
    if (key && S.prev && S.prev[key] !== undefined && S.prev[key] !== st[key]) {
      tr.classList.add('flash');
    }
    rows.push(tr);
  };

  row('', `Картотека [${label}]`, null, st.dict_total, 'dict_total');
  row('cut', 'Звук в другом месте слова', 'нужен ' + st.position_label,
      '−' + st.rejected_position, 'rejected_position');
  if (st.rejected_purity) {
    row('cut', 'Не подошли по звукам',
        S.profile.size ? 'есть ' + listLabels([...S.profile]) + ' или звуки, которые с целевым путают'
                       : 'есть звуки, которые с целевым путают',
        '−' + st.rejected_purity, 'rejected_purity');
  }
  row('sum', 'Годятся для дорожки', null, st.fit_position, 'fit_position');
  row('muted', 'В дорожке картинок', null, st.pictures, 'pictures');

  rows.forEach((r) => t.appendChild(r));
  box.appendChild(t);
  S.prev = Object.assign({}, st);
}

/* ТРИ СПИСКА ЗВУКОВ БЫЛИ ОДНИМ ЯЗЫКОМ — и читались как бред (поймано 08-06):
   · серые чипы            = что УЖЕ убрано автоматически (смешивается с целью)
   · ров «убрали сразу»    = то же самое, но с мягкими парами
   · «обратите внимание»   = совсем другое: буквы в НАЗВАНИЯХ упражнений
   Теперь у серых чипов стоит подпись, объясняющая, почему они серые, — иначе
   логопед видит «нельзя выбрать» и не понимает причины. */
function renderChips() {
  const box = $('chips');
  box.innerHTML = '';
  const base = new Set(S.cfg.sounds.find((x) => x.key === S.sound).stats.base_banned);
  const label = S.cfg.sounds.find((x) => x.key === S.sound).label;
  const off = S.cfg.profile_options
    .filter((o) => o.key !== S.sound && base.has(o.key))
    .map((o) => o.label);
  const note = $('chips-note');
  if (note) {
    note.textContent = off.length
      // Хвост «поэтому слов с ними на листе нет в любом случае» снят 08-22 по
      // слову автора: он повторял то же самое второй раз другими словами.
      ? `${off.join(', ')} — уже убраны: их путают с [${label}].`
      : '';
    note.hidden = !off.length;
  }

  S.cfg.profile_options.forEach((o) => {
    if (o.key === S.sound) return;                    // цель не предлагаем
    const b = el('button', 'chip', o.label);
    if (base.has(o.key)) {
      b.disabled = true;
      b.title = `уже убрано: [${o.label}] смешивается с [${label}]`;
    } else {
      b.classList.toggle('is-on', S.profile.has(o.key));
      b.onclick = () => {
        if (S.profile.has(o.key)) S.profile.delete(o.key);
        else S.profile.add(o.key);
        S.sheetNo = 1;
        forgetPicks();
        renderChips();
        load();
      };
    }
    box.appendChild(b);
  });
}

/* ── предупреждения движка ───────────────────────────────── */

function renderWarnings(w) {
  const box = $('warn');
  box.innerHTML = '';
  const blocking = (w && w.blocking) || [];
  const notes = (w && w.notes) || [];

  if ($('save')) $('save').disabled = false;

  if (!blocking.length && !notes.length) { box.hidden = true; return; }
  box.hidden = false;

  if (blocking.length) {
    const d = el('div', 'block-box');
    d.appendChild(el('h3', null, 'Этот лист лучше не печатать'));
    const ul = el('ul');
    blocking.forEach((x) => ul.appendChild(el('li', null, x)));
    d.appendChild(ul);
    // Решение всё равно за логопедом — но с названной причиной, а не молча.
    const anyway = el('button', 'btn ghost small', 'всё равно распечатать');
    anyway.onclick = () => { if ($('save')) $('save').disabled = false; savePdf(); };
    d.appendChild(anyway);
    box.appendChild(d);
    if ($('save')) $('save').disabled = true;
  }

  if (notes.length) {
    const d = el('div', 'note-box');
    d.appendChild(el('h3', null, notes.length > 1
      ? `Обратите внимание (${notes.length})` : 'Обратите внимание'));
    const ul = el('ul');
    notes.forEach((x) => ul.appendChild(el('li', null, x)));
    d.appendChild(ul);
    box.appendChild(d);
  }
}

/* ── действия ────────────────────────────────────────────── */

/* СКАЧАТЬ ЛИСТ.
   Слово автора 08-24: «сохранить в PDF ценнее намного, чем распечатать» —
   логопед готовит материал заранее, а печатает потом и не всегда там же.

   PDF собирает СЕРВЕР через Gotenberg (см. `server.to_pdf`): браузер не даёт
   выбрать «Сохранить как PDF» программно, а служба автора печатает тем же
   Chromium, что и браузер, — вёрстка остаётся одна на всё.

   Word (.doc с HTML внутри) оставлен вторым пунктом: формат он держит плохо,
   и это сказано автору прямо; годится, когда надо доправить текст в привычном
   редакторе, а не печатать.

   HTML всегда берём из РАМКИ, а не пересобираем на сервере: в рамке живут
   правки логопеда, и уходить в файл они обязаны вместе с листом. */
function sheetHtml() {
  const d = $('frame').contentDocument;
  return (d && d.documentElement) ? d.documentElement.outerHTML : '';
}

function download(blob, ext) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = saveName() + '.' + ext;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}

async function savePdf() {
  const html = sheetHtml();
  if (!html) return;
  const btn = $('save');
  const was = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Собираем…';
  try {
    const r = await fetch('/api/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ html }),
    });
    if (!r.ok || (r.headers.get('Content-Type') || '').indexOf('pdf') < 0) {
      let msg = '';
      try { msg = (await r.json()).message; } catch (e) { msg = ''; }
      showError({ kind: 'network', message: msg
        || 'PDF сейчас не собрать. Лист никуда не делся — сохраните его в Word '
         + 'или через окно печати.' });
      return;
    }
    download(await r.blob(), 'pdf');
  } catch (e) {
    showError({ kind: 'network',
                message: 'Не дозвонились до службы печати. Лист на месте — '
                       + 'сохраните его в Word или через окно печати.' });
  } finally {
    btn.disabled = false;
    btn.textContent = was;
  }
}

/* ── ЛИСТ → WORD ──────────────────────────────────────────────────────
   Word почти не понимает CSS-сетку и колонки: всё, что у нас разложено
   `display:grid` и `column-count`, он сваливает в один столбик — слово автора
   08-24: «ворд не держит строки, все списком уходит».
   Таблицы он держит хорошо и держал всегда. Поэтому перед выгрузкой мы
   перекладываем сеточные блоки в настоящие `<table>` — на КОПИИ документа,
   так что на экране и в PDF ничего не меняется.
   Это не второй отрисовщик: перекладывается расположение, а не содержимое. */

/* Сколько колонок у сеточного блока — спрашиваем у самого браузера, а не
   вычитываем из разметки: он уже посчитал `repeat(N,1fr)` за нас. */
function gridCols(el) {
  const t = getComputedStyle(el).gridTemplateColumns;
  const n = (t && t !== 'none') ? t.trim().split(/\s+/).length : 0;
  return n || el.children.length || 1;
}

/* Сетка → таблица. `byColumn` для `column-count`: там поток идёт СВЕРХУ ВНИЗ по
   первой колонке, потом по второй, а не слева направо. */
function toTable(doc, el, cols, byColumn) {
  const kids = [...el.children];
  if (!kids.length) return;
  const rows = Math.ceil(kids.length / cols);
  const t = doc.createElement('table');
  t.setAttribute('width', '100%');
  t.setAttribute('cellspacing', '0');
  t.setAttribute('cellpadding', '0');
  t.style.borderCollapse = 'collapse';
  for (let r = 0; r < rows; r++) {
    const tr = doc.createElement('tr');
    for (let c = 0; c < cols; c++) {
      const i = byColumn ? (c * rows + r) : (r * cols + c);
      const td = doc.createElement('td');
      td.setAttribute('valign', 'top');
      td.style.width = Math.floor(100 / cols) + '%';
      td.style.paddingRight = '4mm';
      if (kids[i]) td.appendChild(kids[i]);
      tr.appendChild(td);
    }
    t.appendChild(tr);
  }
  el.textContent = '';
  el.appendChild(t);
}

function wordHtml() {
  const src = $('frame').contentDocument;
  if (!src || !src.documentElement) return '';
  const doc = src.cloneNode(true);
  // Считать колонки надо по ЖИВОМУ документу: у копии нет вёрстки, и
  // getComputedStyle вернул бы пустоту.
  const live = [...src.querySelectorAll('.wcols, .game, .sent')];
  const copy = [...doc.querySelectorAll('.wcols, .game, .sent')];
  copy.forEach((el, i) => toTable(doc, el, gridCols(live[i] || el), false));
  // Ряд слогов: у него `column-count: 2`, поток по колонкам.
  doc.querySelectorAll('.syl').forEach((el) => toTable(doc, el, 2, true));
  // Флексы — просто строки: сколько детей, столько ячеек.
  doc.querySelectorAll('.artic, .ticks, .doc-row').forEach((el) => {
    toTable(doc, el, el.children.length || 1, false);
  });
  // Сами правила сетки в стилях остаются — Word их не понимает и просто
  // пропустит, но в браузере они бы спорили с таблицей. Гасим их одной
  // припиской: расположение теперь несёт таблица, а не сетка.
  const off = doc.createElement('style');
  off.textContent = '.wcols,.game,.sent,.artic,.ticks,.doc-row'
    + '{display:block !important}'
    + '.syl{column-count:1 !important}'
    + 'table{border-collapse:collapse}';
  doc.head.appendChild(off);
  return '<html xmlns:o="urn:schemas-microsoft-com:office:office" '
    + 'xmlns:w="urn:schemas-microsoft-com:office:word" '
    + 'xmlns="http://www.w3.org/TR/REC-html40">'
    + doc.documentElement.innerHTML + '</html>';
}

function saveDoc() {
  const html = wordHtml();
  if (!html) return;
  download(new Blob(['\ufeff', html],
    { type: 'application/msword;charset=utf-8' }), 'doc');
}

/* Имя файла — по-человечески: «занятие-Р», «слоговая-дорожка-Рь». Логопед
   складывает листы в папку, и «list(3).pdf» ему там не поможет. */
function saveName() {
  const mat = { sheet: 'занятие', propisi: 'звуковая-дорожка',
                track: 'слоговая-дорожка', phrases: 'словосочетания',
                maze: 'лабиринт', story: 'рассказ' }[S.tab] || 'лист';
  const snd = (soundLabel() || '').replace(/\s+/g, '');
  return snd ? mat + '-' + snd : mat;
}

function doPrint() {
  const f = $('frame');
  f.contentWindow.focus();
  f.contentWindow.print();
}

/* ── методика по кнопке ──────────────────────────────────── */

let METHOD = null;

async function openMethod() {
  if (!METHOD) {
    try {
      METHOD = await (await fetch('/api/method')).json();
    } catch (e) {
      METHOD = null;
      return;
    }
  }
  // ⚠ 2026-08-23. renderMethod() стоял ВНУТРИ `if (!METHOD)` — то есть справка
  // рисовалась один раз, на той вкладке, где ящик открыли первым, и дальше
  // замерзала. Логопед на «Лабиринте» читал устройство листа и не мог понять,
  // почему написано не про то. Справка своя на каждой вкладке — значит и
  // рисоваться обязана на каждое открытие, а не на первое.
  renderMethod();
  $('method-back').hidden = false;
  $('method-drawer').hidden = false;
  $('method-drawer').scrollTop = 0;
  document.body.style.overflow = 'hidden';
}

function closeMethod() {
  $('method-back').hidden = true;
  $('method-drawer').hidden = true;
  document.body.style.overflow = '';
}

const TIER_CLASS = { '✅': 't-book', '🔶': '', '⚠': 't-ours', '❓': 't-open' };

function renderMethod() {
  // Справка СВОЯ на каждой вкладке: лист объясняет лист, дорожка — дорожку.
  // Показывать логопеду устройство листа, когда он смотрит дорожку, — то же
  // самое, что не показывать ничего.
  const pack = (METHOD.by_tab || {})[S.tab] || (METHOD.by_tab || {}).sheet || {};

  const legend = $('method-legend');
  legend.innerHTML = '';
  // Счётчиков «✅ 24 · ⚠ 14» здесь нет намеренно: логопеду нужна пометка у
  // конкретной строки, а не арифметика по всей справке.
  (METHOD.tiers || []).forEach((t) => {
    legend.appendChild(el('span', null, t.tier + ' ' + t.label));
  });

  const title = $('method-title');
  if (title) title.textContent = pack.title || 'Как это устроено';

  const body = $('method-body');
  body.innerHTML = '';
  (pack.sections || []).forEach((sec) => {
    const s2 = el('section', 'method-sec');
    const h = el('h3');
    if (sec.num) h.appendChild(el('span', 'n', sec.num));
    h.append(sec.title);
    s2.appendChild(h);
    sec.rules.forEach((r) => {
      const d = el('div', 'method-rule ' + (TIER_CLASS[r.tier] || ''));
      const p = el('div', 'txt');
      p.appendChild(el('span', 'tag', r.tier));
      p.append(r.text);
      d.appendChild(p);
      if (r.source) d.appendChild(el('span', 'src', r.source));
      s2.appendChild(d);
    });
    body.appendChild(s2);
  });
}


function bindActions() {
  $('method-open').onclick = openMethod;
  $('method-close').onclick = closeMethod;
  $('method-back').onclick = closeMethod;
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !$('method-drawer').hidden) closeMethod();
  });

  // Обе кнопки открывают ОДНО окно печати: выбрать в нём принтер или «Сохранить
  // как PDF» может только человек — предвыбрать программно нельзя ни в одном
  // браузере. Имена и иконки разные потому, что логопед ищет глазами то, что
  // хочет получить; окно у этого одно, и об этом сказано в подсказке кнопки.
  // Кнопка одна и называется «Печать» — честно. Отдельная «Сохранить в PDF»
  // была бы ложью: предвыбрать PDF в окне печати программно нельзя ни в одном
  // браузере, и обе кнопки открывали бы одно и то же окно. Про PDF сказано в
  // подсказке кнопки — там это не занимает места на экране.
  $('save').onclick = savePdf;
  const more = $('save-more');
  const menu = $('save-menu');
  if (more && menu) {
    // ⚠ Список форматов ПЕРЕЕЗЖАЕТ В BODY. У панели настроек `overflow:auto`,
    // и выпадающий список, лежа внутри неё, обрезался её краем — открывался и
    // был не виден. Позиция считается от кнопки при каждом открытии.
    document.body.appendChild(menu);
    menu.style.position = 'fixed';
    const place = () => {
      const r = more.getBoundingClientRect();
      menu.style.top = (r.bottom + 6) + 'px';
      menu.style.left = 'auto';
      menu.style.right = (window.innerWidth - r.right) + 'px';
    };
    const close = () => {
      menu.hidden = true;
      more.setAttribute('aria-expanded', 'false');
    };
    more.onclick = (e) => {
      e.stopPropagation();
      if (menu.hidden) { place(); menu.hidden = false;
                         more.setAttribute('aria-expanded', 'true'); }
      else close();
    };
    menu.onclick = (e) => {
      const b = e.target.closest('button[data-fmt]');
      if (!b) return;
      close();
      ({ pdf: savePdf, doc: saveDoc, print: doPrint }[b.dataset.fmt] || savePdf)();
    };
    // Закрываем по клику МИМО — но не по клику в саму кнопку и не в список.
    document.addEventListener('click', (e) => {
      if (menu.hidden) return;
      if (e.target.closest('#save-menu') || e.target.closest('#save-more')) return;
      close();
    });
    window.addEventListener('resize', () => { if (!menu.hidden) place(); });
  }
  $('reroll').onclick = () => { S.sheetNo += 1; load(); };
  // возврат к выбору слога живёт в крошке «слог РА» сверху — отдельной
  // кнопки для того же действия больше нет

  // Дверь к материалу ОДНА. Прежде вкладка выставляла S.tab руками, а карточка
  // ступени звала pickMaterial — и один материал открывался в двух разных
  // состояниях: pickMaterial переустанавливает цвет, слог, номер сборки и игры,
  // а обработчик вкладки не трогал ничего. Через карточку лабиринт выходил
  // цветным, через вкладку чёрно-белым (поймано разбором 08-22). Теперь обе
  // двери ведут в одну комнату.
  document.querySelectorAll('.tab').forEach((b) => {
    b.onclick = () => pickMaterial({ tab: b.dataset.tab, soon: !!b.dataset.soon });
  });

  $('colour-btn').onclick = () => {
    S.colour = !S.colour;
    renderColour();
    load();
  };

  $('audience-btn').onclick = () => {
    S.audience = S.audience === 'home' ? 'lesson' : 'home';
    renderAudience();
    load();
  };

  $('propisi-mode-btn').onclick = () => {
    S.propisiMode = S.propisiMode === 'isolated' ? 'syllable' : 'isolated';
    S.vowel = null;
    renderPropisiMode();   // на изолированной ступени крошка «слог» уходит
    load();
  };

  $('story-mode-btn').onclick = () => {
    S.storyMode = S.storyMode === 'compose' ? 'retell' : 'compose';
    renderTabs();
    load();
  };
}

boot();

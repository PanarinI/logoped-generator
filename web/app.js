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
  audience: 'home', // куда лист: домой (с шапкой и подвалом) или на занятие
  scene: null,     // null = умолчание по персонажу, '' = логопед выбрал «без фона»
  propisiMode: 'syllable', // ступень звуковой дорожки: только звук / звук + слог
};

const $ = (id) => document.getElementById(id);
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
  renderCrumbs();
  bindActions();
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
  const box = $('sounds');
  box.innerHTML = '';
  S.cfg.sounds.forEach((s) => {
    const b = el('button', 'sound');
    b.appendChild(el('div', 'glyph', s.label));
    b.appendChild(el('div', 'meta',
      `${s.stats.dict_total} слов в картотеке`));
    b.onclick = () => { S.sound = s.key; show('syl'); renderSyls(); };
    box.appendChild(b);
  });
  $('sounds-note').textContent =
    'Это все звуки, которые умеет этот лист. Ц и Ч сюда не входят: их нельзя ' +
    'тянуть на одном выдохе, и порядок слогов у них обратный — им нужен ' +
    'другой лист. Смычные (П Б Т Д К Г) — по той же причине.';
}

/* ── шаг 2: слог ─────────────────────────────────────────── */

/* Подписи движка длинны для кнопки; режем только повтор, канонный термин
   «стечение» остаётся — своих синонимов не выдумываем. */
const SHORT_LABEL = {
  cluster_onset: 'стечение перед гласной',
  cluster_coda: 'стечение после гласной',
};

function renderSyls() {
  const box = $('syls');
  box.innerHTML = '';
  (S.cfg.syllables[S.sound] || []).forEach((t) => {
    const b = el('button', 'syl');
    b.disabled = !t.available;
    b.appendChild(el('div', 'glyph', t.syllable));
    b.appendChild(el('div', 'meta', SHORT_LABEL[t.typ] || t.label));
    b.onclick = () => {
      S.typ = t.typ;
      S.sheetNo = 1;
      S.profile.clear();
      S.prev = null;
      S.syllable = t.syllable;
      S.tab = 'sheet';
      $('ask').hidden = true;      // вопрос о профиле — после первого листа
      $('warn').hidden = true;
      $('moat').innerHTML = '';
      show('result');
      renderChips();
      renderAudience();
      renderTabs();
      load();
    };
    box.appendChild(b);
  });
}

/* ── навигация ───────────────────────────────────────────── */

function show(step) {
  ['sound', 'syl', 'result'].forEach((k) => {
    $('step-' + k).hidden = (k !== step);
  });
  // Переключатель инструментов живёт в верхней панели и имеет смысл только
  // тогда, когда материал уже собран.
  $('tools').hidden = (step !== 'result');
  renderCrumbs();
  // вернулись на экран листа — пересчитать масштаб: пока он был скрыт,
  // ширина сцены была нулевой и подгонка не работала
  if (step === 'result') requestAnimationFrame(fitFrame);
}

function renderCrumbs() {
  const c = $('crumbs');
  c.innerHTML = '';
  const add = (label, value, go) => {
    const b = el('button', 'crumb');
    b.append(label + ' ');
    const strong = el('b', null, value);
    b.appendChild(strong);
    b.onclick = go;
    if (c.children.length) c.appendChild(el('span', 'crumb-sep', '·'));
    c.appendChild(b);
  };
  if (S.sound) add('звук', S.cfg.sounds.find((x) => x.key === S.sound).label,
                   () => show('sound'));
  // На изолированной ступени слога нет вовсе — крошка «слог РА» была бы
  // обещанием того, чего на листе не напечатано. У словосочетаний слога нет
  // тем более: они собираются из слов, а не из слогов.
  const noSyllable = (S.tab === 'propisi' && S.propisiMode === 'isolated')
    || (S.tab === 'phrases');
  if (S.typ && !noSyllable && !$('step-result').hidden) {
    // слог берём из ОТВЕТА (S.syllable), а не из подписи кнопки: подписи
    // посчитаны на старте при пустом профиле, а профиль слог меняет —
    // «РША» на кнопке против «ФША» на листе, когда ребёнку убрали [Р]
    const t = S.cfg.syllables[S.sound].find((x) => x.typ === S.typ);
    add('слог', (S.syllable || t.syllable).toUpperCase(), () => show('syl'));
  }
}

/* ── шаг 3: материал ─────────────────────────────────────── */

function renderTabs() {
  document.querySelectorAll('.tab').forEach((b) => {
    b.classList.toggle('is-on', b.dataset.tab === S.tab);
  });
  $('tab-extra').hidden = (S.tab !== 'maze');
  $('maze-note').hidden = (S.tab !== 'maze');
  if (S.tab === 'maze') renderPositions();
  $('reroll').hidden = (S.tab !== 'sheet');
  // Профиль ребёнка меняет лист и лабиринт, но не дорожку и не прописи:
  // там нет слов, а слог по построению чист (целевой звук + гласная).
  $('ask').hidden = (S.tab === 'track') || (S.tab === 'propisi')
    || (S.tab === 'phrases') || !S.syllable;
  // «Домой / на занятие» — свойство ЛИСТА: шапка-документ и подвал взрослому
  // есть только у него. У дорожки и лабиринта их нет, переключать нечего.
  $('where').hidden = (S.tab !== 'sheet');
  // Ступень «только звук / звук + слог» есть лишь у звуковой дорожки.
  $('stage-step').hidden = (S.tab !== 'propisi');
  $('scene-card').hidden = (S.tab !== 'track');
  if (S.tab === 'track') renderScenePick();
  if (S.tab === 'propisi') renderPropisiMode();
  renderCrumbs();
  // Заголовок рва называет ТОТ материал, который сейчас на экране: «этот лист»
  // на прописях было бы неправдой — там не лист, а дорожки.
  $('moat-summary').textContent = {
    sheet:   'Из чего собран этот лист',
    track:   'Из чего собрана эта слоговая дорожка',
    propisi: 'Из чего собрана эта звуковая дорожка',
    phrases: 'Из чего собраны эти словосочетания',
    maze:    'Из чего собран этот лабиринт',
  }[S.tab] || 'Из чего это собрано';
}

function renderAudience() {
  document.querySelectorAll('#audience .seg-btn').forEach((b) => {
    b.classList.toggle('is-on', b.dataset.aud === S.audience);
  });
  $('audience-hint').textContent = S.audience === 'home'
    ? 'С шапкой на неделю и подписью родителя.'
    : 'Без шапки и подсказок взрослому — логопед рядом.';
}

function renderScenePick() {
  const box = $('scene-pick');
  if (box.dataset.built !== '1') {
    box.innerHTML = '';
    (S.cfg.scenes || []).forEach((sc) => {
      const b = el('button', 'seg-btn', sc.label);
      b.dataset.scene = sc.key;
      b.addEventListener('click', () => {
        if (S.scene === sc.key) return;
        S.scene = sc.key;
        renderScenePick();
        request();
      });
      box.appendChild(b);
    });
    box.dataset.built = '1';
  }
  box.querySelectorAll('.seg-btn').forEach((b) => {
    b.classList.toggle('is-on', S.scene !== null && b.dataset.scene === S.scene);
  });
}


function renderPropisiMode() {
  document.querySelectorAll('#propisi-mode .seg-btn').forEach((b) => {
    b.classList.toggle('is-on', b.dataset.mode === S.propisiMode);
  });
  $('propisi-mode-hint').textContent = S.propisiMode === 'isolated'
    ? 'Гласной в конце нет: ребёнок тянет один звук. Это ступень до слога.'
    : 'В конце линии гласная — собирается слог.';
}

function renderPositions() {
  const box = $('positions');
  box.innerHTML = '';
  S.cfg.positions.forEach((p) => {
    const b = el('button', 'pos' + (p.key === S.position ? ' is-on' : ''), p.label);
    b.onclick = () => { S.position = p.key; renderPositions(); load(); };
    box.appendChild(b);
  });
}

/* Каждому запросу — свой номер. Отвечает медленный сервер или логопед быстро
   щёлкает чипы — на экран попадает только ПОСЛЕДНИЙ запрошенный материал,
   а запросы не теряются. Раньше здесь стоял флаг busy, который просто ронял
   второй клик: чип горел, а лист оставался от прошлого профиля. */
let TICKET = 0;

async function load() {
  const my = ++TICKET;
  $('stage').classList.add('is-busy');
  $('print').disabled = true;          // пока летит — печатать нечего

  const profile = [...S.profile];
  let res;
  try {
    if (S.tab === 'track') {
      // Дорожка Ольги: слоги по тропе. Слов нет — профиль на неё не влияет,
      // слог по построению чист (целевой звук + гласная).
      res = await post('/api/track',
        { sound: S.sound, typ: S.typ, ...(S.scene === null ? {} : { scene: S.scene }) });
    } else if (S.tab === 'propisi') {
      // Прописи: линия + слог. Слов тоже нет — профиль не влияет.
      res = await post('/api/propisi',
        { sound: S.sound, typ: S.typ, mode: S.propisiMode });
    } else if (S.tab === 'phrases') {
      // Здесь профиль работает на ОБЕ части пары: и на существительное,
      // и на прилагательное. Тип слога на словосочетания не влияет.
      res = await post('/api/phrases', { sound: S.sound, profile: profile });
    } else if (S.tab === 'maze') {
      res = await post('/api/maze',
        { sound: S.sound, position: S.position, profile: profile });
    } else {
      res = await post('/api/sheet',
        { sound: S.sound, typ: S.typ, profile: profile, sheet_no: S.sheetNo,
          audience: S.audience });
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
  $('frame').style.visibility = 'visible';
  if (res.syllable) { S.syllable = res.syllable; renderCrumbs(); }
  writeFrame(res.html);
  renderMoat(res.stats);
  renderWarnings(res.warnings);   // она же решает, можно ли печатать
  // Вопрос о профиле — только ПОСЛЕ первого материала и только там, где он
  // на что-то влияет. На дорожке и в прописях слов нет, убирать нечего.
  $('ask').hidden = (S.tab === 'track') || (S.tab === 'propisi')
    || (S.tab === 'phrases');
}

function showError(res) {
  const box = $('stage-msg');
  box.innerHTML = '';
  const THING = { maze: 'лабиринт', track: 'дорожка',
                  propisi: 'звуковая дорожка',
                  phrases: 'словосочетания' }[S.tab] || 'лист';
  const VIN = { лабиринт: 'лабиринт', дорожка: 'дорожку',
                'звуковая дорожка': 'звуковую дорожку', лист: 'лист' }[THING];
  const title = { internal: `Не удалось собрать ${VIN}`,
                  network: 'Нет связи с генератором' }[res.kind]
                || `Такой ${THING} не собирается`;
  const wrap = el('div', 'engine-error');
  wrap.appendChild(el('h3', null, title));
  // Текст уже переведён на человеческий на сервере — показываем как есть.
  wrap.appendChild(el('p', 'way-out', res.message));
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
  $('frame').style.visibility = 'hidden';
  $('frame').srcdoc = '';
  $('print').disabled = true;
  $('warn').hidden = true;
  $('warn').innerHTML = '';
  $('moat').innerHTML = '';
}

/* ── лист в рамке ────────────────────────────────────────── */

function writeFrame(html) {
  // srcdoc, а не document.write: так рамка остаётся нормальным документом
  // (её видно в скриншотах и она корректно уходит в печать).
  const f = $('frame');
  f.onload = () => { fitFrame(); setTimeout(fitFrame, 120); };
  f.srcdoc = html;
}

function fitFrame() {
  const f = $('frame');
  const d = f.contentDocument;
  if (!d || !d.documentElement) return;

  const stage = $('stage');
  // Отступы берём из стилей, а не зашитым числом: они разные на разных
  // ширинах, и на 1000px лист вылезал за колонку и обрезался.
  const cs = getComputedStyle(stage);
  const pad = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
  const avail = stage.clientWidth - pad;
  // экран результата скрыт → ширина 0 → масштаб ушёл бы в минус и лист
  // остался бы зеркальным. Пересчитаем, когда экран снова покажут.
  if (avail <= 0) return;

  const h = Math.max(d.documentElement.scrollHeight, d.body ? d.body.scrollHeight : 0);
  f.style.height = h + 'px';

  // Масштабируем от ВЕРХНЕГО ЛЕВОГО угла и центрируем отступом. При origin
  // «top center» видимая коробка вылезала за колонку и лист обрезало справа.
  const k = Math.min(1, avail / 794);
  const sc = $('scaler');
  sc.style.transformOrigin = 'top left';
  sc.style.transform = `scale(${k})`;
  sc.style.marginLeft = Math.max(0, (avail - 794 * k) / 2) + 'px';
  stage.style.height = (h * k + pad) + 'px';
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
    box.appendChild(el('p', 'hint',
      'Ребёнок ведёт пальцем по тропе и называет каждый кружок. Слов здесь нет — ' +
      'значит и убирать нечего: слог состоит только из отрабатываемого звука и гласной.'));
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
      'Отметьте ниже, чего у ребёнка ещё нет — запас пересоберётся.');
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
      ? `${off.join(', ')} — уже убраны: их путают с [${label}], поэтому слов с ними на листе нет в любом случае.`
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

  $('print').disabled = false;

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
    anyway.onclick = () => { $('print').disabled = false; doPrint(); };
    d.appendChild(anyway);
    box.appendChild(d);
    $('print').disabled = true;
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
    renderMethod();
  }
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
  const legend = $('method-legend');
  legend.innerHTML = '';
  const c = METHOD.counts || {};
  METHOD.tiers.forEach((t) => {
    const s = el('span');
    s.appendChild(el('b', null, t.tier + ' ' + t.label));
    const n = c[t.tier];
    if (n != null) s.append(` — ${n}`);
    legend.appendChild(s);
  });

  const body = $('method-body');
  body.innerHTML = '';
  METHOD.sections.forEach((sec) => {
    const s = el('section', 'method-sec');
    const h = el('h3');
    if (sec.num) h.appendChild(el('span', 'n', sec.num));
    h.append(sec.title);
    s.appendChild(h);
    sec.rules.forEach((r) => {
      const d = el('div', 'method-rule ' + (TIER_CLASS[r.tier] || ''));
      const p = el('div', 'txt');
      p.appendChild(el('span', 'tag', r.tier));
      p.append(r.text);
      d.appendChild(p);
      if (r.source) d.appendChild(el('span', 'src', 'источник: ' + r.source));
      s.appendChild(d);
    });
    body.appendChild(s);
  });
}

function bindActions() {
  $('method-open').onclick = openMethod;
  $('method-close').onclick = closeMethod;
  $('method-back').onclick = closeMethod;
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !$('method-drawer').hidden) closeMethod();
  });

  $('print').onclick = doPrint;
  $('reroll').onclick = () => { S.sheetNo += 1; load(); };
  // возврат к выбору слога живёт в крошке «слог РА» сверху — отдельной
  // кнопки для того же действия больше нет

  document.querySelectorAll('.tab').forEach((b) => {
    b.onclick = () => { S.tab = b.dataset.tab; renderTabs(); load(); };
  });

  document.querySelectorAll('#audience .seg-btn').forEach((b) => {
    b.onclick = () => {
      if (S.audience === b.dataset.aud) return;
      S.audience = b.dataset.aud;
      renderAudience();
      load();
    };
  });

  document.querySelectorAll('#propisi-mode .seg-btn').forEach((b) => {
    b.onclick = () => {
      if (S.propisiMode === b.dataset.mode) return;
      S.propisiMode = b.dataset.mode;
      renderPropisiMode();
      renderCrumbs();   // на изолированной ступени крошка «слог» уходит
      load();
    };
  });
}

boot();

# -*- coding: utf-8 -*-
"""
phonetics.py — детерминированный фонетический движок русского слова
для логопедической картотеки (проект app-studio / LogoKonspekt).

Вход — ДВА ручных поля: word (строка кириллицей) и stress_syllable
(номер ударного слога, с 1). Всё остальное вычисляется.

Ключевой принцип канона: ФИЛЬТР РАБОТАЕТ ПО ЗВУКАМ, НЕ ПО БУКВАМ.
    мороз  -> [марос]   (содержит С, не З)
    ложка  -> [лошка]   (содержит Ш, не Ж)
    юбка   -> [йупка]   (содержит П и Й, не Б)
    морковка -> [маркофка] (содержит Ф, не В)
    матрёшка -> [матр'ошка] (содержит мягкий Рь, не твёрдый Р)

Классификация слоговой структуры — А.К. Маркова, версия V1 (14 типов,
портальный канон). НОМЕР ТИПА != ЧИСЛО СЛОГОВ.

Обозначения транскрипции (внутренний формат, не МФА):
    гласные:        а о у и ы э
    согласные:      буква + "'" для мягких парных (с', л', р', т' ...)
    ж ш ц           всегда твёрдые  — апострофа НЕ несут
    ч щ й           всегда мягкие   — апострофа НЕ несут (мягкость подразумевается)
Поле .soft у фонемы всегда несёт истину, независимо от написания ключа.

Публичный API:
    analyze(word, stress_syllable=None) -> Analysis
    select(words, target_phoneme, position=None, syl_types=None,
           exclude_phonemes=set(), markova_max=None, n=10) -> SelectionList
    describe(word, stress_syllable=None) -> str   (человекочитаемый разбор)

───────────────────────────────────────────────────────────────────────
ГДЕ ПРАВИЛА УПРОЩЕНЫ (честный список — здесь движок может ошибаться)
───────────────────────────────────────────────────────────────────────
1. РЕДУКЦИЯ ГЛАСНЫХ — двухступенчатая вместо трёхступенчатой. Реальный
   русский различает 1-й предударный [ʌ] и прочие безударные [ъ]/[ь];
   здесь всё безударное «о/а» -> а, всё безударное «е/я/э» -> и.
   «молоко» даст [малако] вместо [мълʌко]. Для отбора слов это неважно
   (гласные не корригируются), для печати транскрипции в продукте — важно.
2. АССИМИЛЯТИВНОЕ СМЯГЧЕНИЕ НЕ РЕАЛИЗОВАНО. «снег» -> [сн'эк], а не
   [с'н'эк]; «стена» -> [ст'ина], а не [с'т'ина]; «счастье» -> [щаст'йи],
   а не [щас'т'йэ]. Норма тут сама плавает, но если целевой звук — С/З,
   движок может назвать твёрдым тот С, который логопед слышит мягким.
   ЭТО САМАЯ ВЕРОЯТНАЯ ОШИБКА ДЛЯ СВИСТЯЩИХ.
3. НЕПРОИЗНОСИМЫЕ СОГЛАСНЫЕ — только по списку ORTHO_EXCEPTIONS
   (солнце, лестница, чувство, здравствуй, поздно, праздник, известный,
   местный, честный, грустный, звёздный, конечно, что, его, сегодня...).
   Слова вне списка обработаются буквально: «сверстник» останется со
   всеми согласными. Список расширяется руками.
4. Г -> В в окончаниях -ого/-его НЕ автоматизировано (иначе «много»
   станет [мнова]); работает только по списку исключений.
5. СЛОГОДЕЛЕНИЕ — по восходящей звучности (фонетический слог), не по
   переносу. «автобус» = [а-фто-бус], не «ав-то-бус»; «морковка» =
   [мар-ко-фка]. На число слогов и на классификацию Марковой это не
   влияет (там важны число гласных, число стечений и закрытость слова),
   влияет только на поле syllable_idx и на печать слогов.
6. «ЗАКРЫТОСТЬ» для классификатора = слово оканчивается согласным
   (ends_closed). Внутренние закрытые слоги отдельно не учитываются —
   в V1 они и не различаются, но это допущение, а не буква канона.
7. ТИП 3 принимает и односложные ОТКРЫТЫЕ слова («да», «но») — в V1
   для них слота нет; факт помечается в markova_notes.
8. ОДНОСЛОЖНОЕ СО СТЕЧЕНИЕМ И В НАЧАЛЕ, И В КОНЦЕ («хвост», «спорт»,
   «кнут»+«танк» вместе) даёт тип 12 + markova_conflict=True: в V1
   слота нет, у Марковой-1961 это отдельная строка 11.
9. ЧИСЛО СТЕЧЕНИЙ >= 2 всегда даёт «двойное» звено (13 для двусложных,
   10 для трёхсложных), даже если стечений три («здравствуйте»).
10. ЗАДНЕЯЗЫЧНЫЕ включены вместе с мягкими вариантами (к' г' х'),
   хотя канон перечисляет только [к г х]. Строже — значит безопаснее
   для фильтра чистоты.
11. ОППОЗИЦИЯ «с-ш» и «з-ж» проверяется и для мягких с'/з' (шире
   классической пары). Сознательно: фильтр чистоты должен пере-, а не
   недо-фильтровывать.
12. УДАРЕНИЕ ПРАВИЛАМИ НЕ ВЫВОДИТСЯ (кроме односложных и слов с «ё») —
   это ручное поле, как и записано в каноне.
13. ВОРОТА «ЛЕКСИКА» в select() — только формальные (кириллица, есть
   гласная, длина >= 2) либо явный словник через lexicon=. Смысловая
   пригодность слова для ребёнка остаётся ручным слоем.
14. Транскрипция — внутренняя нотация (кириллица + апостроф), не МФА.
   Долгота, [ə]/[ɨ]-оттенки, [ɣ], ассимиляция по месту образования
   (сшить=[ш:], отца=[ц:]) сведены к одному звуку без долготы.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

__all__ = [
    "analyze", "select", "describe", "Analysis", "Phoneme", "SelectionList",
    "MARKOVA_V1", "CORRIGIBLE", "PHONEME_CLASSES", "OPPOSITION_PAIRS",
]

# ═══════════════════════════════════════════════════════════════════════
#  1. АЛФАВИТ И ФОНОЛОГИЧЕСКИЕ КЛАССЫ
# ═══════════════════════════════════════════════════════════════════════

VOWEL_LETTERS: FrozenSet[str] = frozenset("аеёиоуыэюя")
YOTATED_LETTERS: FrozenSet[str] = frozenset("еёюя")      # дают [й]+гласный в сильной позиции
SOFTENING_LETTERS: FrozenSet[str] = frozenset("еёиюя")   # смягчают ПРЕДШЕСТВУЮЩИЙ согласный
SIGNS: FrozenSet[str] = frozenset("ьъ")
CONSONANT_LETTERS: FrozenSet[str] = frozenset("бвгджзйклмнпрстфхцчшщ")

ALWAYS_HARD: FrozenSet[str] = frozenset("жшц")   # непарные твёрдые
ALWAYS_SOFT: FrozenSet[str] = frozenset("чщй")   # непарные мягкие


def sound_label(sound: str) -> str:
    """Ключ фонемы -> подпись для ЧЕЛОВЕКА: «р'» -> «Рь», «ш» -> «Ш».

    Апостроф — наша внутренняя запись мягкости, она существует только в коде.
    Логопед и родитель пишут «Ль». Локальный закон проекта: на экране и на
    бумаге нет ни одного знака, которого нет у пользователя. Единственный дом
    этого правила — здесь; лист, дорожка и лабиринт зовут отсюда.
    """
    s = str(sound or "")
    return (s[:-1].upper() + "ь") if s.endswith("'") else s.upper()

SONORANT_LETTERS: FrozenSet[str] = frozenset("лмнрй")     # сонорные (не оглушаются, не ассимилируют)
VOICED_TO_VOICELESS: Dict[str, str] = {
    "б": "п", "в": "ф", "г": "к", "д": "т", "ж": "ш", "з": "с",
}
VOICELESS_TO_VOICED: Dict[str, str] = {v: k for k, v in VOICED_TO_VOICELESS.items()}
UNPAIRED_VOICELESS: FrozenSet[str] = frozenset("хцчщ")

# ── корригируемые фонемы (по канону Коноваленко) ────────────────────────
PHONEME_CLASSES: Dict[str, FrozenSet[str]] = {
    "свистящие":     frozenset({"с", "с'", "з", "з'", "ц"}),
    "шипящие":       frozenset({"ш", "ж", "щ", "ч"}),
    "сонорные":      frozenset({"л", "л'", "р", "р'", "й"}),
    "заднеязычные":  frozenset({"к", "к'", "г", "г'", "х", "х'"}),
}
CORRIGIBLE: FrozenSet[str] = frozenset().union(*PHONEME_CLASSES.values())

PHONEME_CLASS_OF: Dict[str, str] = {
    ph: cls for cls, phs in PHONEME_CLASSES.items() for ph in phs
}

# ── оппозиционные пары (смешиваемые звуки) ──────────────────────────────
# Задаются множествами фонем: пара срабатывает, если в слове есть хотя бы
# по одному представителю каждой стороны.
OPPOSITION_PAIRS: List[Tuple[str, FrozenSet[str], FrozenSet[str]]] = [
    ("р-л",  frozenset({"р", "р'"}), frozenset({"л", "л'"})),
    ("с-ш",  frozenset({"с", "с'"}), frozenset({"ш"})),
    ("з-ж",  frozenset({"з", "з'"}), frozenset({"ж"})),
    ("с-з",  frozenset({"с", "с'"}), frozenset({"з", "з'"})),
    ("ш-ж",  frozenset({"ш"}),       frozenset({"ж"})),
    ("с-ц",  frozenset({"с", "с'"}), frozenset({"ц"})),
    ("ч-ть", frozenset({"ч"}),       frozenset({"т'"})),
    ("щ-сь", frozenset({"щ"}),       frozenset({"с'"})),
]

# ── таблица Марковой V1 ─────────────────────────────────────────────────
MARKOVA_V1: Dict[int, str] = {
    1:  "двусложные открытые (вата, муха)",
    2:  "трёхсложные открытые (малина, собака)",
    3:  "односложные закрытые (мак, дом)",
    4:  "двусложные с закрытым слогом (лимон, петух)",
    5:  "двусложные со стечением в середине (банка, юбка)",
    6:  "двусложные с закрытым слогом и стечением (компот, чайник)",
    7:  "трёхсложные с закрытым слогом (телефон, бегемот)",
    8:  "трёхсложные со стечением (комната, яблоко)",
    9:  "трёхсложные со стечением и закрытым слогом (автобус, апельсин)",
    10: "трёхсложные с двумя стечениями (матрёшка, морковка)",
    11: "односложные со стечением в начале (стол, флаг)",
    12: "односложные со стечением в конце (зонт, бант)",
    13: "двусложные с двумя стечениями (кнопка, гнездо)",
    14: "четырёхсложные открытые (черепаха, пианино)",
}

_ORDINALS = ["first", "second", "third", "fourth", "fifth"]

# ═══════════════════════════════════════════════════════════════════════
#  2. ОРФОГРАФИЧЕСКАЯ ПРЕДОБРАБОТКА
# ═══════════════════════════════════════════════════════════════════════

# Непроизносимые согласные и прочие немодельные исключения.
# Значение — «фонетическое написание», которое дальше идёт через общий конвейер.
# ВАЖНО: замена НЕ должна менять число гласных букв (иначе поедет номер ударного слога).
ORTHO_EXCEPTIONS: Dict[str, str] = {
    # непроизносимые согласные
    "солнце": "сонце", "солнца": "сонца", "солнцем": "сонцем", "солнышко": "сонышко",
    "сердце": "серце", "сердца": "серца", "сердцем": "серцем",
    "лестница": "лесница", "лестницы": "лесницы",
    "чувство": "чуство", "чувства": "чуства",
    "здравствуй": "здраствуй", "здравствуйте": "здраствуйте",
    "поздно": "позно", "праздник": "празник", "праздники": "празники",
    "известный": "извесный", "местный": "месный", "честный": "чесный",
    "грустный": "грусный", "звёздный": "звёзный", "радостный": "радосный",
    "счастливый": "щасливый", "счастливо": "щасливо",
    "тростник": "тросник", "окрестность": "окресность",
    "гигантский": "гиганский", "голландский": "голланский",
    # чн -> шн
    "конечно": "конешно", "скучно": "скушно", "нарочно": "нарошно",
    "яичница": "яишница", "скворечник": "скворешник", "прачечная": "прачешная",
    # что / чтобы
    "что": "што", "чтобы": "штобы", "что-то": "што-то", "кое-что": "кое-што",
    # г -> в
    "его": "ево", "сегодня": "севодня", "него": "нево", "кого": "ково",
    "чего": "чево", "того": "тово", "этого": "этово",
}

# Диграфы: сочетания букв, дающие один звук.
DIGRAPH_RULES: List[Tuple[str, str]] = [
    ("сч", "щ"), ("зч", "щ"), ("жч", "щ"), ("шч", "щ"),
    ("сш", "шш"), ("зш", "шш"), ("сж", "жж"), ("зж", "жж"), ("жд", "жд"),
    ("ться", "ца"), ("тся", "ца"),
]

_DOUBLE_RE = re.compile(r"([бвгджзйклмнпрстфхцчшщ])\1")


def _preprocess(word: str) -> str:
    """Орфография -> «фонетическое написание» (ещё буквы, но уже без немых)."""
    w = word.strip().lower().replace("́", "")
    if not w:
        raise ValueError("пустое слово")
    if w in ORTHO_EXCEPTIONS:
        w = ORTHO_EXCEPTIONS[w]
    for src, dst in DIGRAPH_RULES:
        if src != dst:
            w = w.replace(src, dst)
    # удвоенные согласные = один звук
    prev = None
    while prev != w:
        prev = w
        w = _DOUBLE_RE.sub(r"\1", w)
    bad = [ch for ch in w if ch not in VOWEL_LETTERS and ch not in CONSONANT_LETTERS
           and ch not in SIGNS and ch != "-"]
    if bad:
        raise ValueError(f"недопустимые символы в слове {word!r}: {bad}")
    return w


# ═══════════════════════════════════════════════════════════════════════
#  3. ФОНЕМА
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Phoneme:
    symbol: str            # базовая буква звука после всех ассимиляций
    is_vowel: bool
    soft: bool = False
    stressed: bool = False  # только для гласных
    source_letter: str = ""  # буква-источник (для отладки)

    @property
    def key(self) -> str:
        """Строковый ключ фонемы: 'с', \"с'\", 'ш', 'ч' ..."""
        if self.is_vowel:
            return self.symbol
        if self.symbol in ALWAYS_HARD or self.symbol in ALWAYS_SOFT:
            return self.symbol
        return self.symbol + ("'" if self.soft else "")

    @property
    def is_consonant(self) -> bool:
        return not self.is_vowel

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "symbol": self.symbol,
            "is_vowel": self.is_vowel,
            "soft": self.soft,
            "stressed": self.stressed,
            "source_letter": self.source_letter,
        }


# ═══════════════════════════════════════════════════════════════════════
#  4. БУКВЫ -> ФОНЕМЫ
# ═══════════════════════════════════════════════════════════════════════

def _realize_vowel(letter: str, stressed: bool, prev_letter: Optional[str]) -> str:
    """Гласная буква -> гласный звук (аканье / иканье, ы после ж-ш-ц)."""
    after_hard_sibilant = prev_letter in ALWAYS_HARD if prev_letter else False
    after_hushing_soft = prev_letter in ("ч", "щ") if prev_letter else False

    if letter == "а":
        # часы -> [чисы], щавель -> [щив'эл']
        if not stressed and after_hushing_soft:
            return "и"
        return "а"
    if letter == "о":
        return "о" if stressed else "а"          # аканье
    if letter == "у":
        return "у"
    if letter == "ы":
        return "ы"
    if letter == "и":
        return "ы" if after_hard_sibilant else "и"   # жить -> [жыт'], цирк -> [цырк]
    if letter == "э":
        return "э" if stressed else "и"
    if letter == "е":
        if stressed:
            return "э"
        return "ы" if after_hard_sibilant else "и"   # жена -> [жына], лесной -> [л'исной]
    if letter == "ё":
        return "о"
    if letter == "ю":
        return "у"
    if letter == "я":
        return "а" if stressed else "и"           # пятак -> [п'итак]
    raise ValueError(f"не гласная: {letter!r}")


def _consonant_soft(letter: str, next_letter: Optional[str]) -> bool:
    if letter in ALWAYS_HARD:
        return False
    if letter in ALWAYS_SOFT:
        return True
    if next_letter is None:
        return False
    return next_letter in SOFTENING_LETTERS or next_letter == "ь"


def _letters_to_phonemes(letters: str, stressed_vowel_pos: int) -> List[Phoneme]:
    out: List[Phoneme] = []
    n = len(letters)
    for i, ch in enumerate(letters):
        if ch in SIGNS or ch == "-":
            continue                      # ь/ъ звука не дают (мягкость уже учтена)
        prev = letters[i - 1] if i > 0 else None
        nxt = letters[i + 1] if i + 1 < n else None
        if ch in VOWEL_LETTERS:
            stressed = (i == stressed_vowel_pos)
            yotated_strong = ch in YOTATED_LETTERS and (
                i == 0 or (prev in VOWEL_LETTERS) or (prev in SIGNS)
            )
            if yotated_strong:
                out.append(Phoneme("й", is_vowel=False, soft=True, source_letter=ch))
                out.append(Phoneme(_realize_vowel(ch, stressed, None),
                                   is_vowel=True, stressed=stressed, source_letter=ch))
            else:
                out.append(Phoneme(_realize_vowel(ch, stressed, prev),
                                   is_vowel=True, stressed=stressed, source_letter=ch))
        else:
            out.append(Phoneme(ch, is_vowel=False,
                               soft=_consonant_soft(ch, nxt), source_letter=ch))
    return out


def _apply_voicing(ph: List[Phoneme]) -> None:
    """Оглушение/озвончение — справа налево (каскад: поезд -> [пойист])."""
    last = len(ph) - 1
    for i in range(last, -1, -1):
        p = ph[i]
        if p.is_vowel:
            continue
        base = p.symbol
        # 1) оглушение звонкого в абсолютном конце слова
        if i == last and base in VOICED_TO_VOICELESS:
            p.symbol = VOICED_TO_VOICELESS[base]
            continue
        if i == last:
            continue
        nxt = ph[i + 1]
        if nxt.is_vowel:
            continue
        nb = nxt.symbol
        if nb in SONORANT_LETTERS:
            continue                  # сонорные ассимиляции не вызывают
        if nb == "в":
            continue                  # «в» не озвончает предыдущий (твой -> [твой])
        if nb in VOICED_TO_VOICELESS:                 # справа звонкий шумный
            if base in VOICELESS_TO_VOICED:
                p.symbol = VOICELESS_TO_VOICED[base]  # вокзал -> [вагзал]
        elif nb in VOICELESS_TO_VOICED or nb in UNPAIRED_VOICELESS:  # справа глухой
            if base in VOICED_TO_VOICELESS:
                p.symbol = VOICED_TO_VOICELESS[base]  # ложка -> [лошка]


# ═══════════════════════════════════════════════════════════════════════
#  5. СЛОГОДЕЛЕНИЕ
# ═══════════════════════════════════════════════════════════════════════

def _syllable_starts(ph: List[Phoneme]) -> List[int]:
    """Границы слогов по восходящей звучности (фонетический слог)."""
    vidx = [i for i, p in enumerate(ph) if p.is_vowel]
    if not vidx:
        return [0]
    starts = [0]
    for k in range(len(vidx) - 1):
        a, b = vidx[k], vidx[k + 1]
        cons = list(range(a + 1, b))
        if len(cons) == 0:
            split = b
        elif len(cons) == 1:
            split = cons[0]                       # ма-як, пи-а-ни-но
        else:
            c1, c2 = ph[cons[0]], ph[cons[1]]
            if c1.symbol == "й":
                split = cons[1]                   # чай-ник (й всегда закрывает слог)
            elif c1.symbol in SONORANT_LETTERS and c2.symbol not in SONORANT_LETTERS:
                split = cons[1]                   # бан-ка, мор-ковка, апель-син
            else:
                split = cons[0]                   # ю-бка, ма-трёшка, ло-жка
        starts.append(split)
    return starts


# ═══════════════════════════════════════════════════════════════════════
#  6. РЕЗУЛЬТАТ РАЗБОРА
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Analysis:
    word: str
    stress_syllable: int
    processed: str
    phonemes: List[Phoneme]
    transcription: str                       # 'марос'  (без скобок)
    transcription_display: str               # '[марос]'
    phoneme_keys: Tuple[str, ...]
    n_syllables: int
    syllables: List[Dict[str, Any]]
    clusters: List[Dict[str, Any]]
    markova_v1: Optional[int]
    markova_label: Optional[str]
    beyond_base: bool
    markova_conflict: bool
    markova_notes: List[str]
    sound_occurrences: List[Dict[str, Any]]
    problem_phonemes: FrozenSet[str]
    opposition_pairs: List[str]
    is_neutral: bool
    soft_hard_twin: bool
    soft_hard_twins: List[str]
    ends_closed: bool

    # ── удобные производные ────────────────────────────────────────────
    def has(self, phoneme: str) -> bool:
        return phoneme in self.phoneme_keys

    def occurrences_of(self, phoneme: str) -> List[Dict[str, Any]]:
        return [o for o in self.sound_occurrences if o["phoneme"] == phoneme]

    def positions_of(self, phoneme: str) -> Set[str]:
        return {o["position"] for o in self.occurrences_of(phoneme)}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "word": self.word,
            "stress_syllable": self.stress_syllable,
            "transcription": self.transcription,
            "transcription_display": self.transcription_display,
            "phonemes": [p.to_dict() for p in self.phonemes],
            "phoneme_keys": list(self.phoneme_keys),
            "n_syllables": self.n_syllables,
            "syllables": self.syllables,
            "clusters": self.clusters,
            "markova_v1": self.markova_v1,
            "markova_label": self.markova_label,
            "beyond_base": self.beyond_base,
            "markova_conflict": self.markova_conflict,
            "markova_notes": self.markova_notes,
            "sound_occurrences": self.sound_occurrences,
            "problem_phonemes": sorted(self.problem_phonemes),
            "opposition_pairs": self.opposition_pairs,
            "is_neutral": self.is_neutral,
            "soft_hard_twin": self.soft_hard_twin,
            "soft_hard_twins": self.soft_hard_twins,
            "ends_closed": self.ends_closed,
        }


# ═══════════════════════════════════════════════════════════════════════
#  7. ГЛАВНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════════════════════════════════

def analyze(word: str, stress_syllable: Optional[int] = None) -> Analysis:
    """Слово + номер ударного слога -> полный фонетический разбор."""
    raw = word.strip().lower()
    letters = _preprocess(raw)
    vowel_positions = [i for i, ch in enumerate(letters) if ch in VOWEL_LETTERS]
    n_syll = len(vowel_positions)
    if n_syll == 0:
        raise ValueError(f"в слове {word!r} нет гласных — слог не строится")

    # ── ударение ───────────────────────────────────────────────────────
    if stress_syllable is None:
        if n_syll == 1:
            stress_syllable = 1
        elif "ё" in letters:
            stress_syllable = 1 + [letters[i] for i in vowel_positions].index("ё")
        else:
            raise ValueError(
                f"для {word!r} нужно указать stress_syllable "
                f"(1..{n_syll}) — правилами ударение не выводится"
            )
    if not (1 <= stress_syllable <= n_syll):
        raise ValueError(
            f"stress_syllable={stress_syllable} вне диапазона 1..{n_syll} для {word!r}"
        )
    stressed_vowel_pos = vowel_positions[stress_syllable - 1]

    # ── фонемы ─────────────────────────────────────────────────────────
    ph = _letters_to_phonemes(letters, stressed_vowel_pos)
    _apply_voicing(ph)
    keys = tuple(p.key for p in ph)
    transcription = "".join(keys)

    # ── слоги ──────────────────────────────────────────────────────────
    starts = _syllable_starts(ph)
    bounds = [(starts[k], (starts[k + 1] - 1) if k + 1 < len(starts) else len(ph) - 1)
              for k in range(len(starts))]
    syll_of: List[int] = [0] * len(ph)
    nucleus_of: List[int] = []            # 0-based: индекс гласной каждого слога
    syllables: List[Dict[str, Any]] = []
    for si, (a, b) in enumerate(bounds, start=1):
        idxs = list(range(a, b + 1))
        for i in idxs:
            syll_of[i] = si
        nucleus_i = next(i for i in idxs if ph[i].is_vowel)
        nucleus_of.append(nucleus_i)
        onset = [ph[i].key for i in idxs if i < nucleus_i]
        coda = [ph[i].key for i in idxs if i > nucleus_i]
        syllables.append({
            "index": si,
            "text": "".join(ph[i].key for i in idxs),
            "onset": onset,
            "nucleus": ph[nucleus_i].key,
            "coda": coda,
            "closed": len(coda) > 0,
            "stressed": ph[nucleus_i].stressed,
        })

    # ── стечения согласных ─────────────────────────────────────────────
    clusters: List[Dict[str, Any]] = []
    cluster_of: Dict[int, int] = {}       # индекс фонемы -> индекс кластера
    i = 0
    while i < len(ph):
        if ph[i].is_consonant:
            j = i
            while j + 1 < len(ph) and ph[j + 1].is_consonant:
                j += 1
            if j > i:                      # стечение = 2+ согласных подряд
                idxs = list(range(i, j + 1))
                if i == 0:
                    pos = "initial"
                elif j == len(ph) - 1:
                    pos = "final"
                else:
                    pos = "medial"
                spans = sorted({syll_of[k] for k in idxs})
                cl_idx = len(clusters)
                for k in idxs:
                    cluster_of[k] = cl_idx
                # onset / coda / split относительно слога
                if len(spans) > 1:
                    side = "split"
                else:
                    nuc = nucleus_of[spans[0] - 1]
                    side = "onset" if all(k < nuc for k in idxs) else "coda"
                clusters.append({
                    "index": cl_idx,
                    "phonemes": [ph[k].key for k in idxs],
                    "text": "".join(ph[k].key for k in idxs),
                    "position": pos,
                    "syllable_idx": syll_of[i],
                    "syllable_span": spans,
                    "side": side,
                    "spans_boundary": len(spans) > 1,
                    "start": i,
                    "end": j,
                })
            i = j + 1
        else:
            i += 1

    has_initial = any(c["position"] == "initial" for c in clusters)
    has_final = any(c["position"] == "final" for c in clusters)
    ends_closed = ph[-1].is_consonant

    # ── классификация по Марковой V1 ───────────────────────────────────
    markova, conflict, beyond, notes = _classify_markova(
        n_syll, len(clusters), has_initial, has_final, ends_closed, syllables
    )

    # ── вхождения корригируемых звуков ─────────────────────────────────
    occurrences: List[Dict[str, Any]] = []
    last_i = len(ph) - 1
    for idx, p in enumerate(ph):
        if p.is_vowel or p.key not in CORRIGIBLE:
            continue
        if idx == 0:
            position = "initial"
        elif idx == last_i:
            position = "final"
        else:
            position = "medial"
        cl = clusters[cluster_of[idx]] if idx in cluster_of else None
        if cl is not None:
            role_i = idx - cl["start"]
            role = _ORDINALS[role_i] if role_i < len(_ORDINALS) else f"pos{role_i + 1}"
        else:
            role = None
        # «широкая» позиция: внутри начального/конечного стечения слова
        if cl is not None and cl["position"] == "initial":
            position_wide = "initial"
        elif cl is not None and cl["position"] == "final":
            position_wide = "final"
        else:
            position_wide = position
        prev_p = ph[idx - 1] if idx > 0 else None
        next_p = ph[idx + 1] if idx < last_i else None
        occurrences.append({
            "phoneme": p.key,
            "phoneme_class": PHONEME_CLASS_OF[p.key],
            "soft": p.soft,
            "index": idx,
            "position": position,
            "position_wide": position_wide,
            "syllable_idx": syll_of[idx],
            "in_cluster": cl is not None,
            "cluster": cl["text"] if cl else None,
            "cluster_role": role,
            "cluster_side": cl["side"] if cl else None,
            "vowel_after": next_p.key if (next_p and next_p.is_vowel) else None,
            "vowel_before": prev_p.key if (prev_p and prev_p.is_vowel) else None,
            "prev_phoneme": prev_p.key if prev_p else None,
            "next_phoneme": next_p.key if next_p else None,
            "stressed": syllables[syll_of[idx] - 1]["stressed"],
        })

    problem = frozenset(k for k in keys if k in CORRIGIBLE)

    pairs = [name for name, a_set, b_set in OPPOSITION_PAIRS
             if (problem | set(keys)) & a_set and (problem | set(keys)) & b_set]

    # мягкий/твёрдый близнец одной фонемы в одном слове
    twins = sorted({p.symbol for p in ph if p.is_consonant and p.soft
                    and p.symbol not in ALWAYS_SOFT
                    and any(q.is_consonant and q.symbol == p.symbol and not q.soft
                            and q.symbol not in ALWAYS_HARD for q in ph)})

    return Analysis(
        word=raw,
        stress_syllable=stress_syllable,
        processed=letters,
        phonemes=ph,
        transcription=transcription,
        transcription_display=f"[{transcription}]",
        phoneme_keys=keys,
        n_syllables=n_syll,
        syllables=syllables,
        clusters=clusters,
        markova_v1=markova,
        markova_label=MARKOVA_V1.get(markova) if markova else None,
        beyond_base=beyond,
        markova_conflict=conflict,
        markova_notes=notes,
        sound_occurrences=occurrences,
        problem_phonemes=problem,
        opposition_pairs=pairs,
        is_neutral=len(problem) == 0,
        soft_hard_twin=len(twins) > 0,
        soft_hard_twins=twins,
        ends_closed=ends_closed,
    )


def _classify_markova(n_syll: int, n_clusters: int, has_initial: bool,
                      has_final: bool, closed: bool,
                      syllables: List[Dict[str, Any]]):
    """Порядок проверок = «самый сложный подходящий тип»."""
    notes: List[str] = []
    conflict = False
    beyond = False
    t: Optional[int]

    if n_syll == 1:
        if n_clusters == 0:
            t = 3
            if not closed:
                notes.append("односложное открытое — в V1 отдельного типа нет, "
                             "отнесено к 3 (односложные закрытые)")
        elif has_initial and has_final:
            t = 12
            conflict = True
            notes.append("стечение и в начале, и в конце — V1 такого слота не имеет "
                         "(у Марковой-1961 это строка 11: кнут, танк); отнесено к 12")
        elif has_final:
            t = 12
        elif has_initial:
            t = 11
        else:
            t = 11
            notes.append("односложное со стечением без выхода на край слова — "
                         "отнесено к 11")
    elif n_syll == 2:
        if n_clusters == 0:
            t = 4 if closed else 1
        elif n_clusters >= 2:
            t = 13
        else:
            t = 6 if closed else 5
    elif n_syll == 3:
        if n_clusters == 0:
            t = 7 if closed else 2
        elif n_clusters >= 2:
            t = 10
        else:
            t = 9 if closed else 8
    else:  # 4+
        all_open = all(not s["closed"] for s in syllables)
        if n_clusters == 0 and all_open:
            t = 14
            if n_syll > 4:
                notes.append(f"{n_syll} слога(ов) открытых — за примерами типа 14 "
                             f"(тот описан как четырёхсложный)")
        else:
            t = None
            beyond = True
            notes.append("слово сложного слогового состава — за пределами базовых 14 "
                         "типов V1 (beyond_base)")
    return t, conflict, beyond, notes


# ═══════════════════════════════════════════════════════════════════════
#  8. ОТБОР СЛОВ ПО ЖЁСТКИМ ВОРОТАМ
# ═══════════════════════════════════════════════════════════════════════

GATES = ("наличие", "позиция", "структура", "чистота", "лексика")

_CYR_RE = re.compile(r"^[а-яё-]+$")


class SelectionList(list):
    """Список отобранных Analysis + .report (недобор никогда не молчит)."""
    report: Dict[str, Any]


def _opposition_partners(target: str) -> Set[str]:
    out: Set[str] = set()
    for _name, a_set, b_set in OPPOSITION_PAIRS:
        if target in a_set:
            out |= set(b_set)
        if target in b_set:
            out |= set(a_set)
    return out - {target}


def _softness_twin(target: str) -> Optional[str]:
    """Для 'р' -> \"р'\", для \"р'\" -> 'р'. Для непарных (ж, ш, ц, ч, щ, й) — None."""
    base = target.rstrip("'")
    if base in ALWAYS_HARD or base in ALWAYS_SOFT:
        return None
    return base if target.endswith("'") else base + "'"


def _lexical_ok(word: str) -> bool:
    """Лёгкие ворота лексики: кириллица, есть гласная, длина >= 2.
    Смысловая пригодность (детская, картиночная) — ручной/курируемый слой."""
    w = word.strip().lower()
    if len(w) < 2 or not _CYR_RE.match(w):
        return False
    return any(ch in VOWEL_LETTERS for ch in w)


def _coerce(item: Any) -> Tuple[Optional[Analysis], Optional[str]]:
    """str | (word, stress) | dict | Analysis -> Analysis (или причина отказа)."""
    if isinstance(item, Analysis):
        return item, None
    try:
        if isinstance(item, str):
            return analyze(item), None
        if isinstance(item, dict):
            return analyze(item["word"], item.get("stress_syllable")), None
        if isinstance(item, (tuple, list)) and len(item) == 2:
            return analyze(item[0], item[1]), None
    except (ValueError, KeyError) as exc:
        return None, str(exc)
    return None, f"нераспознанный формат: {item!r}"


def select(words: Iterable[Any],
           target_phoneme: str,
           position: Optional[Any] = None,
           syl_types: Optional[Iterable[int]] = None,
           exclude_phonemes: Iterable[str] = frozenset(),
           markova_max: Optional[int] = None,
           n: int = 10,
           *,
           position_mode: str = "strict",
           cluster_role: Optional[str] = None,
           stressed_only: bool = False,
           lexicon: Optional[Iterable[str]] = None,
           purity_softness_twin: bool = True) -> SelectionList:
    """Отбор слов жёсткими воротами:
       наличие -> позиция -> структура -> чистота -> лексика.

    target_phoneme — ключ фонемы ('р', "р'", 'с', 'ш', ...). Мягкий и твёрдый —
    РАЗНЫЕ цели: 'р' не отберёт «матрёшку» ([матр'ошка]).

    position — 'initial' | 'medial' | 'final' (или их набор). По умолчанию
    сравнивается позиция ПО СЛОВУ (индекс фонемы). position_mode='wide'
    считает звук внутри начального/конечного стечения слова начальным/конечным
    (тогда Р в «трава» — initial).

    exclude_phonemes — звуки, которых ребёнок ещё не произносит.
    К ним автоматически добавляются оппозиционные пары цели и (по умолчанию)
    противоположный по твёрдости близнец цели.

    Возвращает SelectionList (<= n элементов) с полем .report:
    сколько нашли из скольких запрошенных и на каких воротах отсеялось.
    """
    if position_mode not in ("strict", "wide"):
        raise ValueError("position_mode должен быть 'strict' или 'wide'")
    pos_key = "position" if position_mode == "strict" else "position_wide"
    wanted_pos: Optional[Set[str]] = None
    if position is not None:
        wanted_pos = {position} if isinstance(position, str) else set(position)
    wanted_types: Optional[Set[int]] = set(syl_types) if syl_types is not None else None
    lex: Optional[Set[str]] = {w.strip().lower() for w in lexicon} if lexicon else None

    banned: Set[str] = set(exclude_phonemes) | _opposition_partners(target_phoneme)
    if purity_softness_twin:
        twin = _softness_twin(target_phoneme)
        if twin:
            banned.add(twin)
    banned.discard(target_phoneme)

    passed: List[Analysis] = []
    rejected: Dict[str, int] = {g: 0 for g in GATES}
    rejected["разбор"] = 0
    detail: List[Dict[str, Any]] = []

    def reject(word: str, gate: str, why: str) -> None:
        rejected[gate] = rejected.get(gate, 0) + 1
        detail.append({"word": word, "gate": gate, "why": why})

    total = 0
    for item in words:
        total += 1
        a, err = _coerce(item)
        if a is None:
            reject(str(item), "разбор", err or "не разобрано")
            continue

        # ворота 1 — наличие
        if target_phoneme not in a.phoneme_keys:
            reject(a.word, "наличие",
                   f"нет [{target_phoneme}] в {a.transcription_display}")
            continue
        occ = [o for o in a.sound_occurrences if o["phoneme"] == target_phoneme]

        # ворота 2 — позиция (+ совместимость cluster_role)
        if wanted_pos is not None:
            occ = [o for o in occ if o[pos_key] in wanted_pos]
            if not occ:
                reject(a.word, "позиция",
                       f"[{target_phoneme}] не в позиции {sorted(wanted_pos)}")
                continue
        if cluster_role is not None:
            occ = [o for o in occ if o["cluster_role"] == cluster_role]
            if not occ:
                reject(a.word, "позиция", f"нет cluster_role={cluster_role}")
                continue
        if stressed_only:
            occ = [o for o in occ if o["stressed"]]
            if not occ:
                reject(a.word, "позиция", "цель только в безударном слоге")
                continue

        # ворота 3 — структура
        if wanted_types is not None and a.markova_v1 not in wanted_types:
            reject(a.word, "структура",
                   f"тип {a.markova_v1} не в {sorted(wanted_types)}")
            continue
        if markova_max is not None:
            if a.beyond_base or a.markova_v1 is None:
                reject(a.word, "структура", "beyond_base")
                continue
            if a.markova_v1 > markova_max:
                reject(a.word, "структура",
                       f"тип {a.markova_v1} > потолка {markova_max}")
                continue

        # ворота 4 — чистота материала (Коноваленко), не смягчается никогда
        dirty = sorted(set(a.phoneme_keys) & banned)
        if dirty:
            reject(a.word, "чистота",
                   f"{a.transcription_display} содержит {dirty}")
            continue

        # ворота 5 — лексика
        if lex is not None and a.word not in lex:
            reject(a.word, "лексика", "нет в разрешённом словнике")
            continue
        if not _lexical_ok(a.word):
            reject(a.word, "лексика", "не похоже на словарное слово")
            continue

        passed.append(a)

    # мягкое ранжирование
    def rank(a: Analysis):
        occ = [o for o in a.sound_occurrences if o["phoneme"] == target_phoneme]
        return (
            0 if any(o["stressed"] for o in occ) else 1,
            a.markova_v1 if a.markova_v1 is not None else 99,
            len(a.problem_phonemes),
            a.word,
        )

    passed.sort(key=rank)
    result = SelectionList(passed[:n])

    hints: List[str] = []
    if len(result) < n:
        worst = sorted(((v, k) for k, v in rejected.items() if v), reverse=True)
        for cnt, gate in worst[:3]:
            if gate == "структура":
                hints.append(f"поднять потолок структуры (отсеяно {cnt})")
            elif gate == "позиция":
                hints.append(f"разрешить другие позиции звука (отсеяно {cnt})")
            elif gate == "чистота":
                hints.append(f"чистота отсеяла {cnt} — сузить exclude_phonemes нельзя, "
                             f"нужен более широкий словник")
            elif gate == "наличие":
                hints.append(f"расширить словник: без цели {cnt}")
            elif gate == "лексика":
                hints.append(f"лексика отсеяла {cnt}")
    result.report = {
        "target": target_phoneme,
        "requested": n,
        "found": len(result),
        "shortfall": max(0, n - len(result)),
        "candidates": total,
        "banned_phonemes": sorted(banned),
        "rejected": {k: v for k, v in rejected.items() if v},
        "rejected_detail": detail,
        "hints": hints,
        "line": f"{len(result)} из {n}" + (f", расширить: {'; '.join(hints)}"
                                           if hints else ""),
    }
    return result


# ═══════════════════════════════════════════════════════════════════════
#  9. ЧЕЛОВЕКОЧИТАЕМЫЙ РАЗБОР
# ═══════════════════════════════════════════════════════════════════════

def describe(word: str, stress_syllable: Optional[int] = None) -> str:
    a = analyze(word, stress_syllable)
    lines = [
        f"{a.word}  {a.transcription_display}  ударение: слог {a.stress_syllable}",
        f"  слоги ({a.n_syllables}): " + " · ".join(
            f"{s['text']}{'|закр' if s['closed'] else ''}"
            f"{'|УДАР' if s['stressed'] else ''}" for s in a.syllables),
        f"  стечения: " + (", ".join(
            f"{c['text']} ({c['position']}, слог {c['syllable_idx']})"
            for c in a.clusters) or "нет"),
        f"  Маркова V1: {a.markova_v1} — {a.markova_label}"
        + ("  [beyond_base]" if a.beyond_base else "")
        + ("  [конфликт V1]" if a.markova_conflict else ""),
        f"  проблемные фонемы: {sorted(a.problem_phonemes) or 'нет (нейтральное)'}",
        f"  оппозиции: {a.opposition_pairs or 'нет'}"
        + (f"   мягко-твёрдый близнец: {a.soft_hard_twins}" if a.soft_hard_twin else ""),
    ]
    for o in a.sound_occurrences:
        lines.append(
            f"    [{o['phoneme']}] {o['phoneme_class']}: {o['position']}"
            f", слог {o['syllable_idx']}"
            + (f", стечение {o['cluster']} ({o['cluster_role']}, {o['cluster_side']})"
               if o["in_cluster"] else ", вне стечения")
            + f", гласная до/после: {o['vowel_before']}/{o['vowel_after']}"
            + (", УДАРНЫЙ слог" if o["stressed"] else "")
        )
    for note in a.markova_notes:
        lines.append(f"  ! {note}")
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover
    demo = [("мороз", 2), ("ложка", 1), ("лодка", 1), ("юбка", 1), ("морковка", 2),
            ("солнце", 1), ("маяк", 2), ("ёж", 1), ("рысь", 1), ("зонт", 1),
            ("стол", 1), ("матрёшка", 2), ("черепаха", 3), ("автобус", 2),
            ("апельсин", 3), ("вата", 1), ("мак", 1)]
    for w, s in demo:
        print(describe(w, s))
        print()

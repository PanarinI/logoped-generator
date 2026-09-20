#!/usr/bin/env bash
#
# vykat.sh — выкатить logozvuk.com, пока вебхук Amvera сломан (с 18.09.2026).
#
# Amvera держит СВОЮ копию репозитория (ветка master) и обычно сама вливает в
# неё наш GitHub. Это вливание падает с 18.09 («неизвестная ошибка во время
# пулла»), поддержка молчит. Скрипт делает тот же шаг руками: сливает `main` в
# `amvera/master` и отправляет — сборка запускается от пуша.
# Разбор, почему так, а не иначе — DECISIONS.md 2026-09-20.
#
#   bash tools/vykat.sh          # выкатить и дождаться сайта
#   bash tools/vykat.sh --dry    # примерка: всё посчитать, ничего не отправлять
#
# Порядок в саду не меняется: код живёт на GitHub. Сначала «git» (gitall.sh),
# потом этот выкат. Скрипт откажется работать, если на GitHub нет того, что
# лежит локально, — иначе на сайте оказалось бы то, чего нет в истории.
#
# ⚠ Слияние, а не --force. У Amvera свой нормализованный `amvera.yaml`
# (`persistenceMount: /data` — папка с отзывами логопедов). Force затёр бы его.
# Откат, если новая сборка встанет колом:
#   git push amvera <прежний-sha>:refs/heads/master --force
set -euo pipefail

cd "$(dirname "$0")/.."
DRY=${1:-}
SITE=https://logozvuk.com
REMOTE=amvera

git remote get-url "$REMOTE" >/dev/null 2>&1 || {
  echo "нет remote «$REMOTE». Заведите: git remote add $REMOTE https://git.amvera.ru/panarini/logozvuk"
  echo "(логин СТРОЧНЫМИ: с PanarinI сервер отвечает «repository not found»)"
  exit 1
}

# 1. То, что не закоммичено, на сайт не поедет — скажем об этом вслух.
DIRTY=$(git status --porcelain -- '*.py' '*.js' '*.css' '*.html' '*.json' '*.jsonl' | head -20)
[ -n "$DIRTY" ] && { echo "⚠ незакоммиченные правки кода (на сайт НЕ поедут):"; echo "$DIRTY"; echo; }

# 2. GitHub — дом кода. Локальное впереди GitHub → сперва «git».
git fetch -q origin main
AHEAD=$(git rev-list --count origin/main..main)
[ "$AHEAD" -gt 0 ] && { echo "❌ на GitHub нет $AHEAD коммит(ов) из main. Сперва «git», потом выкат."; exit 1; }

# 3. Свежая копия ветки Amvera.
git fetch -q "$REMOTE"
if git merge-base --is-ancestor main "$REMOTE/master"; then
  echo "на сайте уже всё, что есть в main ($(git rev-parse --short main)) — выкатывать нечего"; exit 0
fi

echo "поедет на сайт:"
git log --oneline "$REMOTE/master..main" | sed 's/^/  /'
echo "файлы:"; git diff --stat "$REMOTE/master" main | tail -12 | sed 's/^/  /'

# 4. Слияние без рабочей папки: ветку не переключаем — в ней может лежать
#    незаконченная работа (так и было 09-20).
TREE=$(git merge-tree --write-tree "$REMOTE/master" main) || {
  echo "❌ слияние конфликтует — руками: git merge, разобрать, потом push"; exit 1; }
MSG="Слить main в копию Amvera: $(git log -1 --format=%s main)

Выкат мимо GitHub: вебхук Amvera сломан с 18.09.2026. Содержимое то же, что в
GitHub main $(git rev-parse --short main).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
MERGE=$(git commit-tree "$TREE" -p "$REMOTE/master" -p main -m "$MSG")

if [ "$DRY" = "--dry" ]; then
  echo; echo "примерка: отправили бы $MERGE в $REMOTE/master. Ничего не отправлено."; exit 0
fi

echo; echo "откат при беде: git push $REMOTE $(git rev-parse --short "$REMOTE/master"):refs/heads/master --force"
git push "$REMOTE" "$MERGE:refs/heads/master"

# 5. Проверка глазами машины: хэш экрана на сайте должен совпасть с нашим.
#    Считается по трём файлам экрана — тем же способом, что и в web/server.py.
WANT=$( { git show main:web/index.html; git show main:web/app.js; git show main:web/app.css; } | md5 | cut -c1-12)
echo; echo "ждём сборку (сайт на пару минут отдаёт 503 — Amvera гасит старый контейнер)"
for i in $(seq 1 60); do
  GOT=$(curl -s -m 15 "$SITE/api/version" | sed -n 's/.*"v": *"\([^"]*\)".*/\1/p')
  if [ "$GOT" = "$WANT" ]; then echo "✅ сайт отдаёт $GOT — это наш main, $(( i * 20 )) c"; exit 0; fi
  sleep 20
done
echo "⚠ за 20 минут сайт не отдал $WANT (сейчас «${GOT:-нет ответа}»). Смотрите лог сборки в панели Amvera."
exit 1

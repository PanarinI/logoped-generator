# Генератор логопедических листов — образ для любого Docker-хостинга.
#
# Ноль зависимостей: движок и веб написаны на стандартной библиотеке,
# поэтому здесь нет ни pip install, ни requirements.txt — и ломаться нечему.
#
# КУДА ЭТОТ ОБРАЗ ЕДЕТ (08-12). Писался под HuggingFace Space, но HF закрыл
# бесплатные Docker-Space: «Gradio and Docker Spaces run on compute and require
# a paid plan to create» (дока Spaces Overview). Выбран Railway — он отдаёт
# приложения из собственной сети, а не через Cloudflare, и это решающее: с июня
# 2025 Cloudflare отдаёт российским провайдерам только первые 16 КБ ресурса, а
# все наши логопеды в России.
#
# Порт хостинг передаёт сам, переменной PORT — сервер её читает (web/server.py).
# Значение ниже — запасное, на случай запуска без окружения; 8080 стоит потому,
# что именно туда Railway направляет трафик по умолчанию. Раньше здесь было 7860
# (порт HF Space): если бы хостинг не подставил свою переменную, приложение село
# бы на 7860, а трафик шёл на 8080 — и вместо листа была бы ошибка.
FROM python:3.12-slim

ENV HOST=0.0.0.0 \
    PORT=8080 \
    PYTHONUNBUFFERED=1

RUN useradd -m -u 1000 app
USER app
WORKDIR /home/app

COPY --chown=app:app logoped_slovar/ ./logoped_slovar/
COPY --chown=app:app web/ ./web/

EXPOSE 8080
CMD ["python3", "web/server.py"]

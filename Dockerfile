# Генератор логопедических листов — образ для HuggingFace Space (SDK: docker).
#
# Ноль зависимостей: движок и веб написаны на стандартной библиотеке,
# поэтому здесь нет ни pip install, ни requirements.txt — и ломаться нечему.

FROM python:3.12-slim

# HF Space отдаёт трафик на 7860 и запускает контейнер не от root
ENV HOST=0.0.0.0 \
    PORT=7860 \
    PYTHONUNBUFFERED=1

RUN useradd -m -u 1000 app
USER app
WORKDIR /home/app

COPY --chown=app:app logoped_slovar/ ./logoped_slovar/
COPY --chown=app:app web/ ./web/

EXPOSE 7860
CMD ["python3", "web/server.py"]

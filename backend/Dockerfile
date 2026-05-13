FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=80

COPY functions/user-story-api/requirements.txt ./requirements.txt

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY functions/user-story-api/ .

EXPOSE 80

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-80}"]

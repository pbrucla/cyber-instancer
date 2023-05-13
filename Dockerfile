FROM python:3.11-slim-bullseye

WORKDIR /app

COPY backend/requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY ./backend/src /app
COPY ./backend/config.yml /app/config.yml

ENV PORT=8080
CMD ["gunicorn", "-w", "1", "app:app"]

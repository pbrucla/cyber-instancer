FROM python:3.11-slim-bullseye

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY ./src /app
COPY ./config.yml /app/config.yml

ENV PORT=8080
CMD ["gunicorn", "-w", "1", "app:app"]

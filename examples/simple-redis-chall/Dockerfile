FROM python:3.11-slim-bullseye

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py /app/

ENV PORT=8080
CMD ["gunicorn", "-w", "4", "app:app"]

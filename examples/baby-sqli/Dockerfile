FROM python:3.11-slim-bullseye

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py init.py ./

RUN python init.py

ENV PORT=8080
ENV FLAG="flag{yay_you_solved_the_challenge}"

CMD ["gunicorn", "-w", "4", "app:app"]

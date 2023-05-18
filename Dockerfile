# pull official base image
FROM node:20-alpine AS build-frontend

# set working directory
WORKDIR /app

# install app dependencies
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# add app
COPY frontend .

# Build app
RUN npm run build

FROM python:3.11-slim-bullseye

RUN apt-get update && apt-get install -y libpq5

WORKDIR /app

COPY backend/requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY backend .

COPY --from=build-frontend /app/dist static

ENV PORT=8080
CMD ["gunicorn", "-w", "4", "app:app"]

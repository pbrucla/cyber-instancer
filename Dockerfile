# pull official base image
FROM node:20-alpine AS build-frontend

# set working directory
WORKDIR /app

# install app dependencies
COPY ./frontend/package.json ./
COPY ./frontend/package-lock.json ./
RUN npm ci

# add app
COPY /frontend ./

# Build app
RUN npm run build

FROM python:3.11-slim-bullseye

WORKDIR /app

COPY backend/requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY ./backend/src /app
COPY ./backend/config.yml /app/config.yml

COPY --from=build-frontend /app/dist /app/static/

ENV PORT=8080
CMD ["gunicorn", "-w", "1", "app:app"]

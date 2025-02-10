FROM python:3.13.1-bookworm AS base

ARG DEBIAN_FRONTEND=noninteractive

RUN mkdir -p /app/backend
RUN mkdir -p /app/log
WORKDIR /app

COPY requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt

COPY static.py /app/backend/static.py
COPY enums.py /app/backend/enums.py
COPY alembic.ini /app/backend/alembic.ini

COPY alembic /app/backend/alembic
COPY api /app/backend/api
COPY blizzard /app/backend/blizzard
COPY db /app/backend/db
COPY etl /app/backend/etl
COPY utils /app/backend/utils


FROM base AS test

COPY requirements.dev.txt /app/backend/requirements.dev.txt
RUN pip install -r /app/backend/requirements.dev.txt

COPY test /app/backend/test

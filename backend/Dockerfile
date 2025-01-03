FROM python:3.13.1-bookworm

RUN mkdir -p /app/backend
WORKDIR /app

COPY requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt

COPY static.py /app/backend/static.py
COPY enums.py /app/backend/enums.py
COPY alembic.ini /app/backend/alembic.ini

COPY alembic /app/backend/alembic
COPY api /app/backend/api
COPY db /app/backend/db
COPY etl /app/backend/etl

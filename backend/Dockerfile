FROM python:3.13.1-bookworm

RUN mkdir /app
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY static.py /app/static.py
COPY api /app/api

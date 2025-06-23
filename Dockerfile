FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y nmap mongodb curl && \
    pip install pipx && \
    pipx install .

COPY . /app
WORKDIR /app

ENTRYPOINT ["nethawk"]

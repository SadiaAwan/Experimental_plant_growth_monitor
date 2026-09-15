FROM python:3.13-slim-bookworm

WORKDIR /app
COPY consumer.py /app/
COPY utils /app/utils
COPY pyproject.toml /app/

RUN pip install --no-cache-dir uv
RUN uv sync --no-dev


ENV PYTHONUNBUFFERED=1
CMD ["uv", "run", "consumer.py"]
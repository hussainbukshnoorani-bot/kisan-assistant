FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY data ./data
COPY alembic.ini ./
RUN pip install --no-cache-dir .

RUN useradd --create-home kisan
USER kisan

EXPOSE 8000
CMD ["uvicorn", "kisan.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

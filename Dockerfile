FROM python:3.9-slim

LABEL maintainer="Abtaha <f2022-553@bnu.edu.pk>"
LABEL version="1.0"
LABEL description="Sakila Flask Application"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

CMD ["python", "app.py"]
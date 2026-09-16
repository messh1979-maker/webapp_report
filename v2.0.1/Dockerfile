FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY requirements.txt requirements-production.txt ./
RUN pip install --no-cache-dir -r requirements-production.txt
COPY . .
RUN chown -R app:app /app
USER app
EXPOSE 8000
CMD ["/bin/sh", "-c", "AUTO_CREATE_SCHEMA=1 python -c 'from app import app' && AUTO_CREATE_SCHEMA=0 exec gunicorn -c gunicorn.conf.py app:app"]

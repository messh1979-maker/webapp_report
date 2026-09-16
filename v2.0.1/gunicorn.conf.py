import multiprocessing
import os

bind = os.environ.get("BIND", "0.0.0.0:8000")
workers = int(os.environ.get("WEB_CONCURRENCY", min(4, max(2, multiprocessing.cpu_count()))))
worker_class = "gthread"
threads = int(os.environ.get("GUNICORN_THREADS", "25"))
worker_connections = 1000
timeout = 60
graceful_timeout = 30
keepalive = 5
max_requests = 2000
max_requests_jitter = 200
accesslog = "-"
errorlog = "-"
capture_output = True

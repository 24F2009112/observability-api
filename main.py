from collections import deque
from datetime import datetime, timezone
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from starlette.responses import Response

EMAIL = "24f2009112@ds.study.iitm.ac.in"
STARTED_AT = time.monotonic()

# A real Prometheus counter. The HTTP middleware increments this for every request
# that reaches the application, including /metrics and failed endpoint requests.
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests received by this service",
)

# Keep a bounded in-memory tail of structured request logs.
LOG_TAIL = deque(maxlen=2000)

app = FastAPI(title="Production Observability API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Suppress uvicorn's default access logger from being necessary for the assignment;
# the JSON entries below are the structured logs exposed at /logs/tail.

@app.middleware("http")
async def observe_requests(request: Request, call_next):
    HTTP_REQUESTS_TOTAL.inc()
    request_id = str(uuid4())
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration = max(0.0, time.perf_counter() - started)
        entry = {
            "level": "INFO" if status_code < 500 else "ERROR",
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "path": request.url.path,
            "request_id": request_id,
            "method": request.method,
            "status_code": status_code,
            "duration_s": round(duration, 6),
        }
        LOG_TAIL.append(entry)
        # Emit one JSON log line to the platform logs as well.
        logging.getLogger("observability.request").info(
            '{"level":"%s","ts":"%s","path":"%s","request_id":"%s","method":"%s","status_code":%d,"duration_s":%.6f}',
            entry["level"], entry["ts"], entry["path"], entry["request_id"],
            entry["method"], entry["status_code"], entry["duration_s"],
        )

@app.get("/work")
async def work(n: int = Query(default=1, ge=0, le=1000000)):
    # Simulate doing n units of work, without hard-coded answers.
    return {"email": EMAIL, "done": n}

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "uptime_s": max(0.0, time.monotonic() - STARTED_AT)}

@app.get("/logs/tail")
async def logs_tail(limit: int = Query(default=100, ge=1, le=2000)):
    # Snapshot entries most-recent-last; the request to /logs/tail itself is
    # appended by middleware after this response is created.
    return list(LOG_TAIL)[-limit:]

@app.get("/")
async def root():
    return {"status": "ok", "service": "production-observability-api", "docs": "/docs"}

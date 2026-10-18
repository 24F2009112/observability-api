# Production Observability API

FastAPI service for the IITM observability assignment.

## Endpoints

- `GET /work?n=K`: returns `{"email":"24f2009112@ds.study.iitm.ac.in","done":K}` and increments the global request counter.
- `GET /metrics`: Prometheus exposition containing `http_requests_total`.
- `GET /healthz`: returns status `ok` and non-negative uptime seconds.
- `GET /logs/tail?limit=N`: returns recent structured JSON request log entries with `level`, `ts`, `path`, and `request_id` (plus method, status and duration).

Every request is counted by a `prometheus_client.Counter` and captured in the bounded log tail by HTTP middleware. CORS is enabled for browser-based grading.

## Deploy on Render

Create a new Render Web Service connected to this repository.

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Runtime: Python 3

Submit the service base URL only, without a path, to the assignment.

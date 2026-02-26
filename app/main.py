import time

from fastapi import FastAPI

from app.models import ServiceInfo

START_TIME = time.time()
VERSION = "0.1.0"

app = FastAPI(title="Job Board Tracker")


@app.get("/health", status_code=200)
def health():
    return ServiceInfo(
        status="healthy",
        service="Job Board Tracker",
        uptime_seconds=int(time.time() - START_TIME),
        version=VERSION,
    )

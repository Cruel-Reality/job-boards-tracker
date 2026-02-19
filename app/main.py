import time

from fastapi import FastAPI

START_TIME = time.time()
app = FastAPI(title="Job Board Tracker")


@app.get("/health", status_code=200)
def health():
    return {
        "status": "healthy",
        "service": "Job Board Tracker",
        "uptime_seconds": int(time.time() - START_TIME),
    }

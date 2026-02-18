from fastapi import FastAPI

app = FastAPI(title="Job Board Tracker")


@app.get("/hello")
def hello():
    return {"hello:HELLO!!!"}

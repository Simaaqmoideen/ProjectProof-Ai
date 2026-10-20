from fastapi import FastAPI

app = FastAPI(title="ProjectProof AI", version="0.1.0")


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok"}

from fastapi import FastAPI

from app.api.metrics import router as metrics_router
from app.api.routes import router
from app.logging_config import configure_logging

configure_logging()

app = FastAPI(title="Switchboard", version="0.1.0")
app.include_router(router)
app.include_router(metrics_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

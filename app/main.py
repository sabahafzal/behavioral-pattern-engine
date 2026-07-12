from fastapi import FastAPI

from app.api.routes import drift, health

app = FastAPI(
    title="Behavioral Pattern Engine",
    description=(
        "A small ML/statistics API for detecting behavioral patterns — "
        "starting with drift detection, growing toward sentiment, "
        "forecasting, clustering, churn, and CLV models. "
        "Built as shared infrastructure for The Reinvention Edit and future "
        "umbrella-company products."
    ),
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(drift.router)

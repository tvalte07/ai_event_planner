from fastapi import FastAPI
from app.api.routes import router

app=FastAPI(title="AI Event Planner API",version="0.1.0",description="Local-first event planning API")
app.include_router(router)

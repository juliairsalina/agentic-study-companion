from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.upload import router as upload_router
from app.routes.evaluate import router as evaluate_router
from app.routes.workflow import router as workflow_router
from app.routes.study import router as study_router
from app.config import settings

print("FOUNDRY PROJECT ENDPOINT:", settings.FOUNDRY_PROJECT_ENDPOINT)
print("FOUNDRY MODEL:", settings.FOUNDRY_MODEL)

app = FastAPI(
    title="Study Companion API",
    description="Backend API for the Agentic Study Companion hackathon project",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://yellow-moss-0a08bda1e.7.azurestaticapps.net",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Study Companion API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(upload_router)
app.include_router(evaluate_router)
app.include_router(workflow_router)
app.include_router(study_router)

@app.get("/debug/env")
def debug_env():
    return {
        "has_cosmos_endpoint": bool(settings.COSMOS_DB_ENDPOINT),
        "has_cosmos_key": bool(settings.COSMOS_DB_KEY),
        "cosmos_database": settings.COSMOS_DB_DATABASE,
        "cosmos_container": settings.COSMOS_DB_CONTAINER,
        "has_speech_key": bool(settings.AZURE_SPEECH_KEY),
        "speech_region": settings.AZURE_SPEECH_REGION,
        "foundry_model": settings.FOUNDRY_MODEL,
        "has_foundry_endpoint": bool(settings.FOUNDRY_PROJECT_ENDPOINT),
    }
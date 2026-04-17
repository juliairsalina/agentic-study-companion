from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Study Companion API",
    description="Backend API for the Agentic Study Companion hackathon project",
    version="0.1.0",
)

# Allow frontend to call backend during local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later you can restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Study Companion API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }
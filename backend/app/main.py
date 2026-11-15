from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .projects import router as projects_router

app = FastAPI(title="StoryForge API", description="Backend API for The StoryForge Collective.", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(projects_router)

@app.get("/api/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "storyforge-api", "version": app.version}

@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"message": "StoryForge API is running. Visit /docs for the API documentation."}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="StoryForge API",
    description="Backend API for The StoryForge Collective.",
    version="0.1.0",
)

# In local development, the Vite dev server proxies /api requests to this service.
# Keep CORS configured for direct browser access during development as well.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Return a lightweight health response for the frontend and container checks."""
    return {
        "status": "ok",
        "service": "storyforge-api",
        "version": app.version,
    }


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"message": "StoryForge API is running. Visit /docs for the API documentation."}

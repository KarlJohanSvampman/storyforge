from fastapi import FastAPI

app = FastAPI(
    title="StoryForge API",
    description="API for The StoryForge Collective.",
    version="0.1.0",
)


@app.get("/api/v1/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Return a lightweight health response for the API and frontend."""
    return {"status": "ok", "service": "storyforge-api", "version": "0.1.0"}

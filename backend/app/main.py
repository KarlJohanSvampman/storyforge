from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .projects import router as projects_router
from .contributions import router as contributions_router
from .discussion import router as discussion_router
from .narrative import router as narrative_router
from .approval import router as approval_router
from .storyboard import router as storyboard_router
from .documentary import router as documentary_router
from .projects import CurrentUser

app = FastAPI(title="StoryForge API", description="Backend API for The StoryForge Collective.", version="0.10.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(projects_router)
app.include_router(contributions_router)
app.include_router(discussion_router)
app.include_router(narrative_router)
app.include_router(approval_router)
app.include_router(storyboard_router)
app.include_router(documentary_router)


@app.get("/api/me", tags=["users"])
async def current_user(user: CurrentUser) -> dict[str, str]:
    return {"id": str(user.id), "display_name": user.display_name, "email": user.email}


@app.get("/api/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "storyforge-api", "version": app.version}


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"message": "StoryForge API is running. Visit /docs for the API documentation."}

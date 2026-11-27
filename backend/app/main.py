from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .projects import router as projects_router
from .contributions import router as contributions_router
from .discussion import router as discussion_router
from .narrative import router as narrative_router
from .approval import router as approval_router
from .storyboard import router as storyboard_router
from .documentary import router as documentary_router
from .documentary_media import router as documentary_media_router
from .actors import router as actors_router
from .scene_runtime import router as scene_runtime_router
from .performance import router as performance_router
from .production_control import router as production_control_router
from .editorial import router as editorial_router
from .performance_playback import router as performance_playback_router
from .audio import router as audio_router
from .audio_render import router as audio_render_router
from .video_render import router as video_render_router
from .production_assets import router as production_assets_router\nfrom .rig_profiles import router as rig_profiles_router
from .publications import router as publications_router
from .public_release import router as public_release_router
from .release_credits import router as release_credits_router
from .release_feedback import router as release_feedback_router
from .projects import CurrentUser

app = FastAPI(title="StoryForge API", description="Backend API for The StoryForge Collective.", version="0.15.0")
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
app.include_router(documentary_media_router)
app.include_router(actors_router)
app.include_router(scene_runtime_router)
app.include_router(performance_router)
app.include_router(production_control_router)
app.include_router(editorial_router)
app.include_router(performance_playback_router)
app.include_router(audio_router)
app.include_router(audio_render_router)
app.include_router(video_render_router)
app.include_router(production_assets_router)\napp.include_router(rig_profiles_router)
app.include_router(publications_router)
app.include_router(public_release_router)
app.include_router(release_credits_router)
app.include_router(release_feedback_router)


@app.get("/api/me", tags=["users"])
async def current_user(user: CurrentUser) -> dict[str, str]:
    return {"id": str(user.id), "display_name": user.display_name, "email": user.email}


@app.get("/api/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "storyforge-api", "version": app.version}


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"message": "StoryForge API is running. Visit /docs for the API documentation."}

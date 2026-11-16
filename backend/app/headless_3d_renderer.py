"""Playwright bridge for deterministic StoryForge Three.js frame rendering."""
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


def render_manifest_frames(manifest: dict, output_dir: Path) -> int:
    renderer_url = os.getenv("STORYFORGE_HEADLESS_RENDERER_URL", "http://frontend:5173/headless-render.html")
    parsed = urlparse(renderer_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("STORYFORGE_HEADLESS_RENDERER_URL must be an HTTP(S) URL.")
    width = int(manifest.get("width", 1280))
    height = int(manifest.get("height", 720))
    fps = int(manifest.get("fps", 24))
    if width < 320 or width > 1920 or height < 180 or height > 1080 or fps not in (12, 24, 30):
        raise ValueError("Headless 3D render has unsupported dimensions or frame rate.")
    if manifest.get("renderer") != "storyforge-headless-3d-v1":
        raise ValueError("Headless 3D render manifest has an unsupported renderer version.")
    clips = manifest.get("clips")
    if not isinstance(clips, list) or not clips:
        raise ValueError("Headless 3D render manifest contains no clips.")
    starts = [0]
    for index, clip in enumerate(clips):
        duration = int(clip.get("duration_ms", 0))
        if duration <= 0:
            raise ValueError("Headless 3D clips must have a positive duration.")
        if index:
            overlap = int(clip.get("transition_duration_ms", 0))
            if overlap < 0 or overlap > min(int(clips[index - 1]["duration_ms"]), duration) // 2:
                raise ValueError("Headless 3D transition duration is invalid.")
            if clip.get("transition", "cut") not in ("cut", "fade", "dissolve"):
                raise ValueError("Headless 3D manifest contains an unsupported transition.")
            starts.append(starts[-1] + int(clips[index - 1]["duration_ms"]) - overlap)
    duration_ms = starts[-1] + int(clips[-1]["duration_ms"])
    expected_frames = (duration_ms * fps + 999) // 1000
    if expected_frames < 1 or expected_frames > 14_400:
        raise ValueError("Headless 3D render exceeds the ten-minute frame budget.")

    output_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=[
            "--no-sandbox", "--disable-dev-shm-usage", "--enable-webgl",
            "--ignore-gpu-blocklist", "--use-gl=angle", "--use-angle=swiftshader",
            "--enable-unsafe-swiftshader",
        ])
        try:
            page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
            page.set_default_timeout(60_000)
            page.goto(renderer_url, wait_until="networkidle", timeout=120_000)
            page.wait_for_function("() => Boolean(window.storyForgeRenderer)", timeout=60_000)
            initialized = page.evaluate("(manifest) => window.storyForgeRenderer.initialize(manifest)", manifest)
            frame_count = int(initialized.get("frame_count", 0))
            if frame_count != expected_frames:
                raise RuntimeError("Browser renderer frame count does not match the immutable manifest timeline.")
            frame = page.locator("#frame")
            for index in range(frame_count):
                page.evaluate("(index) => window.storyForgeRenderer.renderFrame(index)", index)
                frame.screenshot(path=str(output_dir / f"frame-{index + 1:06d}.png"), timeout=60_000)
            page.evaluate("() => window.storyForgeRenderer.dispose()")
            return frame_count
        except PlaywrightTimeoutError as error:
            raise RuntimeError(f"Headless Three.js renderer timed out: {error}") from error
        finally:
            browser.close()

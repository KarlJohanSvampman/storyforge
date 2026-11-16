"""Deterministic, browser-independent 2D animatic renderer for StoryForge EDL snapshots."""
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def _font(size: int, bold: bool = False):
    candidates = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _vector(value: Any) -> tuple[float, float, float] | None:
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        try:
            result = tuple(float(v) for v in value[:3])
        except (TypeError, ValueError):
            return None
        return result if all(math.isfinite(v) for v in result) else None
    if isinstance(value, dict):
        try:
            result = (float(value["x"]), float(value["y"]), float(value["z"]))
        except (KeyError, TypeError, ValueError):
            return None
        return result if all(math.isfinite(v) for v in result) else None
    return None


def _event_transform(event: dict) -> dict:
    payload = event.get("payload") or {}
    nested = payload.get("transform")
    return nested if isinstance(nested, dict) else payload


def _sample_transform(events: list[dict], instance_id: str, source_ms: int) -> dict:
    samples = [
        event for event in events
        if event.get("event_type") == "transform"
        and event.get("cast_member_instance_id") == instance_id
    ]
    previous = None
    following = None
    for event in samples:
        if int(event.get("timestamp_ms", 0)) <= source_ms:
            previous = event
        else:
            following = event
            break
    if previous is None:
        return {}
    start = _event_transform(previous)
    if following is None:
        return start
    end = _event_transform(following)
    t0, t1 = int(previous.get("timestamp_ms", 0)), int(following.get("timestamp_ms", 0))
    amount = max(0.0, min(1.0, (source_ms - t0) / max(1, t1 - t0)))
    result = dict(start)
    for key in ("position", "rotation", "scale"):
        a, b = _vector(start.get(key)), _vector(end.get(key))
        if a is not None and b is not None:
            result[key] = [a[i] + (b[i] - a[i]) * amount for i in range(3)]
    return result


def _camera_at(clip: dict, source_ms: int) -> dict:
    camera = dict(clip.get("camera_snapshot") or {})
    for event in clip.get("events") or []:
        if event.get("event_type") == "camera" and int(event.get("timestamp_ms", 0)) <= source_ms:
            camera.update(event.get("payload") or {})
    return camera


def _draw_character(draw: ImageDraw.ImageDraw, member: dict, index: int, count: int,
                    transform: dict, zoom: float, camera_offset: tuple[float, float],
                    width: int, height: int) -> None:
    position = _vector(transform.get("position"))
    if position is None:
        position = ((index - (count - 1) / 2) * 2.8, 0.0, 0.0)
    x = width / 2 + (position[0] - camera_offset[0]) * 88 * zoom
    y = height * 0.69 + (position[2] - camera_offset[1]) * 35 * zoom - position[1] * 48 * zoom
    scale_vector = _vector(transform.get("scale")) or (1.0, 1.0, 1.0)
    size = max(0.45, min(2.2, (abs(scale_vector[0]) + abs(scale_vector[1]) + abs(scale_vector[2])) / 3))
    radius = 25 * zoom * size
    if x < -100 or x > width + 100 or y < -150 or y > height + 100:
        return
    draw.ellipse((x - radius * 1.1, y + radius * 1.1, x + radius * 1.1, y + radius * 1.55), fill=(18, 22, 20, 95))
    hue = (index * 43 + 88) % 255
    cloth = (65 + hue // 5, 95 + hue // 4, 66 + hue // 6)
    head_y = y - radius * 2.1
    torso_top, torso_bottom = y - radius * 1.25, y + radius * 0.2
    body_width = radius * 1.05
    draw.rounded_rectangle((x - body_width, torso_top, x + body_width, torso_bottom),
                           radius=max(5, int(radius * 0.25)), fill=cloth, outline=(220, 222, 198), width=2)
    draw.ellipse((x - radius * 0.62, head_y - radius * 0.62,
                  x + radius * 0.62, head_y + radius * 0.62),
                 fill=(188, 145, 112), outline=(46, 43, 37), width=2)
    rotation = _vector(transform.get("rotation")) or (0.0, 0.0, 0.0)
    lean = max(-0.75, min(0.75, rotation[2]))
    shoulder_y = torso_top + radius * 0.2
    hip_y = torso_bottom
    arm_dx = radius * (1.5 + lean)
    draw.line((x - body_width * 0.75, shoulder_y, x - arm_dx, shoulder_y + radius * 1.0),
              fill=(188, 145, 112), width=max(5, int(radius * 0.24)))
    draw.line((x + body_width * 0.75, shoulder_y, x + arm_dx, shoulder_y + radius * 1.0),
              fill=(188, 145, 112), width=max(5, int(radius * 0.24)))
    draw.line((x - radius * 0.38, hip_y, x - radius * 0.48, y + radius * 1.8),
              fill=(37, 43, 39), width=max(7, int(radius * 0.34)))
    draw.line((x + radius * 0.38, hip_y, x + radius * 0.48, y + radius * 1.8),
              fill=(37, 43, 39), width=max(7, int(radius * 0.34)))
    label = (member.get("character_name") or member.get("actor_name") or "Cast")[:24]
    font = _font(max(12, int(15 * zoom)), True)
    box = draw.textbbox((0, 0), label, font=font)
    label_width = box[2] - box[0] + 18
    label_y = head_y - radius * 1.05
    draw.rounded_rectangle((x - label_width / 2, label_y, x + label_width / 2, label_y + 27),
                           radius=7, fill=(20, 27, 23))
    draw.text((x, label_y + 4), label, font=font, fill=(236, 239, 222), anchor="mt")


def render_clip_frame(clip: dict, local_ms: int, width: int, height: int) -> Image.Image:
    image = Image.new("RGB", (width, height), (20, 29, 26))
    draw = ImageDraw.Draw(image, "RGBA")
    for y in range(height):
        blend = y / max(1, height - 1)
        color = (int(22 + 19 * blend), int(36 + 15 * blend), int(33 + 10 * blend), 255)
        draw.line((0, y, width, y), fill=color)
    horizon = int(height * 0.61)
    draw.rectangle((0, horizon, width, height), fill=(57, 65, 53))
    draw.polygon([(0, horizon), (width, horizon), (width, horizon + 90), (0, horizon + 90)],
                 fill=(71, 78, 62))
    draw.line((0, horizon, width, horizon), fill=(165, 168, 137), width=3)
    for offset in range(-width, width * 2, 100):
        draw.line((width // 2 + (offset - width // 2) // 4, horizon,
                   offset, height), fill=(86, 94, 72), width=1)
    draw.rectangle((int(width * .08), int(height * .12), int(width * .92), horizon - 8),
                   outline=(112, 127, 105), width=5)
    draw.rectangle((int(width * .12), int(height * .16), int(width * .88), horizon - 12),
                   outline=(68, 82, 70), width=2)

    source_ms = int(clip.get("in_ms", 0)) + max(0, local_ms)
    camera = _camera_at(clip, source_ms)
    preset = str(camera.get("preset", "wide")).lower()
    zoom = {"close": 1.55, "overhead": 0.82, "reverse": 1.0, "wide": 1.0}.get(preset, 1.0)
    camera_position = _vector(camera.get("position")) or (0.0, 0.0, 0.0)
    camera_offset = (camera_position[0] * 0.12, camera_position[2] * 0.12)
    members = clip.get("cast_members") or []
    events = clip.get("events") or []
    for index, member in enumerate(members):
        transform = _sample_transform(events, str(member.get("id")), source_ms)
        _draw_character(draw, member, index, len(members), transform, zoom, camera_offset, width, height)

    scene_title = str(clip.get("scene_title") or "Scene")[:90]
    title = str(clip.get("title_overlay") or "")[:90]
    font = _font(25, True)
    draw.rounded_rectangle((34, 26, width - 34, 82), radius=12, fill=(10, 16, 14, 205))
    draw.text((54, 40), scene_title, font=font, fill=(224, 232, 215))
    if title:
        title_font = _font(36, True)
        box = draw.textbbox((0, 0), title, font=title_font)
        title_width = min(width - 80, box[2] - box[0] + 56)
        draw.rounded_rectangle((width / 2 - title_width / 2, height - 112,
                                width / 2 + title_width / 2, height - 48),
                               radius=12, fill=(8, 12, 10, 220))
        draw.text((width / 2, height - 80), title, font=title_font,
                  fill=(248, 247, 232), anchor="mm")
    return image


def render_timeline_frame(
    clips: list[dict], starts: list[int], timeline_ms: float, width: int, height: int
) -> Image.Image:
    """Render one timeline frame, compositing the transition between adjacent clips."""
    for index in range(1, len(clips)):
        next_clip = clips[index]
        overlap = int(next_clip.get("transition_duration_ms", 0))
        transition_start = starts[index]
        if overlap <= 0 or not (transition_start <= timeline_ms < transition_start + overlap):
            continue

        previous_clip = clips[index - 1]
        progress = max(0.0, min(1.0, (timeline_ms - transition_start) / overlap))
        previous_local = max(0, int(timeline_ms - starts[index - 1]))
        next_local = max(0, int(timeline_ms - transition_start))
        previous_frame = render_clip_frame(previous_clip, previous_local, width, height)
        next_frame = render_clip_frame(next_clip, next_local, width, height)
        try:
            if next_clip.get("transition") == "fade":
                black = Image.new("RGB", (width, height), (0, 0, 0))
                try:
                    if progress < 0.5:
                        return Image.blend(previous_frame, black, progress * 2)
                    return Image.blend(black, next_frame, (progress - 0.5) * 2)
                finally:
                    black.close()
            return Image.blend(previous_frame, next_frame, progress)
        finally:
            previous_frame.close()
            next_frame.close()

    active = 0
    for index, start in enumerate(starts):
        if start <= timeline_ms:
            active = index
        else:
            break
    clip = clips[active]
    local = min(int(clip["duration_ms"]), max(0, int(timeline_ms - starts[active])))
    return render_clip_frame(clip, local, width, height)


def render_manifest_frames(manifest: dict, output_dir: Path) -> int:
    width, height = int(manifest.get("width", 1280)), int(manifest.get("height", 720))
    fps = int(manifest.get("fps", 24))
    clips = manifest.get("clips") or []
    if not clips or width < 320 or height < 180 or width > 1920 or height > 1080 or fps not in (12, 24, 30):
        raise ValueError("Headless animatic manifest has unsupported dimensions, frame rate, or no clips.")
    starts = [0]
    for index, clip in enumerate(clips):
        duration = int(clip.get("duration_ms", 0))
        if duration <= 0:
            raise ValueError("Headless animatic clips must have a positive duration.")
        if index == 0:
            continue
        overlap = int(clip.get("transition_duration_ms", 0))
        if overlap < 0 or overlap > min(int(clips[index - 1]["duration_ms"]), duration) // 2:
            raise ValueError("Headless animatic transition duration is invalid.")
        if clip.get("transition", "cut") not in ("cut", "fade", "dissolve"):
            raise ValueError("Headless animatic contains an unsupported transition.")
        starts.append(starts[-1] + int(clips[index - 1]["duration_ms"]) - overlap)
    duration_ms = starts[-1] + int(clips[-1]["duration_ms"])
    frame_count = max(1, math.ceil(duration_ms * fps / 1000))
    if frame_count > 14400:
        raise ValueError("Headless animatic exceeds the 10-minute frame budget.")
    output_dir.mkdir(parents=True, exist_ok=True)
    for frame_index in range(frame_count):
        timeline_ms = frame_index * 1000 / fps
        frame = render_timeline_frame(clips, starts, timeline_ms, width, height)
        try:
            frame.save(output_dir / f"frame-{frame_index + 1:06d}.jpg", quality=88, optimize=False)
        finally:
            frame.close()
    return frame_count

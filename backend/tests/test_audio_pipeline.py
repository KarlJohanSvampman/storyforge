import os

from fastapi.testclient import TestClient

from app.main import app
from test_editorial import _finalized_take
from test_scene_runtime import _scene_with_casting

client = TestClient(app)


def _production_sequence(label: str):
    _, project_id, scene_id, _, _ = _scene_with_casting(label)
    run = client.post(f"/api/projects/{project_id}/scene-runs", json={"scene_id": scene_id}).json()
    activated = client.post(
        f"/api/projects/{project_id}/production/activate",
        json={"reason": "Audio pipeline integration test."},
    )
    assert activated.status_code == 200, activated.text
    take_id = _finalized_take(project_id, scene_id, run["id"], "Audio source video take", 1200)
    selected = client.post(f"/api/projects/{project_id}/takes/{take_id}/select")
    assert selected.status_code == 200, selected.text
    sequence = client.post(
        f"/api/projects/{project_id}/edit-sequences",
        json={"name": "Audio assembly"},
    )
    assert sequence.status_code == 201, sequence.text
    return project_id, sequence.json()


def test_audio_asset_track_clip_and_edl_export(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    project_id, sequence = _production_sequence("Audio pipeline end-to-end")

    raw_audio = b"RIFF\x24\x00\x00\x00WAVEfmt "
    upload = client.post(
        f"/api/projects/{project_id}/production/media",
        data={"title": "Opening theme", "duration_ms": "5000"},
        files={"file": ("opening.wav", raw_audio, "audio/wav")},
    )
    assert upload.status_code == 201, upload.text
    asset = upload.json()
    assert asset["content_type"] == "audio/wav"
    assert asset["duration_ms"] == 5000

    downloaded = client.get(asset["download_url"])
    assert downloaded.status_code == 200
    assert downloaded.content == raw_audio

    track_response = client.post(
        f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/audio-tracks",
        json={"name": "Music", "role": "music", "gain": 0.8, "pan": 0},
    )
    assert track_response.status_code == 201, track_response.text
    track = track_response.json()

    clip_response = client.post(
        f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/audio-tracks/{track['id']}/clips",
        json={
            "media_asset_id": asset["id"], "source_in_ms": 250, "source_out_ms": 4250,
            "timeline_start_ms": 500, "gain": 0.9, "fade_in_ms": 300, "fade_out_ms": 500,
        },
    )
    assert clip_response.status_code == 201, clip_response.text
    assert clip_response.json()["clips"][0]["timeline_start_ms"] == 500

    update = client.patch(
        f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/audio-tracks/{track['id']}",
        json={"muted": False, "solo": True, "pan": -0.25},
    )
    assert update.status_code == 200, update.text
    assert update.json()["solo"] is True

    export = client.post(f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/export")
    assert export.status_code == 201, export.text
    manifest = export.json()["manifest"]
    assert manifest["format_version"] == 2
    assert manifest["audio_duration_ms"] == 4500
    assert manifest["audio_tracks"][0]["role"] == "music"
    assert manifest["audio_tracks"][0]["solo"] is True
    exported_clip = manifest["audio_tracks"][0]["clips"][0]
    assert exported_clip["media_asset_id"] == asset["id"]
    assert exported_clip["source_in_ms"] == 250
    assert exported_clip["timeline_start_ms"] == 500
    assert exported_clip["fade_in_ms"] == 300


def test_audio_upload_and_clip_validation_and_project_isolation(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    project_id, sequence = _production_sequence("Audio pipeline isolation")
    other_project_id, _ = _production_sequence("Audio pipeline other project")

    bad_format = client.post(
        f"/api/projects/{project_id}/production/media",
        data={"title": "Not audio"},
        files={"file": ("notes.txt", b"not audio", "text/plain")},
    )
    assert bad_format.status_code == 415

    upload = client.post(
        f"/api/projects/{project_id}/production/media",
        data={"title": "Short sound", "duration_ms": "1000"},
        files={"file": ("sound.wav", b"RIFFWAVE", "audio/wav")},
    )
    assert upload.status_code == 201, upload.text
    asset = upload.json()

    track = client.post(
        f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/audio-tracks",
        json={"name": "Effects", "role": "effects"},
    ).json()
    wrong_project = client.post(
        f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/audio-tracks/{track['id']}/clips",
        json={"media_asset_id": "00000000-0000-0000-0000-000000000001", "source_out_ms": 500},
    )
    assert wrong_project.status_code == 404

    beyond_source = client.post(
        f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/audio-tracks/{track['id']}/clips",
        json={"media_asset_id": asset["id"], "source_out_ms": 1500},
    )
    assert beyond_source.status_code == 422

    foreign_download = client.get(f"/api/projects/{other_project_id}/production/media/{asset['id']}/download")
    assert foreign_download.status_code == 404

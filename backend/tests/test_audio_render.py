from app.audio_render_worker import _render_command
from test_audio_pipeline import _production_sequence, client


def test_audio_render_job_captures_an_immutable_mix_snapshot(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    project_id, sequence = _production_sequence("Audio render job snapshot")
    upload = client.post(
        f"/api/projects/{project_id}/production/media",
        data={"title": "Render source", "duration_ms": "3000"},
        files={"file": ("render.wav", b"RIFFWAVE", "audio/wav")},
    )
    assert upload.status_code == 201, upload.text
    asset = upload.json()
    track = client.post(
        f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/audio-tracks",
        json={"name": "Dialogue", "role": "dialogue", "gain": 0.75, "pan": 0.2},
    )
    assert track.status_code == 201, track.text
    track_data = track.json()
    clip = client.post(
        f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/audio-tracks/{track_data['id']}/clips",
        json={
            "media_asset_id": asset["id"], "source_in_ms": 100, "source_out_ms": 2500,
            "timeline_start_ms": 400, "gain": 0.8, "fade_in_ms": 200, "fade_out_ms": 300,
        },
    )
    assert clip.status_code == 201, clip.text

    queued = client.post(
        f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/audio-renders",
    )
    assert queued.status_code == 202, queued.text
    job = queued.json()
    assert job["status"] == "queued"
    assert job["sequence_revision"] >= 3
    assert job["duration_ms"] == 2800
    assert job["download_url"] is None

    listed = client.get(
        f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/audio-renders",
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == job["id"]
    unavailable = client.get(f"/api/projects/{project_id}/audio-renders/{job['id']}/download")
    assert unavailable.status_code == 409


def test_audio_render_requires_an_audible_clip():
    project_id, sequence = _production_sequence("Audio render requires clips")
    response = client.post(
        f"/api/projects/{project_id}/edit-sequences/{sequence['id']}/audio-renders",
    )
    assert response.status_code == 409
    assert "at least one audible clip" in response.json()["detail"]


def test_ffmpeg_command_contains_trim_fade_pan_delay_and_mix(monkeypatch, tmp_path):
    source = tmp_path / "source.wav"
    source.write_bytes(b"source")
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    monkeypatch.setattr("app.audio_render_worker.shutil.which", lambda _name: "/usr/bin/ffmpeg")
    manifest = {
        "duration_ms": 3000, "sample_rate": 48000, "channels": 2,
        "tracks": [{
            "gain": 0.75, "pan": -0.25,
            "clips": [{
                "storage_key": "source.wav", "media_asset_id": "asset-1", "filename": "source.wav",
                "source_in_ms": 100, "source_out_ms": 2100, "timeline_start_ms": 500,
                "gain": 0.8, "fade_in_ms": 250, "fade_out_ms": 400,
            }],
        }],
    }
    command = _render_command(manifest, tmp_path / "mix.wav")
    graph = command[command.index("-filter_complex") + 1]
    assert "atrim=start=0.100000:duration=2.000000" in graph
    assert "afade=t=in:st=0:d=0.250000" in graph
    assert "afade=t=out:st=1.600000:d=0.400000" in graph
    assert "adelay=500|500" in graph
    assert "amix=inputs=1" in graph
    assert command[-1].endswith("mix.wav")

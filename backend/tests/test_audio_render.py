import hashlib
import math
import shutil
import struct
import wave

import pytest

from app.audio_render_worker import _render_command, render_audio_manifest
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
                "sha256": hashlib.sha256(b"source").hexdigest(),
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
    assert "pan=stereo|c0=1.000000*c0|c1=0.750000*c1" in graph
    assert "adelay=500|500" in graph
    assert "apad=whole_dur=3.000000" in graph
    assert "amix=inputs=1" in graph
    assert command[-1].endswith("mix.wav")



def test_ffmpeg_command_rejects_modified_source_asset(monkeypatch, tmp_path):
    source = tmp_path / "source.wav"
    source.write_bytes(b"modified")
    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    monkeypatch.setattr("app.audio_render_worker.shutil.which", lambda _name: "/usr/bin/ffmpeg")
    manifest = {
        "duration_ms": 1000,
        "tracks": [{
            "gain": 1, "pan": 0,
            "clips": [{
                "storage_key": "source.wav", "media_asset_id": "asset-2",
                "sha256": hashlib.sha256(b"original").hexdigest(),
                "source_in_ms": 0, "source_out_ms": 1000,
                "timeline_start_ms": 0, "gain": 1,
            }],
        }],
    }
    with pytest.raises(RuntimeError, match="SHA-256 integrity check"):
        _render_command(manifest, tmp_path / "out.wav")



@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg is not installed in this test environment.")
def test_ffmpeg_renderer_produces_a_stereo_24_bit_wav(tmp_path, monkeypatch):
    source = tmp_path / "tone.wav"
    sample_rate = 48000
    frames = bytearray()
    for index in range(sample_rate):
        sample = int(math.sin(2 * math.pi * 440 * index / sample_rate) * 12000)
        frames.extend(struct.pack("<h", sample))
    with wave.open(str(source), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(bytes(frames))

    monkeypatch.setenv("STORYFORGE_PRODUCTION_MEDIA_DIR", str(tmp_path))
    manifest = {
        "duration_ms": 1250, "sample_rate": sample_rate, "channels": 2,
        "tracks": [{
            "gain": 0.8, "pan": 0.25,
            "clips": [{
                "storage_key": "tone.wav", "media_asset_id": "tone",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "source_in_ms": 0, "source_out_ms": 1000,
                "timeline_start_ms": 250, "gain": 0.9,
                "fade_in_ms": 100, "fade_out_ms": 100,
            }],
        }],
    }
    output = tmp_path / "renders" / "mix.wav"
    size, digest = render_audio_manifest(manifest, output)
    assert size == output.stat().st_size and size > 44
    assert digest == hashlib.sha256(output.read_bytes()).hexdigest()
    with wave.open(str(output), "rb") as rendered:
        assert rendered.getnchannels() == 2
        assert rendered.getsampwidth() == 3
        assert rendered.getframerate() == sample_rate
        assert rendered.getnframes() == 60000

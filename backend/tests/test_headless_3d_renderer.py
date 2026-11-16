from pathlib import Path

from PIL import Image

from app import headless_3d_renderer


class FakePage:
    def __init__(self):
        self.manifest = None
        self.rendered = []
        self.visited = None

    def set_default_timeout(self, _timeout):
        pass

    def goto(self, url, **_kwargs):
        self.visited = url

    def wait_for_function(self, *_args, **_kwargs):
        pass

    def evaluate(self, script, argument=None):
        if "initialize(manifest)" in script:
            self.manifest = argument
            return {"frame_count": 3}
        if "renderFrame(index)" in script:
            self.rendered.append(argument)
            return None
        return None

    def locator(self, selector):
        assert selector == "#frame"
        return self

    def screenshot(self, path, **_kwargs):
        Image.new("RGB", (640, 360), (24, 36, 28)).save(path)


class FakeBrowser:
    def __init__(self):
        self.page = FakePage()
        self.closed = False

    def new_page(self, **_kwargs):
        return self.page

    def close(self):
        self.closed = True


class FakeChromium:
    def __init__(self):
        self.browser = FakeBrowser()
        self.launch_args = None

    def launch(self, **kwargs):
        self.launch_args = kwargs
        return self.browser


class FakePlaywright:
    def __init__(self):
        self.chromium = FakeChromium()


class FakePlaywrightContext:
    def __init__(self, playwright):
        self.playwright = playwright

    def __enter__(self):
        return self.playwright

    def __exit__(self, *_args):
        return False


def _manifest():
    return {
        "renderer": "storyforge-headless-3d-v1",
        "width": 640,
        "height": 360,
        "fps": 12,
        "duration_ms": 250,
        "clips": [
            {"in_ms": 0, "duration_ms": 250, "cast_members": [], "events": []},
        ],
    }


def test_headless_3d_renderer_captures_deterministic_png_frames(monkeypatch, tmp_path):
    fake = FakePlaywright()
    monkeypatch.setattr(
        headless_3d_renderer,
        "sync_playwright",
        lambda: FakePlaywrightContext(fake),
    )
    monkeypatch.setenv(
        "STORYFORGE_HEADLESS_RENDERER_URL",
        "http://frontend:5173/headless-render.html",
    )

    count = headless_3d_renderer.render_manifest_frames(_manifest(), tmp_path / "frames")

    assert count == 3
    assert fake.chromium.browser.closed
    assert fake.chromium.browser.page.visited.endswith("/headless-render.html")
    assert fake.chromium.browser.page.rendered == [0, 1, 2]
    assert len(list((tmp_path / "frames").glob("frame-*.png"))) == 3


def test_headless_3d_renderer_rejects_wrong_manifest_before_launch(monkeypatch, tmp_path):
    fake = FakePlaywright()
    monkeypatch.setattr(
        headless_3d_renderer,
        "sync_playwright",
        lambda: FakePlaywrightContext(fake),
    )
    manifest = _manifest()
    manifest["renderer"] = "storyforge-headless-animatic-v1"

    try:
        headless_3d_renderer.render_manifest_frames(manifest, tmp_path / "frames")
    except ValueError as error:
        assert "unsupported renderer" in str(error)
    else:
        raise AssertionError("Expected unsupported renderer manifest to be rejected.")
    assert fake.chromium.launch_args is None

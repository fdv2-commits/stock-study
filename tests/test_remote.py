"""GitHub 보관 기능 테스트 (실제 인터넷 연결 없이 가짜 응답으로 확인)."""
import base64

import pytest

import config
from storage import remote


class FakeResponse:
    def __init__(self, status, body=None):
        self.status_code = status
        self._body = body or {}

    def json(self):
        return self._body


@pytest.fixture
def on(monkeypatch):
    """보관 기능을 켠 상태(가짜 토큰·저장소)로 만든다."""
    values = {"GITHUB_DATA_TOKEN": "tok_abcdef", "GITHUB_DATA_REPO": "me/data"}
    monkeypatch.setattr(remote, "get_secret", lambda name: values.get(name))
    remote._sha.clear()


def test_설정이_없으면_꺼짐(monkeypatch, tmp_path):
    monkeypatch.setattr(remote, "get_secret", lambda name: None)
    called = []
    monkeypatch.setattr(remote, "_request", lambda *a, **k: called.append(a))
    path = tmp_path / "progress.json"
    path.write_text("{}", encoding="utf-8")
    assert not remote.enabled()
    assert remote.pull(path) is False
    remote.push(path, "x")
    assert called == []          # 인터넷 요청을 전혀 하지 않음


def test_저장소_안의_폴더_경로(tmp_path):
    assert remote.remote_path(tmp_path / "progress.json") == f"{config.REMOTE_DIR}/progress.json"


def test_내려받기(on, monkeypatch, tmp_path):
    content = base64.b64encode('{"questions": {}, "sessions": []}'.encode()).decode()
    urls = []

    def fake(method, url, **kw):
        urls.append(url)
        return FakeResponse(200, {"content": content, "sha": "s1"})

    monkeypatch.setattr(remote, "_request", fake)
    path = tmp_path / "progress.json"
    assert remote.pull(path) is True
    assert path.read_text(encoding="utf-8") == '{"questions": {}, "sessions": []}'
    assert urls[0].endswith(f"/repos/me/data/contents/{config.REMOTE_DIR}/progress.json")


def test_원격에_파일이_없으면_로컬_그대로(on, monkeypatch, tmp_path):
    monkeypatch.setattr(remote, "_request", lambda *a, **k: FakeResponse(404))
    path = tmp_path / "progress.json"
    path.write_text("local", encoding="utf-8")
    assert remote.pull(path) is False
    assert path.read_text(encoding="utf-8") == "local"


def test_올리기_다른_기기와_충돌하면_한번_더(on, monkeypatch, tmp_path):
    calls = []

    def fake(method, url, **kw):
        calls.append(method)
        if method == "GET":
            return FakeResponse(200, {"sha": f"sha{len(calls)}"})
        if calls.count("PUT") == 1:
            return FakeResponse(409)            # 첫 시도: 충돌
        return FakeResponse(200, {"content": {"sha": "new"}})

    monkeypatch.setattr(remote, "_request", fake)
    path = tmp_path / "progress.json"
    path.write_text("{}", encoding="utf-8")
    remote.push(path, "테스트")
    assert calls == ["GET", "PUT", "GET", "PUT"]


def test_실패해도_앱은_계속_오류메시지에_토큰_가림(on, monkeypatch, tmp_path):
    monkeypatch.setattr(remote, "_request", lambda *a, **k: FakeResponse(401, {"message": "bad tok_abcdef"}))
    monkeypatch.setattr(remote, "mask_secrets", lambda t: t.replace("tok_abcdef", "***"))
    path = tmp_path / "progress.json"
    remote.safe_pull(path)                      # 예외가 밖으로 나오지 않아야 함
    assert "401" in remote.last_error and "tok_abcdef" not in remote.last_error
    remote.last_error = None

"""학습 기록 파일을 비공개 GitHub 저장소에 보관하기 (배포용).

- st.secrets 또는 .env에 GITHUB_DATA_TOKEN과 GITHUB_DATA_REPO("내아이디/저장소이름")가 있으면 켜진다.
- 없으면 아무것도 하지 않는다 → 내 PC에서 실행할 때처럼 프로젝트 폴더의 파일만 쓴다.
- 파일은 저장소 안의 config.REMOTE_DIR 폴더에 둔다. (예: stock_study/progress.json)
- 앱을 처음 열 때 내려받고, 퀴즈를 끝내거나 몇 문제마다 올린다 (올릴 때마다 커밋 1개 = 자동 백업 기록).

스윙 대시보드의 data/remote.py를 바탕으로, 폴더 지정 기능을 넣어 단순하게 만든 것.
"""
import base64
import threading
from pathlib import Path

import requests

import config
from storage.keys import get_secret, mask_secrets

API = "https://api.github.com"
_lock = threading.Lock()
_sha: dict[str, str | None] = {}   # 원격 경로 → 마지막으로 알고 있는 파일 버전(sha)
last_error: str | None = None      # 마지막 동기화 오류 (화면 안내용)


class RemoteError(RuntimeError):
    pass


def settings() -> tuple[str, str, str] | None:
    """(토큰, 저장소, 브랜치) 또는 None(꺼짐). Actions용 이름(DATA_REPO_*)도 받는다."""
    token = get_secret("GITHUB_DATA_TOKEN") or get_secret("DATA_REPO_TOKEN")
    repo = get_secret("GITHUB_DATA_REPO") or get_secret("DATA_REPO_NAME")
    if not token or not repo:
        return None
    return token, repo, get_secret("GITHUB_DATA_BRANCH") or config.REMOTE_DEFAULT_BRANCH


def enabled() -> bool:
    return settings() is not None


def remote_path(path: Path) -> str:
    """로컬 파일 → 저장소 안의 경로. 예: progress.json → stock_study/progress.json"""
    return f"{config.REMOTE_DIR}/{path.name}" if config.REMOTE_DIR else path.name


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}


def _request(method: str, url: str, **kw) -> requests.Response:
    try:
        return requests.request(method, url, timeout=config.HTTP_TIMEOUT, **kw)
    except requests.RequestException as e:
        raise RemoteError(f"GitHub 연결 실패 ({type(e).__name__})") from None


def _fail(r: requests.Response, what: str) -> RemoteError:
    msg = ""
    try:
        msg = r.json().get("message", "")
    except Exception:
        pass
    return RemoteError(mask_secrets(f"GitHub {what} 실패: {r.status_code} {msg}"[:200]))


def _get(token: str, repo: str, branch: str, name: str) -> requests.Response:
    return _request("GET", f"{API}/repos/{repo}/contents/{name}", headers=_headers(token), params={"ref": branch})


def pull(path: Path) -> bool:
    """원격 파일을 내려받아 로컬 파일을 바꾼다. 돌려주는 값: 새로 받았는지. 꺼져 있으면 아무것도 안 함."""
    s = settings()
    if s is None:
        return False
    token, repo, branch = s
    name = remote_path(path)
    with _lock:
        r = _get(token, repo, branch, name)
        if r.status_code == 404:          # 아직 원격에 없음 → 로컬 그대로, 다음 저장 때 올라감
            _sha[name] = None
            return False
        if r.status_code != 200:
            raise _fail(r, "내려받기")
        body = r.json()
        if body.get("content"):
            data = base64.b64decode(body["content"])
        else:                             # 1MB가 넘으면 content가 비어 있어 원본 주소로 다시 받음
            raw = _request("GET", body["download_url"], headers={"Authorization": f"Bearer {token}"})
            if raw.status_code != 200:
                raise _fail(raw, "내려받기")
            data = raw.content
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
        _sha[name] = body.get("sha")
        return True


def _current_sha(token: str, repo: str, branch: str, name: str) -> str | None:
    r = _get(token, repo, branch, name)
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        raise _fail(r, "확인")
    return r.json().get("sha")


def push(path: Path, message: str) -> None:
    """로컬 파일을 원격에 올린다. 꺼져 있으면 아무것도 안 함. 실패하면 RemoteError."""
    s = settings()
    if s is None or not path.exists():
        return
    token, repo, branch = s
    name = remote_path(path)
    with _lock:
        if name not in _sha:
            _sha[name] = _current_sha(token, repo, branch, name)
        body = {"message": f"{config.REMOTE_COMMIT_PREFIX} {message}", "branch": branch,
                "content": base64.b64encode(path.read_bytes()).decode()}
        for attempt in range(2):
            if _sha.get(name):
                body["sha"] = _sha[name]
            r = _request("PUT", f"{API}/repos/{repo}/contents/{name}", headers=_headers(token), json=body)
            if r.status_code in (200, 201):
                _sha[name] = r.json()["content"]["sha"]
                return
            if r.status_code in (409, 422) and attempt == 0:
                # 다른 기기에서 먼저 바꿨음 → 최신 버전 번호로 한 번 더 (마지막 저장이 이김)
                _sha[name] = _current_sha(token, repo, branch, name)
                continue
            raise _fail(r, "저장")


def safe_pull(path: Path) -> None:
    """실패해도 앱은 계속 (로컬 파일로 진행, 오류는 last_error에 남김)."""
    global last_error
    try:
        pull(path)
        last_error = None
    except RemoteError as e:
        last_error = str(e)


def safe_push(path: Path, message: str) -> None:
    """실패해도 앱은 계속 (이 서버에는 저장됨, 오류는 last_error에 남김)."""
    global last_error
    try:
        push(path, message)
        last_error = None
    except RemoteError as e:
        last_error = str(e)

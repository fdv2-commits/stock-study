"""비밀값(토큰·비밀번호) 읽기. 로컬은 .env, 배포 환경은 st.secrets에서 읽는다.

값은 절대 코드에 직접 쓰지 않는다. (스윙 대시보드의 data/keys.py를 복사해 줄인 것)
"""
import os
import re
from pathlib import Path

from dotenv import dotenv_values

# 프로젝트 폴더의 .env 파일 위치
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

# 화면에 오류를 보여줄 때 가릴 비밀값 이름들
SECRET_NAMES = ("GITHUB_DATA_TOKEN", "APP_PASSWORD")


def get_secret(name: str) -> str | None:
    """이름으로 비밀값을 찾는다. 없으면 None. 순서: .env → 환경변수 → st.secrets"""
    if ENV_PATH.exists():
        value = dotenv_values(ENV_PATH).get(name)
        if value and value.strip():
            return value.strip()
    value = os.getenv(name)
    if value and value.strip():
        return value.strip()
    try:
        import streamlit as st
        value = st.secrets.get(name)  # secrets.toml이 없으면 예외가 날 수 있음
        return str(value).strip() if value else None
    except Exception:
        return None


def mask_secrets(text: str) -> str:
    """오류 메시지에 비밀값이 섞여 있으면 ***로 가린다."""
    for name in SECRET_NAMES:
        value = get_secret(name)
        if value and len(value) >= 6:
            text = text.replace(value, "***")
    return re.sub(r"(token|password)=[^&\s]+", r"\1=***", text, flags=re.I)

"""모든 기준값과 기본 설정을 모아 두는 곳.

숫자나 문구를 바꾸고 싶으면 이 파일만 고치면 된다.
"""
from pathlib import Path

# ── 경로 ─────────────────────────────────────────────
# 이 파일이 있는 폴더 = 프로젝트 폴더
BASE_DIR = Path(__file__).resolve().parent
CONTENT_DIR = BASE_DIR / "content"
CONCEPTS_FILE = CONTENT_DIR / "concepts.json"     # 개념 카드
QUESTIONS_FILE = CONTENT_DIR / "questions.json"   # 퀴즈 문제 은행
PROGRESS_FILE = BASE_DIR / "progress.json"        # 내 학습 기록 (git에 올리지 않음)

# ── 화면 문구 ─────────────────────────────────────────
APP_TITLE = "📚 주식 공부"
DISCLAIMER = "학습용 프로그램입니다. 투자 판단과 책임은 사용자에게 있습니다."

# ── 분류 (문제 은행의 category 값 → 화면 이름) ──────────
# 순서대로 화면에 표시된다. 새 분류를 만들면 여기에도 추가한다.
CATEGORIES = {
    "basic": "기초 용어",
    "chart": "캔들·차트",
    "indicator": "기술적 지표",
    "valuation": "가치평가",
    "risk": "리스크 관리",
    "market": "시장 제도 (한국·미국)",
}

# 난이도 (문제 은행의 level 값 → 화면 이름)
LEVELS = {
    1: "기초",
    2: "중급",
    3: "심화",
}

# ── 퀴즈 규칙 ─────────────────────────────────────────
CHOICES_PER_QUESTION = 4      # 문제마다 보기 개수
QUIZ_COUNT_OPTIONS = [5, 10, 20]   # 한 번에 풀 문제 수 선택지
QUIZ_DEFAULT_COUNT = 10            # 기본 문제 수 (위 선택지 중 하나)
SHUFFLE_CHOICES = True        # 보기 순서를 매번 섞을지

# 오답 노트: 틀린 문제를 연속으로 몇 번 맞혀야 오답 노트에서 빠지는지
MASTERY_STREAK = 2

# 학습 기록 화면에 보여줄 최근 퀴즈 수
RECENT_SESSIONS_SHOWN = 10

# 정답률 색 기준 (%) — 이 값 이상이면 초록, 그 아래 노랑 기준 이상이면 노랑, 나머지 빨강
ACCURACY_GOOD = 80
ACCURACY_OK = 60

# ── 차트 ─────────────────────────────────────────────
CHART_TEMPLATE = "plotly_dark"
COLOR_GOOD = "#22c55e"   # 초록
COLOR_OK = "#eab308"     # 노랑
COLOR_BAD = "#ef4444"    # 빨강
CHART_TEXT_INSIDE_MIN = 40   # 정답률이 이 값(%) 이상이면 막대 안에, 미만이면 막대 밖에 숫자 표시

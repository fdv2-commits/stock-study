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
# 기록 시간 기준 (배포 서버는 UTC라서 한국 시간으로 맞춤)
TIMEZONE = "Asia/Seoul"

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

# ── 지표 기준 ─────────────────────────────────────────
MA_SHORT = 20             # 짧은 이동평균(일)
MA_LONG = 60              # 긴 이동평균(일)
RSI_PERIOD = 14
BB_PERIOD = 20            # 볼린저밴드 기간
BB_STD = 2.0              # 볼린저밴드 표준편차 배수
ATR_PERIOD = 14
VOLUME_AVG_PERIOD = 20    # 거래량 평균 기간

# 지표 읽기 도움말 기준
RSI_OVERBOUGHT = 70       # 이 값 이상: 과매수
RSI_OVERSOLD = 30         # 이 값 이하: 과매도
RSI_PULLBACK_LOW = 40     # 눌림목 관심 구간 하단
RSI_PULLBACK_HIGH = 55    # 눌림목 관심 구간 상단
VOLUME_HIGH = 1.5         # 20일 평균의 이 배수 이상이면 '거래량 많음'
VOLUME_LOW = 0.7          # 이 배수 이하면 '거래량 적음'
BB_NEAR_EDGE_PCT = 20     # 볼린저 띠 안 위치가 하단에서 이 % 이내면 '하단 근처', 상단에서 이 % 이내면 '상단 근처'

# ── 차트 복기 연습 ────────────────────────────────────
# 무작위로 고를 대표 종목 (코드 → 이름). 자유롭게 추가·삭제 가능.
REPLAY_POOL_US = {
    "AAPL": "애플", "MSFT": "마이크로소프트", "NVDA": "엔비디아", "AMZN": "아마존", "GOOGL": "알파벳(구글)",
    "META": "메타", "TSLA": "테슬라", "AVGO": "브로드컴", "JPM": "JP모건", "V": "비자",
    "COST": "코스트코", "NFLX": "넷플릭스", "AMD": "AMD", "LLY": "일라이 릴리", "XOM": "엑슨모빌",
    "WMT": "월마트", "KO": "코카콜라", "DIS": "디즈니", "BA": "보잉", "INTC": "인텔",
}
REPLAY_POOL_KR = {
    "005930": "삼성전자", "000660": "SK하이닉스", "035420": "NAVER", "035720": "카카오", "005380": "현대차",
    "051910": "LG화학", "006400": "삼성SDI", "068270": "셀트리온", "105560": "KB금융", "207940": "삼성바이오로직스",
}
MARKETS = {"US": "미국", "KR": "한국"}
DEFAULT_MARKET = "US"            # 기본 시장 (미국 비중이 높아서)

REPLAY_DATA_YEARS = 10           # 몇 년치 일봉에서 구간을 고를지
REPLAY_CACHE_HOURS = 12          # 일봉 데이터 캐시 시간 (과거 데이터라 길게)
REPLAY_HISTORY_BARS = 120        # 판단 전에 보여줄 봉 수
REPLAY_FUTURE_BARS = 20          # 한 번 판단형: 판단 뒤 공개할 봉 수 (= 최대 보유 기간)
REPLAY_STEP_BARS = 40            # 한 봉씩 넘기기형: 넘길 봉 수
REPLAY_STOP_ATR_MULT = 2.0       # 추천 손절가 = 매수가 − ATR × 이 값
REPLAY_DEFAULT_RR = 2.0          # 추천 목표가의 손익비
REPLAY_FALLBACK_STOP_PCT = 5     # ATR을 구할 수 없을 때 추천 손절폭(%)
REPLAY_EXCLUDE_LATEST_BARS = 5   # 가장 최근 며칠은 구간에서 제외 (아직 확정 안 된 봉 방지)

# 캔들 색 (시장 관례: 한국 양봉 빨강·음봉 파랑, 미국 양봉 초록·음봉 빨강)
CANDLE_COLORS = {
    "KR": {"up": "#ef4444", "down": "#3b82f6"},
    "US": {"up": "#22c55e", "down": "#ef4444"},
}
CHART_HEIGHT = 560
COLOR_MA_SHORT = "#f59e0b"   # 20일선 (주황)
COLOR_MA_LONG = "#a855f7"    # 60일선 (보라)
COLOR_BB = "#64748b"         # 볼린저밴드 (회색)
COLOR_ENTRY = "#e6edf3"      # 매수가 선
COLOR_STOP = "#ef4444"       # 손절가 선
COLOR_TARGET = "#22c55e"     # 목표가 선
COLOR_RSI = "#38bdf8"        # RSI 선 (하늘)
COLOR_GUIDE = "#475569"      # RSI 30·70 기준선
COLOR_REVEAL = "#94a3b8"     # 판단 후 공개 구간 표시

# ── 전략 백테스트 ─────────────────────────────────────
BT_YEARS_OPTIONS = [3, 5, 10]    # 테스트 기간(년) 선택지 (REPLAY_DATA_YEARS 이하)
BT_DEFAULT_YEARS = 5

# 공통 매도 규칙 기본값 (화면에서 조절 가능)
BT_STOP_ATR_MULT = 2.0           # 손절 = 매수가 − ATR × 이 값
BT_TARGET_R = 2.0                # 목표 = 매수가 + 손절폭 × 이 값
BT_MAX_HOLD_DAYS = 20            # 최대 보유 거래일 (스윙 3~20일)
BT_MAX_HOLD_RANGE = (3, 60)
BT_STOP_MULT_RANGE = (1.0, 4.0, 0.5)   # 화면 슬라이더 (최소, 최대, 간격)
BT_TARGET_R_RANGE = (1.0, 4.0, 0.5)

# 전략별 숫자 기본값
BT_PULLBACK_RSI_LOW = RSI_PULLBACK_LOW
BT_PULLBACK_RSI_HIGH = RSI_PULLBACK_HIGH
BT_BREAKOUT_DAYS = 20            # 최근 며칠 최고가를 넘으면 돌파
BT_BREAKOUT_VOL_MULT = 1.5       # 거래량이 20일 평균의 몇 배 이상이어야 하는지
BT_OVERSOLD_LEVEL = RSI_OVERSOLD # RSI가 이 값을 아래에서 위로 넘으면 반등 신호

# 거래 비용: 한 번 사고팔 때(왕복) 빠지는 비율(%) = 수수료 + 세금 + 체결 차이(슬리피지)
# 대략값입니다. 내 증권사 수수료·현재 세율에 맞게 고쳐 쓰세요.
BT_COST_PCT = {"KR": 0.30, "US": 0.30}

# 내 자금 기준 시뮬레이션 (CLAUDE.md의 내 설정)
BT_CAPITAL = 3_000_000           # 총 투자금(원)
BT_RISK_PCT = 1.0                # 1회 최대 손실(총자금 대비 %)
BT_MAX_WEIGHT_PCT = 25.0         # 종목당 최대 비중(%)

# 결과 색 기준
BT_GOOD_AVG_R = 0.2              # 평균 R이 이 값 이상이면 초록, 0 초과면 노랑, 그 이하 빨강
BT_MIN_TRADES = 30               # 거래 수가 이보다 적으면 '우연일 수 있음' 경고
BT_TRADES_SHOWN = 30             # 거래 목록에 보여줄 최근 거래 수
COLOR_EQUITY = "#38bdf8"         # 자금 곡선 색
BT_EQUITY_CHART_HEIGHT = 260
BT_PRICE_CHART_HEIGHT = 300

# ── 배포용 GitHub 보관 (학습 기록) ─────────────────────
# Streamlit Cloud는 재시작하면 폴더의 파일이 사라지므로 학습 기록을 비공개 GitHub 저장소에 보관한다.
# 토큰·저장소 이름은 st.secrets(배포) 또는 .env(로컬)의 GITHUB_DATA_TOKEN / GITHUB_DATA_REPO.
# 둘 다 없으면 보관 기능은 꺼지고 내 PC의 progress.json만 쓴다.
REMOTE_DIR = "stock_study"          # 데이터 저장소 안의 폴더 이름 (스윙 대시보드 파일과 섞이지 않게)
REMOTE_DEFAULT_BRANCH = "main"
REMOTE_COMMIT_PREFIX = "[주식공부]"
REMOTE_PUSH_EVERY = 5               # 퀴즈 도중에는 이 문제 수마다 올림 (끝나거나 그만둘 때도 올림)
HTTP_TIMEOUT = 15                   # 인터넷 요청 제한 시간(초)

# ── 차트 ─────────────────────────────────────────────
CHART_TEMPLATE = "plotly_dark"
COLOR_GOOD = "#22c55e"   # 초록
COLOR_OK = "#eab308"     # 노랑
COLOR_BAD = "#ef4444"    # 빨강
CHART_TEXT_INSIDE_MIN = 40   # 정답률이 이 값(%) 이상이면 막대 안에, 미만이면 막대 밖에 숫자 표시

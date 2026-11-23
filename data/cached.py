"""화면에서 쓰는 시세 캐시 (복기 탭과 전략 탭이 함께 쓴다)."""
import streamlit as st

import config
from data.prices import PriceError, fetch_daily
from indicators.core import add_indicators


@st.cache_data(ttl=config.REPLAY_CACHE_HOURS * 3600, show_spinner="시세를 불러오는 중…")
def load_prices(symbol: str, market: str):
    """일봉 + 지표. (데이터, 오류 메시지) — 실패해도 앱이 멈추지 않게 오류는 글자로 돌려준다."""
    try:
        return add_indicators(fetch_daily(symbol, market)), None
    except PriceError as e:
        return None, str(e)


def fmt_price(market: str, value: float) -> str:
    """가격 표시: 한국은 원(정수), 미국은 달러(소수 둘째 자리)."""
    return f"{value:,.0f}원" if market == "KR" else f"${value:,.2f}"


def stock_name(symbol: str, market: str) -> str:
    """대표 종목이면 '이름 (코드)', 아니면 코드."""
    pool = config.REPLAY_POOL_KR if market == "KR" else config.REPLAY_POOL_US
    return f"{pool[symbol]} ({symbol})" if symbol in pool else symbol

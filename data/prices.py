"""일봉 시세 가져오기 (streamlit과 무관한 순수 함수).

- 한국 주식: FinanceDataReader
- 미국 주식: yfinance (분할·배당 조정 가격)
스윙 대시보드의 data/prices.py를 바탕으로 줄인 것. 실패하면 PriceError(한국어 안내)를 올린다.
"""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

import config

OHLCV = ["Open", "High", "Low", "Close", "Volume"]


class PriceError(Exception):
    """시세를 못 가져왔을 때. 화면에 그대로 보여줄 수 있는 한국어 메시지를 담는다."""


def detect_market(symbol: str) -> str:
    """숫자 6자리면 한국(KR), 아니면 미국(US)."""
    return "KR" if re.fullmatch(r"\d{6}", symbol.strip()) else "US"


def normalize_symbol(symbol: str) -> str:
    """입력값 정리: 앞뒤 공백 제거, 미국 티커는 대문자."""
    s = symbol.strip()
    return s if detect_market(s) == "KR" else s.upper()


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """열 이름·형식을 통일하고, 이상한 행을 정리한다."""
    if df is None or df.empty:
        return pd.DataFrame(columns=OHLCV)
    df = df[[c for c in OHLCV if c in df.columns]].copy()
    df = df.astype(float)
    idx = pd.to_datetime(df.index)
    if idx.tz is not None:          # 시간대 정보 제거 (날짜만 남김)
        idx = idx.tz_localize(None)
    df.index = idx.normalize()
    df.index.name = "Date"
    df = df[df["Close"] > 0].dropna(subset=["Close"])
    # 거래정지 등으로 시가·고가·저가가 0인 날은 종가로 채움
    for col in ("Open", "High", "Low"):
        bad = df[col] <= 0
        df.loc[bad, col] = df.loc[bad, "Close"]
    return df[~df.index.duplicated(keep="last")].sort_index()


def fetch_daily(symbol: str, market: str, years: int = config.REPLAY_DATA_YEARS) -> pd.DataFrame:
    """종목의 최근 years년 일봉. 실패하거나 데이터가 없으면 PriceError."""
    start = (datetime.now(ZoneInfo(config.TIMEZONE)) - timedelta(days=365 * years)).strftime("%Y-%m-%d")
    try:
        if market == "KR":
            import FinanceDataReader as fdr
            raw = fdr.DataReader(symbol, start)
        else:
            import yfinance as yf
            raw = yf.Ticker(symbol).history(start=start, auto_adjust=True)
    except Exception as e:   # 인터넷 오류, 잘못된 코드 등 (라이브러리마다 예외 종류가 달라 넓게 잡음)
        raise PriceError(f"{symbol} 시세를 가져오지 못했습니다. ({type(e).__name__})") from None
    df = clean(raw)
    if df.empty:
        raise PriceError(f"{symbol} 시세가 없습니다. 종목 코드를 확인해 주세요. (미국: AAPL, 한국: 005930)")
    return df

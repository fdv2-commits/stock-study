"""지표 계산 함수 모음. 외부 지표 라이브러리 없이 pandas/numpy로 직접 계산한다.

스윙 대시보드(swing_dashboard/indicators/core.py)에서 복사해 온 것 (테스트도 함께 복사).
입력은 모두 pandas Series(날짜 순서대로 정렬된 일봉)이다.
"""
import numpy as np
import pandas as pd

import config


def sma(series: pd.Series, period: int) -> pd.Series:
    """단순 이동평균: 최근 period일 값의 평균."""
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """지수 이동평균: 최근 값에 더 큰 가중치. 가중치 = 2 / (period + 1)."""
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    """
    와일더(Wilder) 평활: RSI·ATR·ADX에 쓰는 방식.
    - 첫 값 = 처음 period개 값의 단순 평균
    - 그다음 = (이전 값 × (period-1) + 오늘 값) ÷ period
    """
    values = series.to_numpy(dtype=float)
    result = np.full(len(values), np.nan)
    # 앞쪽의 빈 값(NaN)은 건너뛰고, 값이 있는 첫 위치부터 계산
    valid = np.where(~np.isnan(values))[0]
    if len(valid) < period:
        return pd.Series(result, index=series.index)
    start = valid[0]
    seed_end = start + period - 1
    result[seed_end] = np.mean(values[start:seed_end + 1])
    for i in range(seed_end + 1, len(values)):
        result[i] = (result[i - 1] * (period - 1) + values[i]) / period
    return pd.Series(result, index=series.index)


def bollinger(close: pd.Series, period: int = config.BB_PERIOD, num_std: float = config.BB_STD) -> pd.DataFrame:
    """
    볼린저밴드.
    - 중심선 = 20일 이동평균
    - 상단/하단 = 중심선 ± 2 × 표준편차 (모집단 표준편차, 대부분의 차트 프로그램과 같음)
    - 폭(width) = (상단 - 하단) ÷ 중심선
    """
    mid = sma(close, period)
    std = close.rolling(window=period, min_periods=period).std(ddof=0)
    upper = mid + num_std * std
    lower = mid - num_std * std
    width = (upper - lower) / mid
    return pd.DataFrame({"bb_mid": mid, "bb_upper": upper, "bb_lower": lower, "bb_width": width})


def rsi(close: pd.Series, period: int = config.RSI_PERIOD) -> pd.Series:
    """
    RSI(상대강도지수), 와일더 방식.
    - 오른 날의 상승폭 평균과 내린 날의 하락폭 평균을 와일더 평활
    - RSI = 100 - 100 ÷ (1 + 평균상승 ÷ 평균하락)
    """
    diff = close.diff()
    gain = diff.clip(lower=0)
    loss = (-diff).clip(lower=0)
    avg_gain = wilder_smooth(gain, period)
    avg_loss = wilder_smooth(loss, period)
    rs = avg_gain / avg_loss
    out = 100 - 100 / (1 + rs)
    # 하락이 한 번도 없으면 RSI 100
    out = out.where(avg_loss != 0, 100.0)
    return out.where(avg_gain.notna())


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """
    실제 변동폭(TR) = 다음 셋 중 가장 큰 값
    - 오늘 고가 - 오늘 저가
    - |오늘 고가 - 어제 종가|
    - |오늘 저가 - 어제 종가|
    (첫날은 어제 종가가 없으니 고가 - 저가)
    """
    prev_close = close.shift(1)
    ranges = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1)
    return ranges.max(axis=1, skipna=True)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = config.ATR_PERIOD) -> pd.Series:
    """ATR(평균 실제 변동폭) = TR의 와일더 평활."""
    return wilder_smooth(true_range(high, low, close), period)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """일봉(Open·High·Low·Close·Volume)에 차트 복기용 지표 열을 붙여 돌려준다."""
    out = df.copy()
    out["ma_short"] = sma(out["Close"], config.MA_SHORT)
    out["ma_long"] = sma(out["Close"], config.MA_LONG)
    out = out.join(bollinger(out["Close"]))
    out["rsi"] = rsi(out["Close"])
    out["atr"] = atr(out["High"], out["Low"], out["Close"])
    out["vol_avg"] = sma(out["Volume"], config.VOLUME_AVG_PERIOD)
    return out

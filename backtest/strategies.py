"""매수 신호(전략) 모음.

각 전략은 일봉 표(지표 열 포함)를 받아, 날마다 '오늘 종가 기준으로 매수 신호가 났는지'(True/False)를 돌려준다.
실제 매수는 신호가 난 다음 날 시가에 한다(backtest/engine.py). 오늘 종가를 보고 오늘 종가에 사는 것은
현실에서 어렵고, 미래 데이터를 미리 보는 실수가 되기 쉽기 때문이다.
"""
import pandas as pd

import config


def pullback(df: pd.DataFrame, rsi_low: float, rsi_high: float) -> pd.Series:
    """눌림목: 상승 추세(종가 > 60일선, 20일선 > 60일선)에서 RSI가 rsi_low~rsi_high로 쉬어갈 때."""
    uptrend = (df["Close"] > df["ma_long"]) & (df["ma_short"] > df["ma_long"])
    return uptrend & df["rsi"].between(rsi_low, rsi_high)


def breakout(df: pd.DataFrame, days: int, vol_mult: float) -> pd.Series:
    """돌파: 종가가 최근 days일(오늘 제외) 최고가를 넘고, 거래량이 20일 평균의 vol_mult배 이상일 때."""
    prev_high = df["High"].shift(1).rolling(int(days), min_periods=int(days)).max()
    return (df["Close"] > prev_high) & (df["Volume"] >= df["vol_avg"] * vol_mult)


def golden_cross(df: pd.DataFrame) -> pd.Series:
    """골든크로스: 20일선이 60일선을 아래에서 위로 뚫은 날."""
    above = df["ma_short"] > df["ma_long"]
    # 전날 이동평균이 계산돼 있어야 '뚫었다'고 말할 수 있다 (데이터 맨 앞에서 가짜 신호 방지)
    prev_ok = df["ma_short"].shift(1).notna() & df["ma_long"].shift(1).notna()
    return above & ~above.shift(1, fill_value=True) & prev_ok


def oversold_bounce(df: pd.DataFrame, level: float) -> pd.Series:
    """RSI 과매도 반등: RSI가 level 아래에 있다가 위로 올라선 날."""
    return (df["rsi"] >= level) & (df["rsi"].shift(1) < level)


# 화면에 보여줄 전략 목록
# params: 이름 → (화면 이름, 기본값, 최솟값, 최댓값, 간격)
STRATEGIES = {
    "pullback": {
        "name": "눌림목",
        "desc": f"상승 추세(종가 > {config.MA_LONG}일선, {config.MA_SHORT}일선 > {config.MA_LONG}일선)에서 "
                "RSI가 정한 구간으로 내려와 쉬어갈 때 매수",
        "func": pullback,
        "params": {
            "rsi_low": ("RSI 하단", config.BT_PULLBACK_RSI_LOW, 20, 60, 1),
            "rsi_high": ("RSI 상단", config.BT_PULLBACK_RSI_HIGH, 30, 70, 1),
        },
    },
    "breakout": {
        "name": "돌파",
        "desc": "종가가 최근 며칠 최고가를 넘고, 거래량이 평소보다 많을 때 매수",
        "func": breakout,
        "params": {
            "days": ("최근 며칠 최고가", config.BT_BREAKOUT_DAYS, 5, 120, 5),
            "vol_mult": ("거래량 배수 (20일 평균 대비)", config.BT_BREAKOUT_VOL_MULT, 1.0, 3.0, 0.1),
        },
    },
    "golden_cross": {
        "name": "골든크로스",
        "desc": f"{config.MA_SHORT}일선이 {config.MA_LONG}일선을 아래에서 위로 뚫은 다음 날 매수",
        "func": golden_cross,
        "params": {},
    },
    "oversold": {
        "name": "RSI 과매도 반등",
        "desc": "RSI가 과매도 기준 아래에 있다가 다시 위로 올라선 다음 날 매수 (추세와 반대 방향 매매)",
        "func": oversold_bounce,
        "params": {
            "level": ("과매도 기준", config.BT_OVERSOLD_LEVEL, 10, 45, 1),
        },
    },
}


def signals(df: pd.DataFrame, key: str, params: dict) -> pd.Series:
    """전략 이름과 숫자로 매수 신호를 계산한다. 지표가 아직 없는 앞쪽(NaN)은 False."""
    out = STRATEGIES[key]["func"](df, **params)
    return out.fillna(False).astype(bool)

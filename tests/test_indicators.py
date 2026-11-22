"""
지표 계산 테스트: 알려진 값(교과서 예제·손계산)과 비교한다.
실행: .venv\\Scripts\\python -m pytest
"""
import math

import numpy as np
import pandas as pd
import pytest

from indicators.core import add_indicators, atr, bollinger, ema, rsi, sma, true_range, wilder_smooth

# StockCharts.com의 RSI 설명 자료에 실린 예제 종가 (Wilder 방식 RSI 14)
RSI_CLOSES = [44.3389, 44.0902, 44.1497, 43.6124, 44.3278, 44.8264, 45.0955, 45.4245, 45.8433, 46.0826,
              45.8931, 46.0328, 45.6140, 46.2820, 46.2820, 46.0028, 46.0328, 46.4116, 46.2222, 45.6439,
              46.2122, 46.2521, 45.7137, 46.4515, 45.7835, 45.3548, 44.0288, 44.1783, 44.2181, 44.5672,
              43.4205, 42.6628, 43.1314]
# 같은 자료의 RSI 결과 (15번째 종가부터)
RSI_EXPECTED = [70.53, 66.32, 66.55, 69.41, 66.36, 57.97, 62.93, 63.26, 56.06, 62.38, 54.71, 50.42,
                39.99, 41.46, 41.87, 45.46, 37.30, 33.08, 37.77]


def test_sma_hand():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    out = sma(s, 3)
    assert out.iloc[:2].isna().all()
    assert out.iloc[2:].tolist() == [2.0, 3.0, 4.0]


def test_ema_hand():
    # 기간 3 → 가중치 0.5: 1, 1.5, 2.25, 3.125, 4.0625 (앞 2개는 기간 부족으로 빈 값)
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    out = ema(s, 3)
    assert out.iloc[:2].isna().all()
    assert out.iloc[2:].tolist() == pytest.approx([2.25, 3.125, 4.0625])


def test_wilder_smooth_hand():
    s = pd.Series([2, 3, 5, 2], dtype=float)
    out = wilder_smooth(s, 3)
    assert out.iloc[2] == pytest.approx(10 / 3)               # 첫 값 = 평균(2,3,5)
    assert out.iloc[3] == pytest.approx((10 / 3 * 2 + 2) / 3)  # (이전×2 + 오늘) ÷ 3


def test_rsi_known_values():
    out = rsi(pd.Series(RSI_CLOSES), 14)
    assert out.iloc[:14].isna().all()
    assert out.iloc[14:].round(2).tolist() == pytest.approx(RSI_EXPECTED, abs=0.01)


def test_rsi_all_up_is_100():
    out = rsi(pd.Series(np.arange(1, 40, dtype=float)), 14)
    assert out.iloc[-1] == pytest.approx(100.0)


def test_bollinger_hand():
    bb = bollinger(pd.Series([1, 2, 3], dtype=float), period=3, num_std=2)
    std = math.sqrt(2 / 3)  # 모집단 표준편차
    assert bb["bb_mid"].iloc[-1] == pytest.approx(2.0)
    assert bb["bb_upper"].iloc[-1] == pytest.approx(2 + 2 * std)
    assert bb["bb_lower"].iloc[-1] == pytest.approx(2 - 2 * std)
    assert bb["bb_width"].iloc[-1] == pytest.approx(4 * std / 2)


def test_true_range_and_atr_hand():
    high = pd.Series([10, 12, 16, 15], dtype=float)
    low = pd.Series([8, 9, 14, 13], dtype=float)
    close = pd.Series([9, 11, 15, 14], dtype=float)
    # TR: 2(첫날 고-저), 3(고-저), 5(고가-전일종가 갭), 2
    assert true_range(high, low, close).tolist() == [2, 3, 5, 2]
    a = atr(high, low, close, period=3)
    assert a.iloc[2] == pytest.approx(10 / 3)
    assert a.iloc[3] == pytest.approx((10 / 3 * 2 + 2) / 3)


def test_지표_열이_모두_붙음():
    n = 80
    close = pd.Series(np.linspace(100, 120, n))
    df = pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 1000.0})
    out = add_indicators(df)
    for col in ["ma_short", "ma_long", "bb_mid", "bb_upper", "bb_lower", "rsi", "atr", "vol_avg"]:
        assert col in out.columns
        assert out[col].iloc[-1] == out[col].iloc[-1]   # 마지막 값은 NaN이 아님

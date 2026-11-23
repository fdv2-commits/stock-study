"""전략 백테스트 테스트: 작은 가짜 데이터로 손계산과 비교한다."""
import math

import numpy as np
import pandas as pd
import pytest

from backtest import engine as bt
from backtest import strategies as stg


def frame(opens, highs, lows, closes, atr=2.0, volume=1000.0):
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="B")
    return pd.DataFrame({"Open": opens, "High": highs, "Low": lows, "Close": closes,
                         "Volume": volume, "atr": atr}, index=idx)


# ── 거래 만들기 ───────────────────────────────────────
def test_신호_다음날_시가에_사고_목표에서_정리():
    # 0일 신호 → 1일 시가 100 매수, ATR 2×2 = 손절폭 4 → 손절 96, 목표 108(2R)
    df = frame(opens=[99, 100, 103, 107], highs=[100, 104, 108, 109], lows=[98, 99, 102, 106],
               closes=[99, 103, 107, 108])
    sig = pd.Series([True, False, False, False], index=df.index)
    trades = bt.run_symbol(df, sig, stop_mult=2, target_r=2, max_hold=10, cost_pct=0)
    assert len(trades) == 1
    t = trades[0]
    assert t["entry_date"] == df.index[1] and t["entry"] == 100
    assert t["stop"] == 96 and t["target"] == 108
    assert t["reason"] == "target" and t["exit_date"] == df.index[2]
    assert t["r"] == pytest.approx(2.0) and t["stop_pct"] == pytest.approx(4.0)


def test_비용은_수익률과_R에서_빠짐():
    df = frame(opens=[99, 100, 103], highs=[100, 104, 108], lows=[98, 99, 102], closes=[99, 103, 107])
    sig = pd.Series([True, False, False], index=df.index)
    t = bt.run_symbol(df, sig, 2, 2, 10, cost_pct=0.5)[0]
    assert t["ret_pct"] == pytest.approx(8.0 - 0.5)
    assert t["r"] == pytest.approx((108 - 100 - 0.5) / 4)


def test_최대_보유일이_지나면_종가에_정리():
    df = frame(opens=[100] * 6, highs=[101] * 6, lows=[99] * 6, closes=[100, 100, 100.5, 101, 100, 100])
    sig = pd.Series([True] + [False] * 5, index=df.index)
    t = bt.run_symbol(df, sig, 2, 2, max_hold=3, cost_pct=0)[0]
    assert t["reason"] == "time" and t["bars_held"] == 3 and t["exit"] == 101   # 1·2·3일째 → 3일째 종가


def test_데이터_끝까지_결과가_안난_거래는_제외():
    df = frame(opens=[100] * 4, highs=[101] * 4, lows=[99] * 4, closes=[100] * 4)
    sig = pd.Series([True, False, False, False], index=df.index)
    assert bt.run_symbol(df, sig, 2, 2, max_hold=10, cost_pct=0) == []


def test_보유중에는_새_신호를_무시하고_정리한날부터_다시봄():
    # 0일 신호 → 1일 매수, 2일 손절(저가 95 ≤ 96). 1일 신호는 보유 중이라 무시, 2일 신호로 3일 재매수
    df = frame(opens=[100, 100, 99, 100, 101], highs=[101, 101, 100, 109, 102], lows=[99, 99, 95, 99, 100],
               closes=[100, 100, 96, 108, 101])
    sig = pd.Series([True, True, True, False, False], index=df.index)
    trades = bt.run_symbol(df, sig, 2, 2, 10, 0)
    assert [t["entry_date"] for t in trades] == [df.index[1], df.index[3]]
    assert trades[0]["reason"] == "stop" and trades[1]["reason"] == "target"


def test_시작위치_이전_신호는_무시():
    df = frame(opens=[99, 100, 103, 107], highs=[100, 104, 108, 109], lows=[98, 99, 102, 106],
               closes=[99, 103, 107, 108])
    sig = pd.Series([True, False, False, False], index=df.index)
    assert bt.run_symbol(df, sig, 2, 2, 10, 0, start_idx=1) == []


# ── 성적 요약 ────────────────────────────────────────
def test_성적_요약():
    trades = [{"r": 2.0, "bars_held": 4, "reason": "target"}, {"r": -1.0, "bars_held": 2, "reason": "stop"},
              {"r": 0.5, "bars_held": 6, "reason": "time"}]
    s = bt.summarize(trades)
    assert s["count"] == 3 and s["wins"] == 2
    assert s["avg_r"] == pytest.approx(0.5) and s["total_r"] == pytest.approx(1.5)
    assert s["profit_factor"] == pytest.approx(2.5)        # (2 + 0.5) ÷ 1
    assert s["avg_hold"] == pytest.approx(4.0)
    assert s["reasons"] == {"target": 1, "stop": 1, "time": 1}


def test_손실이_없으면_이익손실비는_무한대():
    assert math.isinf(bt.summarize([{"r": 1.0, "bars_held": 1, "reason": "target"}])["profit_factor"])


def test_본전_승률():
    assert bt.breakeven_win_rate(2) == pytest.approx(100 / 3)


# ── 내 자금 기준 ──────────────────────────────────────
def test_투자_비율은_손실한도와_비중한도_중_작은쪽():
    assert bt.position_fraction(stop_pct=4, risk_pct=1, max_weight_pct=25) == pytest.approx(0.25)   # 1/4
    assert bt.position_fraction(stop_pct=2, risk_pct=1, max_weight_pct=25) == pytest.approx(0.25)   # 0.5 → 한도 0.25
    assert bt.position_fraction(stop_pct=10, risk_pct=1, max_weight_pct=25) == pytest.approx(0.1)


def test_자금곡선_손절이면_딱_1퍼센트_손실():
    # 손절폭 4%, 손실 −4%(=−1R, 비용 0) → 비중 25% × −4% = 자금의 −1%
    t = {"exit_date": pd.Timestamp("2024-01-05"), "stop_pct": 4.0, "ret_pct": -4.0}
    curve = bt.equity_curve([t], 3_000_000, 1.0, 25.0)
    assert curve["equity"].iloc[-1] == pytest.approx(2_970_000)


def test_자금곡선은_정리일_순서로_복리():
    t1 = {"exit_date": pd.Timestamp("2024-02-01"), "stop_pct": 4.0, "ret_pct": 8.0}    # +2%
    t2 = {"exit_date": pd.Timestamp("2024-01-01"), "stop_pct": 4.0, "ret_pct": -4.0}   # −1% (먼저)
    curve = bt.equity_curve([t1, t2], 100.0, 1.0, 25.0)
    assert curve["pnl"].iloc[1] == pytest.approx(-1.0)
    assert curve["equity"].iloc[-1] == pytest.approx(100 * 0.99 * 1.02)


def test_최대_낙폭():
    assert bt.max_drawdown_pct(pd.Series([100, 120, 90, 130, 117])) == pytest.approx(-25.0)
    assert bt.max_drawdown_pct(pd.Series([100, 110, 120])) == 0.0


# ── 전략 신호 ────────────────────────────────────────
def ind_frame(**cols):
    n = len(next(iter(cols.values())))
    base = {"Open": [10.0] * n, "High": [10.0] * n, "Low": [10.0] * n, "Close": [10.0] * n,
            "Volume": [100.0] * n, "vol_avg": [100.0] * n, "ma_short": [10.0] * n, "ma_long": [10.0] * n,
            "rsi": [50.0] * n}
    base.update(cols)
    return pd.DataFrame(base)


def test_눌림목_신호():
    df = ind_frame(Close=[12, 12, 9], ma_short=[11, 11, 11], ma_long=[10, 10, 10], rsi=[48, 60, 48])
    assert stg.pullback(df, 40, 55).tolist() == [True, False, False]   # 2번째 RSI 60, 3번째 종가<60일선


def test_돌파_신호():
    df = ind_frame(High=[10, 11, 10, 12.5], Close=[10, 11, 10, 12], Volume=[100, 100, 100, 200])
    out = stg.breakout(df, days=2, vol_mult=1.5)
    assert out.tolist() == [False, False, False, True]   # 최근 2일 고가 11 → 종가 12 돌파 + 거래량 2배


def test_골든크로스는_뚫은_날만():
    df = ind_frame(ma_short=[np.nan, 9, 11, 12, 9, 11], ma_long=[np.nan, 10, 10, 10, 10, 10])
    assert stg.golden_cross(df).tolist() == [False, False, True, False, False, True]


def test_골든크로스_데이터_맨앞_가짜신호_없음():
    df = ind_frame(ma_short=[np.nan, 11, 12], ma_long=[np.nan, 10, 10])
    assert stg.golden_cross(df).tolist() == [False, False, False]


def test_과매도_반등_신호():
    df = ind_frame(rsi=[np.nan, 25, 28, 31, 35, 29, 30])
    assert stg.oversold_bounce(df, 30).tolist() == [False, False, False, True, False, False, True]


def test_모든_전략이_기본값으로_실행됨():
    n = 150
    close = pd.Series(100 + np.sin(np.arange(n) / 5) * 10)
    df = ind_frame(Close=close.tolist(), High=(close + 1).tolist(), Low=(close - 1).tolist(),
                   ma_short=close.rolling(20).mean().tolist(), ma_long=close.rolling(60).mean().tolist(),
                   rsi=[50.0] * n, Volume=[100.0] * n, vol_avg=[100.0] * n, Open=close.tolist())
    for key, info in stg.STRATEGIES.items():
        params = {name: p[1] for name, p in info["params"].items()}
        out = stg.signals(df, key, params)
        assert out.dtype == bool and len(out) == n

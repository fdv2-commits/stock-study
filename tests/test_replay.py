"""차트 복기 계산 테스트: 손으로 계산한 값과 비교한다."""
import random

import pandas as pd
import pytest

from data.prices import clean, detect_market, normalize_symbol
from quiz import progress as prog
from replay import engine


def bars(rows):
    """[(시가, 고가, 저가, 종가), ...] → 일봉 표."""
    return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"])


# ── 손절·목표 판정 ────────────────────────────────────
def test_목표가_먼저_도달():
    future = bars([(100, 103, 99, 102), (102, 111, 101, 110)])
    r = engine.simulate_trade(future, entry=100, stop=95, target=110)
    assert r["reason"] == "target" and r["exit_price"] == 110 and r["bars_held"] == 2
    assert r["r"] == pytest.approx(2.0)          # (110-100)/(100-95)
    assert r["ret_pct"] == pytest.approx(10.0)


def test_손절가_먼저_도달():
    future = bars([(100, 101, 94, 96)])
    r = engine.simulate_trade(future, entry=100, stop=95, target=110)
    assert r["reason"] == "stop" and r["exit_price"] == 95 and r["r"] == pytest.approx(-1.0)


def test_갭하락이면_시가에_손절_1R보다_더_손해():
    future = bars([(90, 92, 88, 91)])
    r = engine.simulate_trade(future, entry=100, stop=95, target=110)
    assert r["reason"] == "stop_gap" and r["exit_price"] == 90
    assert r["r"] == pytest.approx(-2.0)          # (90-100)/5


def test_갭상승이면_시가에_익절():
    future = bars([(100, 101, 99, 100), (115, 118, 114, 117)])
    r = engine.simulate_trade(future, entry=100, stop=95, target=110)
    assert r["reason"] == "target_gap" and r["exit_price"] == 115 and r["exit_pos"] == 1


def test_같은날_손절과_목표_모두_닿으면_보수적으로_손절():
    future = bars([(100, 112, 94, 105)])
    r = engine.simulate_trade(future, entry=100, stop=95, target=110)
    assert r["reason"] == "stop" and r["both_same_day"]


def test_둘다_안오면_마지막_종가로_기간만료():
    future = bars([(100, 102, 98, 101), (101, 104, 99, 103)])
    r = engine.simulate_trade(future, entry=100, stop=95, target=110)
    assert r["reason"] == "time" and r["exit_price"] == 103
    assert r["r"] == pytest.approx(0.6)


def test_결과_설명에_이유와_R이_들어감():
    r = engine.simulate_trade(bars([(100, 111, 99, 110)]), 100, 95, 110)
    text = engine.explain_result(r, lambda v: f"${v:.2f}")
    assert "목표가 도달" in text and "+2.00R" in text and "$110.00" in text


# ── 추천 계획·검사 ────────────────────────────────────
def test_추천_손절_목표():
    stop, target = engine.suggest_plan(100, atr_value=2.5, stop_mult=2, rr=2)
    assert stop == pytest.approx(95) and target == pytest.approx(110)


def test_ATR이_없으면_고정_퍼센트로():
    stop, target = engine.suggest_plan(100, atr_value=float("nan"))
    assert stop < 100 < target


@pytest.mark.parametrize("stop, target, ok", [(95, 110, True), (100, 110, False), (105, 110, False),
                                              (95, 100, False), (0, 110, False)])
def test_계획_검사(stop, target, ok):
    assert (engine.validate_plan(100, stop, target) is None) == ok


def test_손익비():
    assert engine.plan_rr(100, 95, 112.5) == pytest.approx(2.5)


# ── 구간 고르기 ───────────────────────────────────────
def test_판단봉_위치는_앞뒤_여유를_지킴():
    rng = random.Random(0)
    for _ in range(200):
        d = engine.pick_decision_index(500, rng, history=120, after=20, warmup=60, exclude_latest=5)
        assert 60 + 120 - 1 <= d <= 500 - 1 - 20 - 5


def test_데이터가_짧으면_안내():
    with pytest.raises(ValueError):
        engine.pick_decision_index(100, random.Random(0), history=120, after=20, warmup=60)


# ── 한 봉씩: 매매 요약 ─────────────────────────────────
def test_매매_요약_복리():
    s = engine.summarize_trades([{"entry": 100, "exit": 110}, {"entry": 50, "exit": 45}])
    assert s["count"] == 2 and s["wins"] == 1 and s["win_rate"] == 50
    assert s["total_ret_pct"] == pytest.approx((1.1 * 0.9 - 1) * 100)   # -1%


def test_매매가_없으면_0():
    assert engine.summarize_trades([]) == {"count": 0, "wins": 0, "win_rate": 0.0, "total_ret_pct": 0.0}


# ── 지표 읽기 도움말 ──────────────────────────────────
def test_지표_도움말_문장():
    row = pd.Series({"Close": 110, "ma_short": 105, "ma_long": 100, "rsi": 48,
                     "bb_upper": 120, "bb_lower": 100, "Volume": 2000, "vol_avg": 1000})
    notes = engine.indicator_notes(row)
    assert any("상승 추세" in n for n in notes)
    assert any("RSI 48 → 40~55" in n for n in notes)
    assert any("50% 위치" in n for n in notes)
    assert any("2.0배 → 많음" in n for n in notes)


# ── 시세 정리·종목 코드 ────────────────────────────────
def test_시장_구분():
    assert detect_market("005930") == "KR"
    assert detect_market("aapl") == "US"
    assert normalize_symbol(" aapl ") == "AAPL"
    assert normalize_symbol("005930") == "005930"


def test_시세_정리():
    idx = pd.to_datetime(["2024-01-03", "2024-01-02", "2024-01-02", "2024-01-04"]).tz_localize("America/New_York")
    raw = pd.DataFrame({"Open": [0, 10, 11, 12], "High": [0, 11, 12, 13], "Low": [0, 9, 10, 11],
                        "Close": [10.5, 10, 11, 0], "Volume": [1, 2, 3, 4], "Dividends": [0, 0, 0, 0]}, index=idx)
    df = clean(raw)
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert df.index.tz is None and df.index.is_monotonic_increasing
    assert len(df) == 2                       # 중복 날짜 1개, 종가 0인 날 1개 제거
    assert df.loc["2024-01-03", "Open"] == 10.5   # 시가 0 → 종가로 채움


# ── 복기 기록 ────────────────────────────────────────
def test_복기_기록과_성적():
    p = prog.empty_progress()
    prog.record_replay(p, {"mode": "one", "decision": "buy", "r": 2.0, "ret_pct": 10}, when="t")
    prog.record_replay(p, {"mode": "one", "decision": "buy", "r": -1.0, "ret_pct": -5}, when="t")
    prog.record_replay(p, {"mode": "one", "decision": "pass", "would_r": -1.0}, when="t")
    prog.record_replay(p, {"mode": "step", "ret_pct": 3.0, "hold_ret_pct": 1.0}, when="t")
    s = prog.replay_stats(p)
    assert (s["buys"], s["wins"], s["total_r"]) == (2, 1, 1.0)
    assert s["avg_r"] == pytest.approx(0.5)
    assert (s["passes"], s["good_passes"]) == (1, 1)
    assert (s["steps"], s["step_beat"]) == (1, 1)
    assert p["replays"][0]["time"] == "t"


def test_예전_기록에도_복기칸이_생김(tmp_path):
    path = tmp_path / "progress.json"
    path.write_text('{"questions": {}, "sessions": []}', encoding="utf-8")
    loaded, _ = prog.load_progress(path)
    assert loaded["replays"] == []

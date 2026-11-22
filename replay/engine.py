"""차트 복기 계산: 구간 고르기, 손절·목표 판정, 점수, 지표 읽기 도움말.

용어
- 판단 봉(decision): 판단할 때 화면에 보이는 마지막 봉. 이 봉의 종가에 매수한다고 가정한다.
- 미래 봉(future): 판단 뒤에 공개되는 봉들.
- R: 손절폭(매수가 − 손절가) 1개를 1R로 보고 손익을 잰 값. +2R = 손절폭의 2배만큼 벌었다는 뜻.
"""
import math
import random

import pandas as pd

import config


# ── 구간 고르기 ───────────────────────────────────────
def pick_decision_index(n_rows: int, rng: random.Random, history: int, after: int,
                        warmup: int = config.MA_LONG, exclude_latest: int = config.REPLAY_EXCLUDE_LATEST_BARS) -> int:
    """판단 봉 위치(0부터)를 무작위로 고른다.

    - 앞쪽: 지표 계산용 warmup + 보여줄 history봉이 있어야 함
    - 뒤쪽: 판단 뒤 after봉이 있어야 하고, 가장 최근 exclude_latest봉은 쓰지 않음
    데이터가 모자라면 ValueError.
    """
    lo = warmup + history - 1
    hi = n_rows - 1 - after - exclude_latest
    if hi < lo:
        raise ValueError("데이터 기간이 짧아서 연습 구간을 만들 수 없습니다.")
    return rng.randint(lo, hi)


# ── 손절·목표 ─────────────────────────────────────────
def suggest_plan(entry: float, atr_value: float, stop_mult: float = config.REPLAY_STOP_ATR_MULT,
                 rr: float = config.REPLAY_DEFAULT_RR) -> tuple[float, float]:
    """추천 손절가·목표가. 손절 = 매수가 − ATR×배수, 목표 = 매수가 + 손절폭×손익비."""
    risk = atr_value * stop_mult
    if not risk or math.isnan(risk) or risk >= entry:
        risk = entry * config.REPLAY_FALLBACK_STOP_PCT / 100   # ATR을 못 구하면 고정 %로 대신 (안전장치)
    return entry - risk, entry + risk * rr


def validate_plan(entry: float, stop: float, target: float) -> str | None:
    """손절가 < 매수가 < 목표가인지. 문제가 있으면 한국어 안내, 정상이면 None."""
    if stop <= 0:
        return "손절가는 0보다 커야 합니다."
    if stop >= entry:
        return "손절가는 매수가보다 낮아야 합니다."
    if target <= entry:
        return "목표가는 매수가보다 높아야 합니다."
    return None


def plan_rr(entry: float, stop: float, target: float) -> float:
    """손익비 = (목표가 − 매수가) ÷ (매수가 − 손절가)."""
    return (target - entry) / (entry - stop)


def simulate_trade(future: pd.DataFrame, entry: float, stop: float, target: float) -> dict:
    """판단 봉 종가에 매수했다고 보고, 미래 봉에서 손절·목표 중 무엇이 먼저 나오는지 판정한다.

    규칙 (매일 순서대로 확인)
    1. 시가가 이미 손절가 이하 → 시가에 손절 (갭하락: 손절가보다 더 손해)
    2. 시가가 이미 목표가 이상 → 시가에 익절 (갭상승)
    3. 저가가 손절가 이하 → 손절가에 손절
       (같은 날 고가도 목표가 이상이면, 어느 쪽이 먼저인지 알 수 없어 보수적으로 손절로 본다)
    4. 고가가 목표가 이상 → 목표가에 익절
    끝까지 둘 다 안 나오면 마지막 봉 종가에 정리(기간 만료).
    """
    reason, exit_price, exit_pos = "time", float(future["Close"].iloc[-1]), len(future) - 1
    both_same_day = False
    for i, (o, h, l) in enumerate(zip(future["Open"], future["High"], future["Low"])):
        if o <= stop:
            reason, exit_price, exit_pos = "stop_gap", float(o), i
            break
        if o >= target:
            reason, exit_price, exit_pos = "target_gap", float(o), i
            break
        if l <= stop:
            both_same_day = h >= target
            reason, exit_price, exit_pos = "stop", float(stop), i
            break
        if h >= target:
            reason, exit_price, exit_pos = "target", float(target), i
            break
    return {
        "reason": reason,
        "exit_price": exit_price,
        "exit_pos": exit_pos,                 # 미래 봉 중 몇 번째(0부터)에 끝났는지
        "bars_held": exit_pos + 1,
        "r": (exit_price - entry) / (entry - stop),
        "ret_pct": (exit_price / entry - 1) * 100,
        "both_same_day": both_same_day,
    }


REASON_TEXT = {
    "stop": "손절가 도달",
    "stop_gap": "갭하락으로 시가에 손절",
    "target": "목표가 도달",
    "target_gap": "갭상승으로 시가에 익절",
    "time": "기간 만료로 마지막 종가에 정리",
}


def explain_result(result: dict, fmt) -> str:
    """결과 한 줄 설명. fmt는 가격을 글자로 바꾸는 함수."""
    text = (f"{result['bars_held']}일째 {REASON_TEXT[result['reason']]} → "
            f"{fmt(result['exit_price'])} ({result['ret_pct']:+.1f}%, {result['r']:+.2f}R)")
    if result["both_same_day"]:
        text += " · 같은 날 목표가도 닿았지만 순서를 알 수 없어 손절로 계산"
    return text


# ── 한 봉씩 넘기기형 ───────────────────────────────────
def summarize_trades(trades: list[dict]) -> dict:
    """매매 목록 [{entry, exit}] → 거래 수, 승률, 누적 수익률(복리 %)."""
    rets = [t["exit"] / t["entry"] - 1 for t in trades]
    total = 1.0
    for r in rets:
        total *= 1 + r
    wins = sum(1 for r in rets if r > 0)
    return {
        "count": len(rets),
        "wins": wins,
        "win_rate": wins / len(rets) * 100 if rets else 0.0,
        "total_ret_pct": (total - 1) * 100,
    }


# ── 지표 읽기 도움말 ──────────────────────────────────
def indicator_notes(row: pd.Series) -> list[str]:
    """판단 봉의 지표를 쉬운 말로 풀어 쓴다. (예: 'RSI 48 → 40~55 눌림목 관심 구간')"""
    notes = []
    c, ma_s, ma_l = row["Close"], row.get("ma_short"), row.get("ma_long")
    if pd.notna(ma_s) and pd.notna(ma_l):
        above_s, above_l = c > ma_s, c > ma_l
        if above_s and above_l and ma_s > ma_l:
            trend = "상승 추세 (종가 > 20일선 > 60일선)"
        elif not above_s and not above_l and ma_s < ma_l:
            trend = "하락 추세 (종가 < 20일선 < 60일선)"
        else:
            trend = "추세 애매 (이동평균선과 종가가 엇갈림)"
        notes.append(f"추세: {trend}")
    r = row.get("rsi")
    if pd.notna(r):
        if r >= config.RSI_OVERBOUGHT:
            zone = f"{config.RSI_OVERBOUGHT} 이상 과매수"
        elif r <= config.RSI_OVERSOLD:
            zone = f"{config.RSI_OVERSOLD} 이하 과매도"
        elif config.RSI_PULLBACK_LOW <= r <= config.RSI_PULLBACK_HIGH:
            zone = f"{config.RSI_PULLBACK_LOW}~{config.RSI_PULLBACK_HIGH} 눌림목 관심 구간"
        else:
            zone = "중간 구간"
        notes.append(f"RSI {r:.0f} → {zone}")
    up, lo = row.get("bb_upper"), row.get("bb_lower")
    if pd.notna(up) and pd.notna(lo) and up > lo:
        pos = (c - lo) / (up - lo) * 100      # 0 = 하단, 100 = 상단
        edge = config.BB_NEAR_EDGE_PCT
        where = "상단 근처" if pos >= 100 - edge else "하단 근처" if pos <= edge else "중간"
        notes.append(f"볼린저밴드: 띠 안에서 {pos:.0f}% 위치 → {where}")
    va = row.get("vol_avg")
    if pd.notna(va) and va > 0:
        ratio = row["Volume"] / va
        level = "많음" if ratio >= config.VOLUME_HIGH else "적음" if ratio <= config.VOLUME_LOW else "보통"
        notes.append(f"거래량: 20일 평균의 {ratio:.1f}배 → {level}")
    return notes
